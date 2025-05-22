"""
Synthetic Statement Generator for Lucky Lad Energy
-------------------------------------------------
A tool to generate realistic vendor statements for training and testing Document AI.

This generator creates synthetic statements that mimic the structure and appearance
of real statements from vendors like Reagan Power, with aging summaries and transaction history.
"""

import os
import json
import random
import datetime
from typing import List, Dict, Optional, Union, Tuple
from enum import Enum
from decimal import Decimal

# Data generation
from faker import Faker
from faker.providers import BaseProvider

# PDF generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.platypus.flowables import Flowable

# Image processing for degradation
from PIL import Image, ImageFilter, ImageOps
import numpy as np
from io import BytesIO

# Data validation
from pydantic import BaseModel, field_validator, model_validator

# Template rendering
from jinja2 import Template

# Create directories if they don't exist
os.makedirs("synthetic_statements/pdf", exist_ok=True)
os.makedirs("synthetic_statements/json", exist_ok=True)
os.makedirs("synthetic_statements/templates", exist_ok=True)

# Initialize Faker
fake = Faker()

# ===== Custom Faker Providers =====

class OilGasStatementProvider(BaseProvider):
    """Custom provider for oil and gas industry statement data"""
    
    def well_name(self) -> str:
        """Generate a realistic well name"""
        patterns = [
            lambda: f"{fake.random_int(10000, 99999)} {fake.last_name()} Creek",
            lambda: f"{fake.last_name()} {fake.random_int(1, 9)}",
            lambda: f"{fake.last_name()} {fake.random_element(['A', 'B', 'C', 'D'])}-{fake.random_int(1, 99)}",
            lambda: f"Godchaux {fake.random_int(1, 9)}",
            lambda: f"Kirby {fake.last_name()}",
            lambda: f"{fake.last_name()} {fake.random_element(['SWD', 'ALT', 'UNIT'])}",
            lambda: f"{fake.city()} {fake.random_element(['East', 'West', 'North', 'South'])} {fake.random_int(1, 12)}",
            lambda: f"{fake.last_name()}-{fake.last_name()} {fake.random_element(['Joint', 'Combined'])} {fake.random_int(1, 5)}",
        ]
        return random.choice(patterns)()
    
    def field_name(self) -> str:
        """Generate a realistic field name"""
        patterns = [
            lambda: random.choice([
                "Live Oak", "Theuvenins", "Johnson Bayou", "Gordon",
                "Temple", "Spurger", "Dreyfus", "Duplantier",
                "Eagleford", "Permian", "Bakken", "Marcellus",
                "Haynesville", "Barnett", "Woodford", "Utica"
            ]),
            lambda: f"{fake.city()} {random.choice(['Field', 'Basin', 'Formation', 'Play'])}",
            lambda: f"{fake.last_name()} {random.choice(['County', 'Parish', 'Township'])} {random.choice(['East', 'West', 'North', 'South'])}"
        ]
        return random.choice(patterns)()
    
    def invoice_number(self) -> str:
        """Generate an invoice number"""
        patterns = [
            lambda: str(fake.random_int(10000, 999999)),
            lambda: f"INV{fake.random_int(100000, 999999)}",
            lambda: f"{fake.random_int(10000, 99999)}[{fake.random_int(10, 99)}]",
            lambda: f"{fake.random_letter().upper()}{fake.random_letter().upper()}-{fake.random_int(1000, 9999)}",
            lambda: f"{fake.random_int(100, 999)}-{fake.random_int(1000, 9999)}",
            lambda: f"INV-{fake.date_this_year().strftime('%m%d')}-{fake.random_int(100, 999)}",
            lambda: f"{datetime.datetime.now().strftime('%y')}{fake.random_int(1000, 9999)}",
            lambda: f"SI{fake.random_int(10000, 99999)}",
        ]
        return random.choice(patterns)()
    
    def transaction_description(self, is_credit=False, well_name=None) -> str:
        """Generate a realistic transaction description"""
        if is_credit:
            patterns = [
                lambda: f"GENJRNL #{fake.random_int(10, 99)}-{fake.random_int(10, 99)}-{fake.random_int(10, 99)}R. "
                        f"Reverse of GJE {fake.random_int(10, 99)}-{fake.random_int(10, 99)}-{fake.random_int(10, 99)} "
                        f"Transfer of Credits for\nLUCKY LAD ENERGY LLC from LUCKY LAD ENERGY LLC to {well_name or self.well_name()}",
                lambda: f"Credit Memo #{fake.random_int(1000, 9999)}. Amount ${fake.random_int(100, 2000)}.00.",
                lambda: f"Payment - Thank you. Check #{fake.random_int(10000, 99999)}",
                lambda: f"Adjustment #{fake.random_int(100, 999)}. Service credit ${fake.random_int(50, 500)}.00."
            ]
        else:
            invoice_num = self.invoice_number()
            due_date = (
                fake.date_between(start_date="+10d", end_date="+40d")
                .strftime("%m/%d/%Y")
                .lstrip("0")
                .replace("/0", "/")
            )
            amount = fake.random_int(500, 4000)
            
            patterns = [
                lambda: f"INV #{invoice_num}. Due {due_date}. Orig. Amount ${amount:,.2f}.",
                lambda: f"Invoice {invoice_num}. Due {due_date}. ${amount:,.2f}.",
                lambda: f"Monthly Service - INV #{invoice_num}. ${amount:,.2f}.",
                lambda: f"Equipment Rental - INV #{invoice_num}. ${amount:,.2f}."
            ]
        
        return random.choice(patterns)()

# Register the custom provider
fake.add_provider(OilGasStatementProvider)

# ===== Data Models =====

class AgingCategory(str, Enum):
    CURRENT = "CURRENT"
    PAST_DUE_30 = "1-30 DAYS PAST DUE"
    PAST_DUE_60 = "31-60 DAYS PAST DUE" 
    PAST_DUE_90 = "61-90 DAYS PAST DUE"
    OVER_90 = "OVER 90 DAYS PAST DUE"

class Address(BaseModel):
    """Model for address information"""
    customer_name: str
    attention: Optional[str] = None
    address: str

class StatementTransaction(BaseModel):
    """Model for statement transactions"""
    date: str
    transaction: str
    amount: float
    balance: float
    well_name: Optional[str] = None
    
    @property
    def formatted_amount(self) -> str:
        """Format amount with commas and 2 decimal places"""
        return f"{self.amount:,.2f}"
    
    @property
    def formatted_balance(self) -> str:
        """Format balance with commas and 2 decimal places"""
        return f"{self.balance:,.2f}"

class AgingSummary(BaseModel):
    """Model for aging summary"""
    current: float = 0.0
    past_due_30: float = 0.0
    past_due_60: float = 0.0 
    past_due_90: float = 0.0
    over_90: float = 0.0
    
    @property
    def total(self) -> float:
        """Calculate total of all aging categories"""
        return self.current + self.past_due_30 + self.past_due_60 + self.past_due_90 + self.over_90
    
    @property
    def formatted_current(self) -> str:
        return f"{self.current:,.2f}"
    
    @property
    def formatted_past_due_30(self) -> str:
        return f"{self.past_due_30:,.2f}"
    
    @property
    def formatted_past_due_60(self) -> str:
        return f"{self.past_due_60:,.2f}"
    
    @property
    def formatted_past_due_90(self) -> str:
        return f"{self.past_due_90:,.2f}"
    
    @property
    def formatted_over_90(self) -> str:
        return f"{self.over_90:,.2f}"
    
    @property
    def formatted_total(self) -> str:
        return f"{self.total:,.2f}"

class Statement(BaseModel):
    """Model for statement data"""
    statement_date: str
    to: Address
    vendor_name: str
    vendor_address: str
    transactions: List[StatementTransaction]
    aging_summary: AgingSummary

# ===== JSON Schema for Document AI =====

STATEMENT_JSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Vendor Statement Schema",
    "description": "Schema for vendor statements in the oil & gas industry",
    "type": "object",
    "required": [
        "metadata",
        "vendor_information",
        "customer_information",
        "statement_details",
        "aging_summary",
        "transactions"
    ],
    "properties": {
        "metadata": {
            "type": "object",
            "description": "Document AI processing metadata",
            "required": ["processor_id", "document_type", "confidence_threshold"],
            "properties": {
                "processor_id": {
                    "type": "string",
                    "description": "ID of the Document AI processor"
                },
                "document_type": {
                    "type": "string",
                    "enum": ["vendor_statement"],
                    "description": "Type of document"
                },
                "confidence_threshold": {
                    "type": "number",
                    "description": "Minimum confidence score for field extraction",
                    "minimum": 0,
                    "maximum": 1
                },
                "source_filename": {
                    "type": "string",
                    "description": "Original filename of the document"
                },
                "generation_timestamp": {
                    "type": "string",
                    "format": "date-time",
                    "description": "When the document was generated"
                }
            }
        },
        "vendor_information": {
            "type": "object",
            "description": "Information about the vendor issuing the statement",
            "required": ["name", "address"],
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the vendor"
                },
                "address": {
                    "type": "object",
                    "description": "Vendor's address",
                    "properties": {
                        "street": {
                            "type": "string",
                            "description": "Street address"
                        },
                        "city": {
                            "type": "string",
                            "description": "City"
                        },
                        "state": {
                            "type": "string",
                            "description": "State or province"
                        },
                        "postal_code": {
                            "type": "string",
                            "description": "ZIP or postal code"
                        },
                        "country": {
                            "type": "string",
                            "description": "Country"
                        },
                        "full_address": {
                            "type": "string",
                            "description": "Complete address as a single string"
                        }
                    }
                },
                "phone": {
                    "type": "string",
                    "description": "Vendor's phone number"
                },
                "email": {
                    "type": "string",
                    "description": "Vendor's email address"
                },
                "website": {
                    "type": "string",
                    "description": "Vendor's website"
                }
            }
        },
        "customer_information": {
            "type": "object",
            "description": "Information about the customer receiving the statement",
            "required": ["name", "address"],
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the customer"
                },
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID or account number"
                },
                "address": {
                    "type": "object",
                    "description": "Customer's address",
                    "properties": {
                        "street": {
                            "type": "string",
                            "description": "Street address"
                        },
                        "city": {
                            "type": "string",
                            "description": "City"
                        },
                        "state": {
                            "type": "string",
                            "description": "State or province"
                        },
                        "postal_code": {
                            "type": "string",
                            "description": "ZIP or postal code"
                        },
                        "country": {
                            "type": "string",
                            "description": "Country"
                        },
                        "full_address": {
                            "type": "string",
                            "description": "Complete address as a single string"
                        }
                    }
                },
                "attention": {
                    "type": "string",
                    "description": "Person or department the statement is addressed to"
                }
            }
        },
        "statement_details": {
            "type": "object",
            "description": "Details about the statement",
            "required": ["statement_date", "amount_due"],
            "properties": {
                "statement_date": {
                    "type": "string",
                    "description": "Date of the statement"
                },
                "statement_number": {
                    "type": "string",
                    "description": "Statement reference number"
                },
                "period_start": {
                    "type": "string",
                    "description": "Start date of the statement period"
                },
                "period_end": {
                    "type": "string",
                    "description": "End date of the statement period"
                },
                "amount_due": {
                    "type": "string",
                    "description": "Total amount due"
                },
                "amount_due_numeric": {
                    "type": "number",
                    "description": "Total amount due as a number"
                },
                "currency": {
                    "type": "string",
                    "description": "Currency of the amounts",
                    "default": "USD"
                },
                "payment_terms": {
                    "type": "string",
                    "description": "Payment terms"
                },
                "due_date": {
                    "type": "string",
                    "description": "Date payment is due"
                }
            }
        },
        "aging_summary": {
            "type": "object",
            "description": "Summary of aging buckets",
            "required": ["total"],
            "properties": {
                "current": {
                    "type": "string",
                    "description": "Current amount"
                },
                "current_numeric": {
                    "type": "number",
                    "description": "Current amount as a number"
                },
                "days_1_30": {
                    "type": "string",
                    "description": "1-30 days past due amount"
                },
                "days_1_30_numeric": {
                    "type": "number",
                    "description": "1-30 days past due amount as a number"
                },
                "days_31_60": {
                    "type": "string",
                    "description": "31-60 days past due amount"
                },
                "days_31_60_numeric": {
                    "type": "number",
                    "description": "31-60 days past due amount as a number"
                },
                "days_61_90": {
                    "type": "string",
                    "description": "61-90 days past due amount"
                },
                "days_61_90_numeric": {
                    "type": "number",
                    "description": "61-90 days past due amount as a number"
                },
                "days_over_90": {
                    "type": "string",
                    "description": "Over 90 days past due amount"
                },
                "days_over_90_numeric": {
                    "type": "number",
                    "description": "Over 90 days past due amount as a number"
                },
                "total": {
                    "type": "string",
                    "description": "Total of all aging buckets"
                },
                "total_numeric": {
                    "type": "number",
                    "description": "Total of all aging buckets as a number"
                }
            }
        },
        "transactions": {
            "type": "array",
            "description": "List of transactions on the statement",
            "items": {
                "type": "object",
                "required": ["date", "description", "amount", "balance"],
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date of the transaction"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the transaction"
                    },
                    "invoice_number": {
                        "type": "string",
                        "description": "Invoice number referenced in the transaction"
                    },
                    "amount": {
                        "type": "string",
                        "description": "Amount of the transaction"
                    },
                    "amount_numeric": {
                        "type": "number",
                        "description": "Amount of the transaction as a number"
                    },
                    "balance": {
                        "type": "string",
                        "description": "Running balance after the transaction"
                    },
                    "balance_numeric": {
                        "type": "number",
                        "description": "Running balance after the transaction as a number"
                    },
                    "well_name": {
                        "type": "string",
                        "description": "Name of the well associated with the transaction"
                    },
                    "transaction_type": {
                        "type": "string",
                        "description": "Type of transaction (invoice, payment, credit, etc.)",
                        "enum": ["invoice", "payment", "credit", "adjustment", "other"]
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Due date for the transaction"
                    }
                }
            }
        },
        "additional_information": {
            "type": "object",
            "description": "Any additional information on the statement",
            "properties": {
                "notes": {
                    "type": "string",
                    "description": "Notes or messages on the statement"
                },
                "payment_instructions": {
                    "type": "string",
                    "description": "Instructions for making payment"
                },
                "remittance_address": {
                    "type": "string",
                    "description": "Address for sending payment"
                }
            }
        }
    }
}


# ===== PDF Generation =====

def add_page_number(canvas, doc, page_number, total_pages):
    """Adds page numbers to the document"""
    canvas.saveState()
    canvas.setFont('Helvetica', 9)
    canvas.drawRightString(7.5*inch, 0.75*inch, f"Page {page_number} of {total_pages}")
    canvas.restoreState()


def create_statement_pdf(statement_data: Statement, output_path: str) -> str:
    """Create a PDF statement based on the statement data"""
    
    # Create a PDF document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch,
    )
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    title_style.alignment = 1  # Center alignment
    
    subtitle_style = styles["Heading2"]
    subtitle_style.alignment = 1  # Center alignment
    
    normal_style = styles["Normal"]
    
    # Create header style
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading2'],
        alignment=1,  # Center
        spaceAfter=0.1*inch,
    )
    
    # Create address style
    address_style = ParagraphStyle(
        'Address',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
    )
    
    # Create content elements
    elements = []
    
    # Vendor header
    elements.append(Paragraph(statement_data.vendor_name.upper(), title_style))
    elements.append(Paragraph(statement_data.vendor_address.replace("\n", "<br/>"), normal_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Statement header
    elements.append(Paragraph(f"Statement Date", header_style))
    elements.append(Paragraph(statement_data.statement_date, subtitle_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Customer info
    elements.append(Paragraph("To:", subtitle_style))
    elements.append(Paragraph(statement_data.to.customer_name, normal_style))
    elements.append(Paragraph(statement_data.to.address.replace("\n", "<br/>"), address_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Aging summary
    aging_data = [
        ["CURRENT", "1-30 DAYS PAST DUE", "31-60 DAYS PAST DUE", "61-90 DAYS PAST DUE", "OVER 90 DAYS PAST DUE", "Amount Due"],
        [
            f"${statement_data.aging_summary.formatted_current}",
            f"${statement_data.aging_summary.formatted_past_due_30}",
            f"${statement_data.aging_summary.formatted_past_due_60}",
            f"${statement_data.aging_summary.formatted_past_due_90}",
            f"${statement_data.aging_summary.formatted_over_90}",
            f"${statement_data.aging_summary.formatted_total}",
        ],
    ]
    
    # Calculate column widths for aging table
    aging_col_width = (doc.width - 12) / 6  # Divide available width by 6 columns
    
    aging_table = Table(aging_data, colWidths=[aging_col_width]*6)
    aging_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),  # Smaller font for headers
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("ALIGN", (0, 1), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),  # Smaller font for values
            ]
        )
    )
    
    elements.append(aging_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Transactions header
    elements.append(Paragraph("Transaction History", subtitle_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Transactions table
    trans_data = [["Date", "Transaction", "Amount", "Balance"]]
    
    # Group transactions by well name
    current_well = None
    
    for transaction in statement_data.transactions:
        # Check if we need to add a well name header
        if transaction.well_name and transaction.well_name != current_well:
            current_well = transaction.well_name
            # Add a well name row that spans all columns
            trans_data.append([current_well + "-", "", "", ""])
        
        # Add the transaction row
        trans_data.append([
            transaction.date,
            transaction.transaction,
            f"{transaction.amount:,.2f}",
            f"{transaction.balance:,.2f}",
        ])
    
    # Calculate column widths - date is narrow, transaction is wide
    trans_table = Table(
        trans_data, 
        colWidths=[0.8*inch, 4.5*inch, 1*inch, 1*inch],
        repeatRows=1  # Repeat header row on each page
    )
    
    # Style the transactions table
    table_style = [
        # Header row styling
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        
        # Data rows
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        
        # Align amounts and balances right
        ("ALIGN", (2, 1), (3, -1), "RIGHT"),
    ]
    
    # Add styling for well name rows
    for i, row in enumerate(trans_data):
        if i > 0 and row[1] == "" and row[2] == "" and row[3] == "":
            # This is a well name row
            table_style.extend([
                ("SPAN", (0, i), (-1, i)),  # Span all columns
                ("BACKGROUND", (0, i), (-1, i), colors.lightgrey),
                ("FONTNAME", (0, i), (-1, i), "Helvetica-Bold"),
                ("ALIGN", (0, i), (-1, i), "LEFT"),
            ])
    
    trans_table.setStyle(TableStyle(table_style))
    elements.append(trans_table)
    
    # Add page numbers
    # This is handled by the onLaterPages and onFirstPage functions in the build method
    
    # Build the PDF with page numbers
    page_count = len(statement_data.transactions) // 20 + 1  # Estimate page count
    
    # Build the PDF
    doc.build(
        elements,
        onFirstPage=lambda canvas, doc: add_page_number(canvas, doc, 1, page_count),
        onLaterPages=lambda canvas, doc: add_page_number(canvas, doc, canvas.getPageNumber(), page_count)
    )
    
    return output_path


# ===== JSON Generation =====

def generate_statement_json(statement_data: Statement) -> str:
    """Generate a JSON representation of the statement data for Document AI training"""
    
    # Parse address components
    def parse_address(address_str):
        lines = address_str.split('\n')
        address_obj = {
            "full_address": address_str
        }
        
        # Try to extract city, state, zip from the last line
        if len(lines) > 1:
            last_line = lines[-1]
            if ',' in last_line and ' ' in last_line.split(',')[1]:
                city = last_line.split(',')[0].strip()
                state_zip = last_line.split(',')[1].strip()
                state = state_zip.split(' ')[0].strip()
                postal_code = ' '.join(state_zip.split(' ')[1:]).strip()
                
                address_obj["city"] = city
                address_obj["state"] = state
                address_obj["postal_code"] = postal_code
                address_obj["street"] = '\n'.join(lines[:-1])
            else:
                address_obj["street"] = address_str
        else:
            address_obj["street"] = address_str
            
        return address_obj
    
    # Extract invoice numbers from transaction descriptions
    def extract_invoice_number(description):
        if "INV #" in description:
            parts = description.split("INV #")[1].split(".")
            if parts:
                return parts[0].strip()
        return None
    
    # Determine transaction type
    def determine_transaction_type(amount, description):
        if amount < 0:
            return "credit"
        elif "INV #" in description:
            return "invoice"
        elif "PAYMENT" in description.upper():
            return "payment"
        elif "ADJUST" in description.upper():
            return "adjustment"
        else:
            return "other"
    
    # Extract due date from transaction description
    def extract_due_date(description):
        if "Due " in description:
            parts = description.split("Due ")[1].split(".")
            if parts:
                return parts[0].strip()
        return None
    
    # Build the JSON structure
    json_data = {
        "metadata": {
            "processor_id": "statement-processor-v1",
            "document_type": "vendor_statement",
            "confidence_threshold": 0.7,
            "source_filename": f"statement_{statement_data.statement_date.replace('/', '')}.pdf",
            "generation_timestamp": datetime.datetime.now().isoformat()
        },
        "vendor_information": {
            "name": statement_data.vendor_name,
            "address": parse_address(statement_data.vendor_address)
        },
        "customer_information": {
            "name": statement_data.to.customer_name,
            "address": parse_address(statement_data.to.address)
        },
        "statement_details": {
            "statement_date": statement_data.statement_date,
            "amount_due": f"${statement_data.aging_summary.formatted_total}",
            "amount_due_numeric": statement_data.aging_summary.total,
            "currency": "USD"
        },
        "aging_summary": {
            "current": f"${statement_data.aging_summary.formatted_current}",
            "current_numeric": statement_data.aging_summary.current,
            "days_1_30": f"${statement_data.aging_summary.formatted_past_due_30}",
            "days_1_30_numeric": statement_data.aging_summary.past_due_30,
            "days_31_60": f"${statement_data.aging_summary.formatted_past_due_60}",
            "days_31_60_numeric": statement_data.aging_summary.past_due_60,
            "days_61_90": f"${statement_data.aging_summary.formatted_past_due_90}",
            "days_61_90_numeric": statement_data.aging_summary.past_due_90,
            "days_over_90": f"${statement_data.aging_summary.formatted_over_90}",
            "days_over_90_numeric": statement_data.aging_summary.over_90,
            "total": f"${statement_data.aging_summary.formatted_total}",
            "total_numeric": statement_data.aging_summary.total
        },
        "transactions": []
    }
    
    # Add transactions
    for transaction in statement_data.transactions:
        transaction_obj = {
            "date": transaction.date,
            "description": transaction.transaction,
            "amount": f"{transaction.amount:,.2f}",
            "amount_numeric": transaction.amount,
            "balance": f"{transaction.balance:,.2f}",
            "balance_numeric": transaction.balance,
            "transaction_type": determine_transaction_type(transaction.amount, transaction.transaction)
        }
        
        # Add optional fields if available
        if transaction.well_name:
            transaction_obj["well_name"] = transaction.well_name
            
        invoice_number = extract_invoice_number(transaction.transaction)
        if invoice_number:
            transaction_obj["invoice_number"] = invoice_number
            
        due_date = extract_due_date(transaction.transaction)
        if due_date:
            transaction_obj["due_date"] = due_date
            
        json_data["transactions"].append(transaction_obj)
    
    return json.dumps(json_data, indent=2)


def save_statement_json(statement_data: Statement, output_path: str) -> str:
    """Save the statement data as JSON for Document AI training"""
    json_content = generate_statement_json(statement_data)
    
    with open(output_path, "w") as f:
        f.write(json_content)
        
    return output_path
    statement_date: str
    to: Address
    vendor_name: str
    vendor_address: str
    transactions: List[StatementTransaction]
    aging_summary: AgingSummary
    
    class Config:
        arbitrary_types_allowed = True
# ===== Image Degradation =====

def degrade_pdf_image(pdf_path, output_path=None):
    """Apply realistic degradation to a PDF by converting to image and back"""
    if output_path is None:
        output_path = pdf_path.replace(".pdf", "_degraded.pdf")

    # Convert PDF to image
    images = []
    try:
        # Use Pillow to convert PDF to images
        from pdf2image import convert_from_path

        images = convert_from_path(pdf_path, dpi=150)
    except ImportError:
        print("pdf2image not installed. Please install it with: pip install pdf2image")
        print("Also ensure poppler is installed on your system")
        return pdf_path

    degraded_images = []
    for img in images:
        # Apply various degradation effects
        img = apply_degradation_effects(img)
        degraded_images.append(img)

    # Save degraded images as a new PDF
    degraded_images[0].save(
        output_path,
        save_all=True,
        append_images=degraded_images[1:] if len(degraded_images) > 1 else [],
    )

    return output_path


def apply_degradation_effects(img):
    """Apply various degradation effects to an image, but keep it realistic and readable"""
    # Convert to grayscale with slight probability (reduced chance)
    if random.random() < 0.15:  # Reduced from 0.3
        img = img.convert("L").convert("RGB")

    # Apply very slight rotation (0-1 degrees) - reduced from 0-2 degrees
    rotation_angle = random.uniform(-1, 1)
    img = img.rotate(rotation_angle, resample=Image.BICUBIC, expand=False)

    # Add minimal noise - significantly reduced noise factor
    img_array = np.array(img)
    noise_factor = random.uniform(1, 5)  # Reduced from 5-15
    noise = np.random.normal(0, noise_factor, img_array.shape).astype(np.uint8)
    noisy_img_array = np.clip(img_array + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(noisy_img_array)

    # Add very slight blur (reduced chance and radius)
    if random.random() < 0.3:  # Reduced from 0.5
        blur_radius = random.uniform(0.1, 0.4)  # Reduced from 0.3-0.8
        img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # Adjust contrast and brightness (minimal adjustment)
    enhancer = ImageOps.autocontrast(img, cutoff=random.uniform(0, 3))  # Reduced from 0-5

    # Add minimal JPEG compression artifacts (higher quality)
    quality = random.randint(75, 95)  # Increased from 50-85
    buffer = BytesIO()
    enhancer.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    img = Image.open(buffer)

    return img


# ===== Sample Statement Generation =====

def generate_sample_statement():
    """Generate a sample statement for testing the PDF template"""
    
    # Generate statement date
    statement_date = (
        fake.date_between(start_date="-30d", end_date="today")
        .strftime("%m/%d/%Y")
        .lstrip("0")
        .replace("/0", "/")
    )
    
    # Customer address
    to_address = Address(
        customer_name="LUCKY LAD ENERGY LLC",
        address=f"P O BOX {fake.random_int(1000, 9999)}\nCONROE, TX 77305-1379",
    )
    
    # Vendor info
    vendor_name = "REAGAN POWER COMPRESSION LLC"
    vendor_address = "1347 EVANGELINE THRUWAY\nBROUSSARD, LA 70518"
    
    # Generate aging summary
    aging = AgingSummary(
        current=round(random.uniform(500, 2000), 2),
        past_due_30=round(random.uniform(1000, 15000), 2),
        past_due_60=round(random.uniform(1000, 5000), 2),
        past_due_90=round(random.uniform(1000, 6000), 2),
        over_90=round(random.uniform(500, 2000), 2),
    )
    
    # Generate transactions (10-20 transactions)
    num_transactions = random.randint(10, 20)
    transactions = []
    balance = 0
    
    # Generate well names
    well_names = [
        "10032 Theuvenins Creek",
        "10051 LG #1, SPURGER, TX",
        "10083 DUPLANTIER ESTATE #2",
        "10084 DREYFUS MINERALS #1",
        "10085 DREYFUS MINERALS #2 ALT",
        "10086 JOHNSON BAYOU",
        "10087 GORDON"
    ]
    
    # Assign transactions to wells
    well_assignments = {}
    for i in range(num_transactions):
        well_assignments[i] = random.choice(well_names)
    
    # Sort transactions by well name for grouping
    sorted_assignments = sorted(well_assignments.items(), key=lambda x: x[1])
    
    for i, (trans_idx, well_name) in enumerate(sorted_assignments):
        # Generate transaction date (older for earlier transactions)
        days_ago = 180 - (i * 10)  # Spread transactions over ~6 months
        trans_date = (
            fake.date_between(start_date=f"-{days_ago}d", end_date=f"-{days_ago - 10}d")
            .strftime("%m/%d/%Y")
            .lstrip("0")
            .replace("/0", "/")
        )
        
        # Determine if this is a regular invoice or a credit/reversal
        is_credit = random.random() < 0.2  # 20% chance of being a credit
        
        if is_credit:
            amount = round(random.uniform(-2000, -100), 2)
            transaction_text = (
                f"GENJRNL #{fake.random_int(10, 99)}-{fake.random_int(10, 99)}-{fake.random_int(10, 99)}R. "
                f"Reverse of GJE {fake.random_int(10, 99)}-{fake.random_int(10, 99)}-{fake.random_int(10, 99)} "
                f"Transfer of Credits for\nLUCKY LAD ENERGY LLC from LUCKY LAD ENERGY LLC to {well_name}"
            )
        else:
            amount = round(random.uniform(500, 4000), 2)
            due_date = (
                (
                    datetime.datetime.strptime(
                        trans_date.replace("/", "/").replace(" ", ""), "%m/%d/%Y"
                    )
                    + datetime.timedelta(days=30)
                )
                .strftime("%m/%d/%Y")
                .lstrip("0")
                .replace("/0", "/")
            )
            transaction_text = f"INV #{fake.random_int(1000, 99999)}. Due {due_date}. Orig. Amount ${amount:,.2f}."
        
        # Update balance
        balance += amount
        
        transaction = StatementTransaction(
            date=trans_date,
            transaction=transaction_text,
            amount=amount,
            balance=balance,
            well_name=well_name
        )
        
        transactions.append(transaction)
    
    # Sort transactions by date
    transactions.sort(
        key=lambda x: datetime.datetime.strptime(
            x.date.replace("/", "/").replace(" ", ""), "%m/%d/%Y"
        )
    )
    
    # Create statement
    statement = Statement(
        statement_date=statement_date,
        to=to_address,
        vendor_name=vendor_name,
        vendor_address=vendor_address,
        transactions=transactions,
        aging_summary=aging
    )
    
    return statement


def generate_sample_statement_pdf_and_json():
    """Generate a sample statement PDF and JSON for testing"""
    
    # Generate sample statement data
    statement_data = generate_sample_statement()
    
    # Create unique filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"sample_statement_{timestamp}"
    
    # Create PDF
    pdf_path = f"synthetic_statements/pdf/{base_filename}.pdf"
    create_statement_pdf(statement_data, pdf_path)
    
    # Create JSON
    json_path = f"synthetic_statements/json/{base_filename}.json"
    save_statement_json(statement_data, json_path)
    
    print(f"Generated sample statement PDF: {pdf_path}")
    print(f"Generated sample statement JSON: {json_path}")
    
    # Apply degradation
    degraded_pdf_path = f"synthetic_statements/pdf/{base_filename}_degraded.pdf"
    try:
        degrade_pdf_image(pdf_path, degraded_pdf_path)
        print(f"Generated degraded statement PDF: {degraded_pdf_path}")
    except Exception as e:
        print(f"Error applying degradation: {e}")
        degraded_pdf_path = None
    
    return pdf_path, json_path, degraded_pdf_path
# ===== Batch Generation =====

def generate_synthetic_statements(count=10, include_degradation=True, vendor_types=None):
    """Generate a specified number of synthetic statements with varied data
    
    Args:
        count (int): Number of statements to generate
        include_degradation (bool): Whether to include degraded versions
        vendor_types (list): List of vendor types to include (default: all available types)
        
    Returns:
        list: List of tuples containing (json_path, pdf_path, degraded_pdf_path)
    """
    # Ensure directories exist
    os.makedirs("synthetic_statements/pdf", exist_ok=True)
    os.makedirs("synthetic_statements/json", exist_ok=True)
    
    # Default vendor types
    if vendor_types is None:
        vendor_types = ["reagan", "aegis", "atkinson"]
    
    # Track generated files
    generated_files = []
    
    # Generate statements
    for i in range(count):
        # Select vendor type (if multiple types are specified)
        if len(vendor_types) > 1:
            vendor_type = random.choice(vendor_types)
        else:
            vendor_type = vendor_types[0]
        
        # Generate statement with varied data
        statement_data = generate_varied_statement(vendor_type)
        
        # Create unique filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{vendor_type}_statement_{timestamp}_{i}"
        
        # Save JSON
        json_path = f"synthetic_statements/json/{base_filename}.json"
        save_statement_json(statement_data, json_path)
        
        # Create PDF
        pdf_path = f"synthetic_statements/pdf/{base_filename}.pdf"
        create_statement_pdf(statement_data, pdf_path)
        
        # Apply degradation if requested
        degraded_pdf_path = None
        if include_degradation:
            degraded_pdf_path = f"synthetic_statements/pdf/{base_filename}_degraded.pdf"
            try:
                degrade_pdf_image(pdf_path, degraded_pdf_path)
            except Exception as e:
                print(f"Error applying degradation: {e}")
                degraded_pdf_path = None
        
        # Add to generated files
        generated_files.append((json_path, pdf_path, degraded_pdf_path))
        
        # Print progress
        print(f"Generated {vendor_type} statement {i+1}/{count}: {base_filename}")
    
    return generated_files


def generate_varied_statement(vendor_type="reagan"):
    """Generate a statement with varied data based on vendor type
    
    Args:
        vendor_type (str): Type of vendor (reagan, aegis, atkinson)
        
    Returns:
        Statement: Generated statement data
    """
    # Generate statement date with varied formats
    date_formats = [
        lambda d: d.strftime("%m/%d/%Y").lstrip("0").replace("/0", "/"),
        lambda d: d.strftime("%m-%d-%Y").lstrip("0").replace("-0", "-"),
        lambda d: d.strftime("%B %d, %Y").replace(" 0", " "),
        lambda d: d.strftime("%m/%d/%y").lstrip("0").replace("/0", "/"),
    ]
    
    # Choose a date format (weighted toward standard format)
    date_format = random.choices(
        date_formats,
        weights=[0.7, 0.1, 0.1, 0.1]
    )[0]
    
    statement_date_obj = fake.date_between(start_date="-60d", end_date="today")
    statement_date = date_format(statement_date_obj)
    
    # Generate customer data with variations
    customer_name_formats = [
        "Lucky Lad Energy LLC",
        "LUCKY LAD ENERGY LLC",
        "Lucky Lad Energy, LLC",
        "Lucky Lad Energy L.L.C.",
        "Lucky Lad Energy"
    ]
    customer_name = random.choice(customer_name_formats)
    
    # Address variations
    address_formats = [
        lambda: f"P O BOX {fake.random_int(1000, 9999)}\nCONROE, TX 77305-{fake.random_int(1000, 9999)}",
        lambda: f"PO BOX {fake.random_int(1000, 9999)}\nCONROE, TX 77305",
        lambda: f"{fake.street_address()}\nCONROE, TX 77305",
        lambda: f"{fake.building_number()} {fake.street_name()}\nSuite {fake.random_int(100, 999)}\nCONROE, TX 77305",
    ]
    
    customer_address = random.choice(address_formats)()
    
    # Create customer address object
    to_address = Address(
        customer_name=customer_name,
        address=customer_address,
    )
    
    # Generate vendor info based on vendor type
    if vendor_type == "reagan":
        vendor_name = "REAGAN POWER COMPRESSION LLC"
        vendor_address = "1347 EVANGELINE THRUWAY\nBROUSSARD, LA 70518"
    elif vendor_type == "aegis":
        vendor_name = "AEGIS CHEMICAL SOLUTIONS"
        vendor_address = "1100 LOUISIANA ST\nSUITE 3300\nHOUSTON, TX 77002"
    elif vendor_type == "atkinson":
        vendor_name = "ATKINSON PROPANE CO. INC."
        vendor_address = "1005 N MAIN ST\nLIVINGSTON, TX 77351"
    else:
        # Default to Reagan
        vendor_name = "REAGAN POWER COMPRESSION LLC"
        vendor_address = "1347 EVANGELINE THRUWAY\nBROUSSARD, LA 70518"
    
    # Generate aging summary with realistic variations
    # Vary the distribution of amounts across aging buckets
    aging_patterns = [
        # Mostly current
        lambda: AgingSummary(
            current=round(random.uniform(5000, 15000), 2),
            past_due_30=round(random.uniform(500, 2000), 2),
            past_due_60=round(random.uniform(0, 500), 2),
            past_due_90=round(random.uniform(0, 200), 2),
            over_90=round(random.uniform(0, 100), 2),
        ),
        # Mostly 30 days
        lambda: AgingSummary(
            current=round(random.uniform(500, 2000), 2),
            past_due_30=round(random.uniform(5000, 15000), 2),
            past_due_60=round(random.uniform(500, 2000), 2),
            past_due_90=round(random.uniform(0, 500), 2),
            over_90=round(random.uniform(0, 200), 2),
        ),
        # Distributed across all buckets
        lambda: AgingSummary(
            current=round(random.uniform(1000, 5000), 2),
            past_due_30=round(random.uniform(1000, 5000), 2),
            past_due_60=round(random.uniform(1000, 5000), 2),
            past_due_90=round(random.uniform(1000, 5000), 2),
            over_90=round(random.uniform(1000, 5000), 2),
        ),
        # Mostly older buckets
        lambda: AgingSummary(
            current=round(random.uniform(0, 1000), 2),
            past_due_30=round(random.uniform(500, 2000), 2),
            past_due_60=round(random.uniform(1000, 3000), 2),
            past_due_90=round(random.uniform(2000, 5000), 2),
            over_90=round(random.uniform(5000, 15000), 2),
        ),
    ]
    
    aging = random.choice(aging_patterns)()
    
    # Generate transactions with varied patterns
    # Number of transactions varies by vendor and statement size
    if vendor_type == "reagan":
        num_transactions = random.randint(15, 30)  # Reagan tends to have more transactions
    elif vendor_type == "aegis":
        num_transactions = random.randint(5, 15)   # Aegis has moderate number
    else:
        num_transactions = random.randint(3, 10)   # Atkinson has fewer
    
    # Generate well names with variations
    well_name_patterns = [
        lambda: f"{random.randint(10000, 99999)} {fake.last_name()} Creek",
        lambda: f"{fake.last_name()} {random.randint(1, 9)}",
        lambda: f"{fake.last_name()} {random.choice(['A', 'B', 'C', 'D'])}-{random.randint(1, 99)}",
        lambda: f"Godchaux {random.randint(1, 9)}",
        lambda: f"Kirby {fake.last_name()}",
        lambda: f"{fake.last_name()} {random.choice(['SWD', 'ALT', 'UNIT'])}",
        lambda: f"{fake.city()} {random.choice(['East', 'West', 'North', 'South'])} {random.randint(1, 12)}",
    ]
    
    # Generate a set of well names for this statement
    num_wells = min(random.randint(3, 7), num_transactions)
    well_names = [random.choice(well_name_patterns)() for _ in range(num_wells)]
    
    # Assign transactions to wells
    well_assignments = {}
    for i in range(num_transactions):
        well_assignments[i] = random.choice(well_names)
    
    # Sort transactions by well name for grouping
    sorted_assignments = sorted(well_assignments.items(), key=lambda x: x[1])
    
    # Generate transactions
    transactions = []
    balance = 0
    
    for i, (trans_idx, well_name) in enumerate(sorted_assignments):
        # Generate transaction date (older for earlier transactions)
        days_ago = 180 - (i * 10)  # Spread transactions over ~6 months
        trans_date = (
            fake.date_between(start_date=f"-{days_ago}d", end_date=f"-{days_ago - 10}d")
            .strftime("%m/%d/%Y")
            .lstrip("0")
            .replace("/0", "/")
        )
        
        # Determine transaction type with probabilities
        transaction_types = [
            "invoice",      # Regular invoice
            "credit",       # Credit memo
            "adjustment",   # Adjustment
            "reversal"      # Reversal
        ]
        
        transaction_weights = [0.7, 0.1, 0.1, 0.1]  # 70% invoices, 10% each for others
        transaction_type = random.choices(transaction_types, weights=transaction_weights)[0]
        
        # Generate transaction details based on type
        if transaction_type == "invoice":
            amount = round(random.uniform(500, 4000), 2)
            due_date = (
                (
                    datetime.datetime.strptime(
                        trans_date.replace("/", "/").replace(" ", ""), "%m/%d/%Y"
                    )
                    + datetime.timedelta(days=30)
                )
                .strftime("%m/%d/%Y")
                .lstrip("0")
                .replace("/0", "/")
            )
            transaction_text = f"INV #{fake.random_int(1000, 99999)}. Due {due_date}. Orig. Amount ${amount:,.2f}."
            
            # Sometimes add additional details
            if random.random() < 0.3:
                transaction_text += f" PO #{fake.random_int(10000, 99999)}"
        
        elif transaction_type == "credit":
            amount = round(random.uniform(-2000, -100), 2)
            transaction_text = f"Credit Memo #{fake.random_int(1000, 9999)}. Amount ${abs(amount):,.2f}."
        
        elif transaction_type == "adjustment":
            # Adjustments can be positive or negative
            if random.random() < 0.5:
                amount = round(random.uniform(50, 500), 2)
                transaction_text = f"Adjustment #{fake.random_int(100, 999)}. Price correction ${amount:,.2f}."
            else:
                amount = round(random.uniform(-500, -50), 2)
                transaction_text = f"Adjustment #{fake.random_int(100, 999)}. Service credit ${abs(amount):,.2f}."
        
        else:  # reversal
            amount = round(random.uniform(-2000, -100), 2)
            transaction_text = (
                f"GENJRNL #{fake.random_int(10, 99)}-{fake.random_int(10, 99)}-{fake.random_int(10, 99)}R. "
                f"Reverse of GJE {fake.random_int(10, 99)}-{fake.random_int(10, 99)}-{fake.random_int(10, 99)} "
                f"Transfer of Credits for\n{customer_name} from {customer_name} to {well_name}"
            )
        
        # Update balance
        balance += amount
        
        transaction = StatementTransaction(
            date=trans_date,
            transaction=transaction_text,
            amount=amount,
            balance=balance,
            well_name=well_name
        )
        
        transactions.append(transaction)
    
    # Sort transactions by date
    transactions.sort(
        key=lambda x: datetime.datetime.strptime(
            x.date.replace("/", "/").replace(" ", ""), "%m/%d/%Y"
        )
    )
    
    # Create statement
    statement = Statement(
        statement_date=statement_date,
        to=to_address,
        vendor_name=vendor_name,
        vendor_address=vendor_address,
        transactions=transactions,
        aging_summary=aging
    )
    
    return statement


def validate_generated_dataset(generated_files, output_report=None):
    """Validate a generated dataset of statements
    
    Args:
        generated_files (list): List of tuples containing (json_path, pdf_path, degraded_pdf_path)
        output_report (str): Path to save validation report (optional)
        
    Returns:
        dict: Validation results
    """
    validation_results = {
        "total_files": len(generated_files),
        "valid_json": 0,
        "valid_pdf": 0,
        "valid_degraded": 0,
        "errors": []
    }
    
    for i, (json_path, pdf_path, degraded_pdf_path) in enumerate(generated_files):
        # Validate JSON
        try:
            with open(json_path, "r") as f:
                json_data = json.load(f)
                
            # Check required fields
            required_fields = [
                "metadata", "vendor_information", "customer_information", 
                "statement_details", "aging_summary", "transactions"
            ]
            
            json_valid = all(field in json_data for field in required_fields)
            
            if json_valid:
                validation_results["valid_json"] += 1
            else:
                missing_fields = [field for field in required_fields if field not in json_data]
                validation_results["errors"].append(f"JSON missing fields: {missing_fields} in {json_path}")
        
        except Exception as e:
            validation_results["errors"].append(f"JSON error in {json_path}: {str(e)}")
        
        # Validate PDF
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            validation_results["valid_pdf"] += 1
        else:
            validation_results["errors"].append(f"PDF invalid or missing: {pdf_path}")
        
        # Validate degraded PDF if it exists
        if degraded_pdf_path and os.path.exists(degraded_pdf_path) and os.path.getsize(degraded_pdf_path) > 0:
            validation_results["valid_degraded"] += 1
        elif degraded_pdf_path:
            validation_results["errors"].append(f"Degraded PDF invalid or missing: {degraded_pdf_path}")
        
        # Print progress for large datasets
        if (i + 1) % 10 == 0 or i == len(generated_files) - 1:
            print(f"Validated {i + 1}/{len(generated_files)} files")
    
    # Calculate success rates
    validation_results["json_success_rate"] = validation_results["valid_json"] / validation_results["total_files"] * 100
    validation_results["pdf_success_rate"] = validation_results["valid_pdf"] / validation_results["total_files"] * 100
    
    if any(f[2] for f in generated_files):
        degraded_count = sum(1 for f in generated_files if f[2])
        validation_results["degraded_success_rate"] = validation_results["valid_degraded"] / degraded_count * 100
    
    # Save report if requested
    if output_report:
        with open(output_report, "w") as f:
            json.dump(validation_results, f, indent=2)
    
    return validation_results


def print_document_ai_setup_instructions():
    """Print instructions for setting up a Document AI processor for statements"""
    print("\nFor detailed instructions on setting up a Document AI processor for statements, see:")
    print("Documentation/DOCUMENT_AI_STATEMENT_PROCESSOR_SETUP.md\n")


# ===== Main Execution =====

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate synthetic statements for Document AI training"
    )
    parser.add_argument(
        "--sample", action="store_true", help="Generate a sample statement PDF and JSON"
    )
    parser.add_argument(
        "--validate-schema", action="store_true", help="Validate the JSON schema"
    )
    parser.add_argument(
        "--batch", type=int, default=0, help="Generate a batch of statements (specify count)"
    )
    parser.add_argument(
        "--vendor", type=str, choices=["reagan", "aegis", "atkinson", "all"], 
        default="all", help="Vendor type for statement generation"
    )
    parser.add_argument(
        "--no-degradation", action="store_true", help="Skip degradation step"
    )
    parser.add_argument(
        "--validate", action="store_true", help="Validate generated files"
    )
    parser.add_argument(
        "--output-report", type=str, help="Path to save validation report"
    )
    parser.add_argument(
        "--setup-instructions", action="store_true", 
        help="Print Document AI processor setup instructions"
    )
    
    args = parser.parse_args()
    
    if args.setup_instructions:
        print_document_ai_setup_instructions()
    elif args.sample:
        pdf_path, json_path, degraded_pdf_path = generate_sample_statement_pdf_and_json()
        print("\nSample statement generation complete!")
        print(f"PDF saved to: {pdf_path}")
        print(f"JSON saved to: {json_path}")
        if degraded_pdf_path:
            print(f"Degraded PDF saved to: {degraded_pdf_path}")
    elif args.validate_schema:
        try:
            import jsonschema
            
            # Generate a sample statement
            statement_data = generate_sample_statement()
            
            # Generate JSON
            json_content = generate_statement_json(statement_data)
            json_data = json.loads(json_content)
            
            # Validate against schema
            jsonschema.validate(instance=json_data, schema=STATEMENT_JSON_SCHEMA)
            
            print("JSON schema validation successful!")
        except ImportError:
            print("jsonschema package not installed. Please install it with: pip install jsonschema")
        except Exception as e:
            print(f"Schema validation error: {e}")
    elif args.batch > 0:
        print(f"Generating {args.batch} synthetic statements...")
        
        # Determine vendor types
        if args.vendor == "all":
            vendor_types = ["reagan", "aegis", "atkinson"]
        else:
            vendor_types = [args.vendor]
        
        # Generate batch
        generated_files = generate_synthetic_statements(
            count=args.batch,
            include_degradation=not args.no_degradation,
            vendor_types=vendor_types
        )
        
        # Validate if requested
        if args.validate:
            print("\nValidating generated files...")
            validation_results = validate_generated_dataset(
                generated_files,
                output_report=args.output_report
            )
            
            print("\nValidation Results:")
            print(f"Total files: {validation_results['total_files']}")
            print(f"Valid JSON: {validation_results['valid_json']} ({validation_results['json_success_rate']:.1f}%)")
            print(f"Valid PDF: {validation_results['valid_pdf']} ({validation_results['pdf_success_rate']:.1f}%)")
            
            if any(f[2] for f in generated_files):
                print(f"Valid degraded PDFs: {validation_results['valid_degraded']} ({validation_results['degraded_success_rate']:.1f}%)")
            
            if validation_results["errors"]:
                print(f"\nFound {len(validation_results['errors'])} errors:")
                for i, error in enumerate(validation_results["errors"][:5]):
                    print(f"  {i+1}. {error}")
                
                if len(validation_results["errors"]) > 5:
                    print(f"  ... and {len(validation_results['errors']) - 5} more errors")
                
                if args.output_report:
                    print(f"\nFull error details saved to: {args.output_report}")
        
        print("\nBatch generation complete!")
        print(f"JSON files saved to: synthetic_statements/json/")
        print(f"PDF files saved to: synthetic_statements/pdf/")
    else:
        print("Please specify an action. Use --sample, --batch, --validate-schema, or --setup-instructions.")