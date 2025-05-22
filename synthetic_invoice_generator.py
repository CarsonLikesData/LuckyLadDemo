"""
Synthetic Invoice Generator for Lucky Lad Energy
------------------------------------------------
A tool to generate realistic oil & gas invoices for training and testing purposes.

This generator creates synthetic invoices that mimic the structure and appearance
of real invoices from vendors like Reagan Power, Aegis Chemical, and Atkinson Propane.
"""

import os
import json
import random
import datetime
from typing import List, Dict, Optional, Union

# Data generation
from faker import Faker
from faker.providers import BaseProvider

# PDF generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

# Image processing for degradation
from PIL import Image, ImageFilter, ImageOps
import numpy as np

# Data validation
from pydantic import BaseModel, field_validator, model_validator

# Template rendering
from jinja2 import Template

# Create directories if they don't exist
os.makedirs("synthetic_invoices/pdf", exist_ok=True)
os.makedirs("synthetic_invoices/json", exist_ok=True)
os.makedirs("synthetic_invoices/templates", exist_ok=True)

# Initialize Faker
fake = Faker()
# ===== Custom Faker Providers =====


class OilGasProvider(BaseProvider):
    """Custom provider for oil and gas industry terms and patterns"""

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
            lambda: f"{fake.company()} {fake.random_element(['Exploration', 'Production'])} #{fake.random_int(100, 999)}",
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

    def product_code(self) -> str:
        """Generate a realistic product code"""
        prefixes = ["CS", "SS", "PS", "DS", "OLA", "CH", "FS", "MS", "TS", "WS"]
        patterns = [
            lambda: f"{random.choice(prefixes)}-{fake.random_int(100, 9999)}",
            lambda: f"{random.choice(prefixes)}{fake.random_int(10, 999)}",
            lambda: f"{random.choice(prefixes)}/{fake.random_int(100, 999)}-{fake.random_letter().upper()}{fake.random_int(1, 99)}",
            lambda: f"{fake.random_int(10, 99)}-{random.choice(prefixes)}-{fake.random_int(1000, 9999)}",
            lambda: f"{random.choice(prefixes)}{fake.random_letter().upper()}{fake.random_letter().upper()}-{fake.random_int(100, 999)}"
        ]
        return random.choice(patterns)()

    def product_name(self) -> str:
        """Generate a realistic product name"""
        base_products = [
            "Corr-Shield CS-1148",
            "SCALE-SHIELD SS-728",
            "Phase Shield PS-653M",
            "D-SHIELD DS-129",
            "OLA-905 (Oil - Low Ash)",
            "Methanol",
            "METHANOL",
            "Propane",
            "Seats",
            "Darts",
            "Kit Repair Viton",
            "Cylinder",
            "Assy Rod Piston",
            "Inhibitor Solution",
            "Demulsifier",
            "Paraffin Treatment",
            "Biocide Formula",
            "Oxygen Scavenger",
            "H2S Scavenger",
            "Valve Assembly",
            "Pressure Regulator",
            "Flow Control Unit",
            "Compression Fitting",
            "Wellhead Component"
        ]
        
        # Sometimes add modifiers or specifications
        product = random.choice(base_products)
        
        # 30% chance to add a specification
        if random.random() < 0.3:
            specs = [
                f"Type {fake.random_letter().upper()}",
                f"Grade {random.choice(['A', 'B', 'C', 'Industrial', 'Commercial'])}",
                f"{random.choice(['High', 'Low', 'Medium'])}-Pressure",
                f"{random.choice(['Standard', 'Premium', 'Economy'])} Model",
                f"{random.choice(['1/4', '1/2', '3/4', '1', '2'])} inch"
            ]
            product = f"{product} {random.choice(specs)}"
            
        # 20% chance to add a brand name
        if random.random() < 0.2:
            brands = ["ChemTech", "PetroSol", "OilMaster", "WellGuard", "FlowPro", "EnerChem"]
            product = f"{random.choice(brands)} {product}"
            
        return product

    def tank_serial_number(self) -> str:
        """Generate a tank serial number"""
        return str(fake.random_int(100000000, 999999999))

    def tank_size(self) -> str:
        """Generate a tank size"""
        return str(random.choice([250, 320, 500, 1000]))

    def tank_percentage(self) -> str:
        """Generate a tank percentage"""
        return str(fake.random_int(1, 95))

    def po_box(self) -> str:
        """Generate a PO Box address"""
        return f"PO Box {fake.random_int(1000, 9999)}"

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
        
    def payment_terms(self) -> str:
        """Generate payment terms"""
        terms = [
            "Net 30",
            "Net 45",
            "Net 60",
            "2/10 Net 30",
            "Due on Receipt",
            "COD",
            "Net 15",
            "Net 30 EOM",
            "50% Advance, 50% Net 30"
        ]
        return random.choice(terms)


# Register the custom provider
fake.add_provider(OilGasProvider)
# ===== Data Models =====


class Address(BaseModel):
    """Model for address information"""

    customer_name: str
    attention: Optional[str] = None
    address: str


class LineItem(BaseModel):
    """Model for invoice line items"""

    well_name: Optional[str] = None
    item: str
    description: str
    unit: str = "GAL"
    quantity: Union[int, float, str]
    unit_price: Union[float, str]
    total_price: Optional[Union[float, str]] = None

    @field_validator("quantity")
    def validate_quantity(cls, v):
        if isinstance(v, str):
            try:
                return float(v.replace(",", ""))
            except ValueError:
                pass
        return v

    @field_validator("unit_price")
    def validate_unit_price(cls, v: Union[str, float, int]) -> float:
        """Validates and normalizes unit_price values. Handles:
        - String/numeric inputs
        - Comma separation
        - Negative values
        - Detailed error reporting
        """
        # Handle numeric types directly
        if isinstance(v, (int, float)):
            if v < 0:
                raise ValueError("Unit price cannot be negative")
            return float(v)
        
        # Handle string inputs
        elif isinstance(v, str):
            # Remove currency symbols and whitespace
            cleaned_value = v.strip()
            
            # Check for negative sign before removing currency symbol
            is_negative = cleaned_value.startswith('-')
            
            # Remove currency symbol if present
            if cleaned_value.startswith('$') or cleaned_value.startswith('-$'):
                cleaned_value = cleaned_value.replace('$', '', 1)
            
            # Remove commas for number formatting
            cleaned_value = cleaned_value.replace(",", "")
            
            try:
                # Convert to float
                float_value = float(cleaned_value)
                
                # Check for negative values
                if float_value < 0 or is_negative:
                    raise ValueError("Unit price cannot be negative")
                
                return float_value
            except ValueError as e:
                # Check if this was our own negative value error
                if "cannot be negative" in str(e):
                    raise
                # Otherwise it's a format error
                raise ValueError(f"Invalid unit price format: '{v}'. Expected a numeric value.")
        
        # Handle invalid types
        else:
            raise ValueError(f"Unit price must be a number or string, got {type(v).__name__}")

    @model_validator(mode="after")
    def calculate_total_price(self):
        quantity = self.quantity
        unit_price = self.unit_price
        total_price = self.total_price

        if quantity is not None and unit_price is not None and total_price is None:
            if isinstance(quantity, (int, float)) and isinstance(
                unit_price, (int, float)
            ):
                self.total_price = round(quantity * unit_price, 2)

        return self


class Invoice(BaseModel):
    """Base model for all invoice types"""

    invoice_number: str
    invoice_date: str
    due_date: Optional[str] = None
    customer_id: Optional[str] = None
    lease_name: Optional[str] = None
    well_name: Optional[str] = None
    property_no: Optional[str] = None
    afe_po_no: Optional[str] = None
    area: Optional[str] = None
    service_date: Optional[str] = None
    order_no: Optional[str] = None
    sales_person: Optional[str] = None
    bill_to: Address
    ship_to: Optional[Address] = None
    line_items: List[LineItem]
    amount_subject_to_sales_tax: Optional[Union[float, str]] = None
    amount_exempt_from_sales_tax: Optional[Union[float, str]] = "0.00"
    subtotal: Optional[Union[float, str]] = None
    invoice_discount: Optional[Union[float, str]] = "0.00"
    total_sales_tax: Optional[Union[float, str]] = None
    total: Optional[Union[float, str]] = None
    # Fields for Atkinson Propane
    tank_serial_number: Optional[str] = None
    tank_size: Optional[str] = None
    before_percentage: Optional[str] = None
    after_percentage: Optional[str] = None

    @model_validator(mode="after")
    def calculate_totals(self):
        line_items = self.line_items

        if line_items:
            # Calculate subtotal
            subtotal = sum(
                item.total_price for item in line_items if item.total_price is not None
            )
            self.subtotal = subtotal

            # Calculate tax (8.25%)
            tax_rate = 0.0825
            tax = round(subtotal * tax_rate, 2)
            self.total_sales_tax = tax

            # Calculate total
            self.total = subtotal + tax

            # Set amount subject to sales tax
            self.amount_subject_to_sales_tax = subtotal

        return self


class Statement(BaseModel):
    """Model for statement data"""

    statement_date: str
    to: Address
    transactions: List[Dict[str, str]]

    class Config:
        arbitrary_types_allowed = True


# ===== Template Definitions =====

# Reagan Power template
REAGAN_POWER_TEMPLATE = """
{
  "header": {
    "vendor": "Reagan Power Compression LLC",
    "client": "{{ bill_to.customer_name }}",
    "statement_date": "{{ invoice_date }}"
  },
  "line_items": [
    {% for item in line_items %}
    {
      "product_code": "{{ item.item }}",
      "description": "{{ item.description|replace('\n', ' ') }}",
      "quantity": {{ item.quantity }},
      "price": {{ item.unit_price }}
    }{% if not loop.last %},{% endif %}
    {% endfor %}
  ],
  "subtotal": "{{ subtotal }}",
  "tax": "{{ total_sales_tax }}",
  "total": "{{ total }}"
}
"""

# Aegis Chemical template
AEGIS_CHEMICAL_TEMPLATE = """
{
  "invoice_number": "{{ invoice_number }}",
  "invoice_date": "{{ invoice_date }}",
  "due_date": "{{ due_date }}",
  "bill_to": {
    "customer_name": "{{ bill_to.customer_name }}",
    "address": "{{ bill_to.address|replace('\n', ' ') }}"
  },
  "ship_to": {
    "customer_name": "{{ ship_to.customer_name if ship_to else '' }}",
    "address": "{{ ship_to.address|replace('\n', ' ') if ship_to else '' }}"
  },
  "line_items": [
    {% for item in line_items %}
    {
      "well_name": "{{ item.well_name if item.well_name else '' }}",
      "item": "{{ item.item }}",
      "description": "{{ item.description }}",
      "quantity": {{ item.quantity }},
      "unit_price": {{ item.unit_price }},
      "total_price": {{ item.total_price if item.total_price else (item.quantity * item.unit_price) }}
    }{% if not loop.last %},{% endif %}
    {% endfor %}
  ],
  "subtotal": "{{ subtotal }}",
  "tax": "{{ total_sales_tax }}",
  "total": "{{ total }}"
}
"""

# Atkinson Propane template
ATKINSON_PROPANE_TEMPLATE = """
{
  "invoice_number": "{{ invoice_number }}",
  "date": "{{ invoice_date }}",
  "sold_to": "{{ bill_to.customer_name }} {{ bill_to.address|replace('\n', ' ') }}",
  "gallons": "{{ line_items[0].quantity }}",
  "price_per_gal": "{{ line_items[0].unit_price }}",
  "amount": "{{ line_items[0].total_price }}",
  "tax": "{{ total_sales_tax }}",
  "total_payment_due": "{{ total }}",
  "tank_serial_number": "{{ tank_serial_number }}",
  "tank_size": "{{ tank_size }}",
  "before_percentage": "{{ before_percentage }}",
  "after_percentage": "{{ after_percentage }}"
}
"""
# ===== Generator Functions =====


def generate_invoice_data(template_type="aegis"):
    """Generate random invoice data based on template type"""

    # Common data
    # Randomize date format occasionally
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
    
    invoice_date_obj = fake.date_between(start_date="-60d", end_date="today")
    invoice_date = date_format(invoice_date_obj)
    
    # Randomize due date calculation (15-45 days)
    payment_days = random.choice([15, 30, 45])
    due_date_obj = invoice_date_obj + datetime.timedelta(days=payment_days)
    due_date = date_format(due_date_obj)

    # Generate customer data with more variations
    customer_name_formats = [
        "Lucky Lad Energy LLC",
        "LUCKY LAD ENERGY LLC",
        "Lucky Lad Energy, LLC",
        "Lucky Lad Energy L.L.C.",
        "Lucky Lad Energy"
    ]
    customer_name = random.choice(customer_name_formats)
    
    attention_options = [None, "Richard Hopper", "R. Hopper", "Accounts Payable", "A/P Department"]
    
    # Address variations
    address_formats = [
        lambda: f"{fake.po_box()}\nConroe, TX 77305\nUSA",
        lambda: f"{fake.po_box()}\nConroe, TX 77305",
        lambda: f"{fake.street_address()}\nConroe, TX 77305",
        lambda: f"{fake.building_number()} {fake.street_name()}\nSuite {fake.random_int(100, 999)}\nConroe, TX 77305",
    ]
    
    bill_to = Address(
        customer_name=customer_name,
        attention=random.choice(attention_options),
        address=random.choice(address_formats)(),
    )

    ship_to_formats = [
        lambda: f"{fake.well_name()} Tank Battery",
        lambda: f"{fake.well_name()} Site",
        lambda: f"Field Office: {fake.field_name()}",
        lambda: f"{fake.street_address()}\nConroe, TX 77305",
        lambda: f"Well Site {fake.random_int(1000, 9999)}\n{fake.field_name()} Field",
    ]
    
    ship_to = Address(
        customer_name=customer_name,
        attention=random.choice(attention_options),
        address=random.choice(ship_to_formats)(),
    )

    # Generate line items with more variations
    num_items = random.randint(1, 10)  # Increased max items
    line_items = []

    # Available units with weighted probabilities
    units = ["GAL", "LBS", "EA", "BOX", "UNIT", "HR", "DAY", "FT", "BBL"]
    unit_weights = [0.5, 0.1, 0.2, 0.05, 0.05, 0.03, 0.02, 0.03, 0.02]

    for _ in range(num_items):
        well_name = fake.well_name() if random.random() < 0.8 else None  # Sometimes omit well name
        product_code = fake.product_code()
        product_name = fake.product_name()
        
        # More varied quantities and prices
        if random.random() < 0.1:  # 10% chance for decimal quantities
            quantity = round(random.uniform(0.5, 100.0), 2)
        else:
            quantity = random.randint(1, 1000)
            
        # Occasionally use very specific quantities
        if random.random() < 0.05:
            quantity = round(quantity + random.uniform(0.01, 0.99), 2)
            
        # More varied pricing
        price_tier = random.choice([
            lambda: round(random.uniform(0.5, 5.0), 2),     # Low price tier
            lambda: round(random.uniform(5.0, 50.0), 2),    # Medium price tier
            lambda: round(random.uniform(50.0, 500.0), 2),  # High price tier
        ])
        unit_price = price_tier()
        
        # Select unit with weighted probability
        unit = random.choices(units, weights=unit_weights)[0]

        line_item = LineItem(
            well_name=well_name,
            item=product_code,
            description=product_name,
            unit=unit,
            quantity=quantity,
            unit_price=unit_price,
        )
        line_items.append(line_item)

    # Create invoice based on template type
    if template_type == "reagan":
        # Add more variation to Reagan Power invoices
        customer_id_formats = [
            "LUCK001",
            "LL-001",
            "LUCKY-1",
            f"LL{fake.random_int(1000, 9999)}",
            f"CUST-{fake.random_int(100, 999)}"
        ]
        
        service_date_obj = fake.date_between(start_date="-10d", end_date="today")
        service_date = date_format(service_date_obj)
        
        invoice = Invoice(
            invoice_number=fake.invoice_number(),
            invoice_date=invoice_date,
            due_date=due_date,
            customer_id=random.choice(customer_id_formats),
            lease_name=fake.field_name(),
            area=fake.field_name(),
            service_date=service_date,
            sales_person=fake.name(),
            bill_to=bill_to,
            ship_to=ship_to,
            line_items=line_items,
            afe_po_no=random.choice([None, f"PO-{fake.random_int(10000, 99999)}", f"AFE#{fake.random_int(1000, 9999)}"]),
            property_no=random.choice([None, f"PROP-{fake.random_int(100, 999)}"]),
        )

    elif template_type == "atkinson":
        # Atkinson Propane with more variations
        propane_descriptions = [
            "Propane Delivery",
            "Propane - Residential",
            "Propane - Commercial",
            "Propane Gas Delivery",
            "LP Gas",
            "Propane Refill",
            "Bulk Propane Delivery"
        ]
        
        propane_items = [
            "PROPANE",
            "LP-GAS",
            "PROP-COM",
            "PROP-RES",
            "LP-BULK"
        ]
        
        # Sometimes add multiple line items for Atkinson
        num_propane_items = random.choices([1, 2, 3], weights=[0.8, 0.15, 0.05])[0]
        propane_line_items = []
        
        for i in range(num_propane_items):
            propane_line_item = LineItem(
                item=random.choice(propane_items),
                description=random.choice(propane_descriptions),
                unit="GAL",
                quantity=random.randint(50, 800),
                unit_price=round(random.uniform(2.0, 4.5), 2),
            )
            propane_line_items.append(propane_line_item)
            
        # Sometimes add service items
        if random.random() < 0.3:
            service_items = [
                ("DELIVERY", "Delivery Fee", "EA", 1, random.randint(15, 50)),
                ("SAFETY", "Safety Inspection", "EA", 1, random.randint(30, 100)),
                ("REGULATOR", "Regulator Replacement", "EA", random.randint(1, 2), random.randint(40, 120)),
                ("LABOR", "Service Labor", "HR", random.randint(1, 3), random.randint(65, 95))
            ]
            
            service_item = random.choice(service_items)
            service_line_item = LineItem(
                item=service_item[0],
                description=service_item[1],
                unit=service_item[2],
                quantity=service_item[3],
                unit_price=service_item[4],
            )
            propane_line_items.append(service_line_item)

        invoice = Invoice(
            invoice_number=fake.invoice_number(),
            invoice_date=invoice_date,
            due_date=random.choice([None, due_date]),  # Sometimes include due date
            bill_to=bill_to,
            line_items=propane_line_items,
        )

        # Add propane-specific fields
        invoice.tank_serial_number = fake.tank_serial_number()
        invoice.tank_size = fake.tank_size()
        invoice.before_percentage = fake.tank_percentage()
        invoice.after_percentage = str(
            min(int(invoice.before_percentage) + random.randint(40, 80), 95)
        )

    else:  # Default to Aegis Chemical
        # More variation for Aegis Chemical invoices
        service_date_obj = fake.date_between(start_date="-10d", end_date="today")
        service_date = date_format(service_date_obj)
        
        # Sometimes include order number and other optional fields
        order_no = random.choice([None, f"ORD-{fake.random_int(10000, 99999)}", f"SO#{fake.random_int(1000, 9999)}"])
        
        # Occasionally add discount
        invoice_discount = 0.0
        if random.random() < 0.2:  # 20% chance for discount
            invoice_discount = round(random.uniform(50, 500), 2)
        
        invoice = Invoice(
            invoice_number=fake.invoice_number(),
            invoice_date=invoice_date,
            due_date=due_date,
            customer_id=random.choice(["LUCK001", "LL-001", "LUCKY-1", f"CUST-{fake.random_int(100, 999)}"]),
            lease_name=fake.field_name(),
            well_name=fake.well_name(),
            area=fake.field_name(),
            service_date=service_date,
            sales_person=fake.name(),
            bill_to=bill_to,
            ship_to=ship_to,
            line_items=line_items,
            order_no=order_no,
            afe_po_no=random.choice([None, f"PO-{fake.random_int(10000, 99999)}"]),
            invoice_discount=invoice_discount if invoice_discount > 0 else "0.00",
        )

    return invoice


def generate_statement_data():
    """Generate random statement data"""

    statement_date = (
        fake.date_between(start_date="-30d", end_date="today")
        .strftime("%m/%d/%Y")
        .lstrip("0")
        .replace("/0", "/")
    )

    # Customer address
    to_address = Address(
        customer_name="LUCKY LAD ENERGY LLC",
        address=f"PO BOX {fake.random_int(1000, 9999)}\nCONROE, TX 77305-1379",
    )

    # Generate transactions (3-10 transactions)
    num_transactions = random.randint(3, 10)
    transactions = []
    balance = 0

    for i in range(num_transactions):
        # Generate transaction date (older for earlier transactions)
        days_ago = 180 - (i * 15)  # Spread transactions over ~6 months
        trans_date = (
            fake.date_between(start_date=f"-{days_ago}d", end_date=f"-{days_ago - 15}d")
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
                f"Transfer of Credits for\nLUCKY LAD ENERGY LLC from LUCKY LAD ENERGY LLC to {fake.well_name()}"
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

            # Sometimes add a well name
            if random.random() < 0.3:
                transaction_text += f"\n{fake.well_name()}-"

        # Update balance
        balance += amount

        transaction = {
            "date": trans_date,
            "transaction": transaction_text,
            "amount": f"{amount:,.2f}",
            "balance": f"{balance:,.2f}",
        }

        transactions.append(transaction)

    # Sort transactions by date
    transactions.sort(
        key=lambda x: datetime.datetime.strptime(
            x["date"].replace("/", "/").replace(" ", ""), "%m/%d/%Y"
        )
    )

    # Create statement
    statement = Statement(
        statement_date=statement_date, to=to_address, transactions=transactions
    )

    return statement


def render_template(template_str, data):
    """Render a Jinja2 template with the provided data"""
    template = Template(template_str)
    return template.render(**data.model_dump())


def generate_invoice_json(template_type="aegis"):
    """Generate a JSON invoice based on template type"""
    invoice_data = generate_invoice_data(template_type)

    if template_type == "reagan":
        template_str = REAGAN_POWER_TEMPLATE
    elif template_type == "atkinson":
        template_str = ATKINSON_PROPANE_TEMPLATE
    else:  # Default to Aegis
        template_str = AEGIS_CHEMICAL_TEMPLATE

    rendered_json = render_template(template_str, invoice_data)
    return rendered_json, invoice_data


def generate_statement_json():
    """Generate a JSON statement"""
    statement_data = generate_statement_data()
    # For statements, we'll just convert the model to JSON directly
    return json.dumps(statement_data.model_dump(), indent=2), statement_data


# ===== PDF Generation =====


def create_invoice_pdf(invoice_data, output_path, template_type="aegis"):
    """Create a PDF invoice based on the template type and invoice data"""

    # Create a PDF document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )

    # Styles
    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    subtitle_style = styles["Heading2"]
    normal_style = styles["Normal"]

    # Create content elements
    elements = []

    if template_type == "reagan":
        # Reagan Power Compression LLC invoice
        elements.append(Paragraph("REAGAN POWER COMPRESSION LLC", title_style))
        elements.append(Spacer(1, 12))
        elements.append(
            Paragraph(f"STATEMENT DATE: {invoice_data.invoice_date}", subtitle_style)
        )
        elements.append(Spacer(1, 12))

        # Customer info
        elements.append(Paragraph("BILL TO:", subtitle_style))
        elements.append(Paragraph(invoice_data.bill_to.customer_name, normal_style))
        elements.append(Paragraph(invoice_data.bill_to.address, normal_style))
        elements.append(Spacer(1, 24))

        # Line items
        data = [["PRODUCT CODE", "DESCRIPTION", "QUANTITY", "PRICE", "AMOUNT"]]

        for item in invoice_data.line_items:
            amount = item.quantity * item.unit_price
            data.append(
                [
                    item.item,
                    item.description,
                    f"{item.quantity}",
                    f"${item.unit_price:.2f}",
                    f"${amount:.2f}",
                ]
            )

        # Add totals
        data.append(["", "", "", "SUBTOTAL:", f"${invoice_data.subtotal:.2f}"])
        data.append(
            ["", "", "", "TAX (8.25%):", f"${invoice_data.total_sales_tax:.2f}"]
        )
        data.append(["", "", "", "TOTAL DUE:", f"${invoice_data.total:.2f}"])

        # Create table
        table = Table(data, colWidths=[80, 180, 70, 70, 80])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ]
            )
        )

        elements.append(table)

    elif template_type == "atkinson":
        # Atkinson Propane invoice
        elements.append(Paragraph("ATKINSON PROPANE CO. INC.", title_style))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"DATE: {invoice_data.invoice_date}", subtitle_style))
        elements.append(
            Paragraph(f"INVOICE #: {invoice_data.invoice_number}", subtitle_style)
        )
        elements.append(Spacer(1, 12))

        # Customer info
        elements.append(Paragraph("SOLD TO:", subtitle_style))
        elements.append(Paragraph(invoice_data.bill_to.customer_name, normal_style))
        elements.append(Paragraph(invoice_data.bill_to.address, normal_style))
        elements.append(Spacer(1, 24))

        # Tank info
        tank_info = [
            ["TANK SERIAL NUMBER", "TANK SIZE", "BEFORE %", "AFTER %"],
            [
                invoice_data.tank_serial_number,
                invoice_data.tank_size,
                invoice_data.before_percentage,
                invoice_data.after_percentage,
            ],
        ]

        tank_table = Table(tank_info, colWidths=[120, 120, 120, 120])
        tank_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("ALIGN", (0, 1), (-1, -1), "CENTER"),
                ]
            )
        )

        elements.append(tank_table)
        elements.append(Spacer(1, 24))

        # Delivery info
        delivery_info = [
            ["GALLONS", "PRICE/GAL", "AMOUNT"],
            [
                f"{invoice_data.line_items[0].quantity}",
                f"${invoice_data.line_items[0].unit_price:.2f}",
                f"${invoice_data.line_items[0].total_price:.2f}",
            ],
        ]

        delivery_table = Table(delivery_info, colWidths=[160, 160, 160])
        delivery_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("ALIGN", (0, 1), (-1, -1), "CENTER"),
                ]
            )
        )

        elements.append(delivery_table)
        elements.append(Spacer(1, 24))

        # Totals
        totals_info = [
            ["TAX", "TOTAL PAYMENT DUE"],
            [f"${invoice_data.total_sales_tax:.2f}", f"${invoice_data.total:.2f}"],
        ]

        totals_table = Table(totals_info, colWidths=[240, 240])
        totals_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("ALIGN", (0, 1), (-1, -1), "CENTER"),
                ]
            )
        )

        elements.append(totals_table)

    else:  # Default to Aegis Chemical
        # Aegis Chemical invoice
        elements.append(Paragraph("AEGIS CHEMICAL SOLUTIONS", title_style))
        elements.append(Spacer(1, 12))
        elements.append(
            Paragraph(f"INVOICE #: {invoice_data.invoice_number}", subtitle_style)
        )
        elements.append(Paragraph(f"DATE: {invoice_data.invoice_date}", subtitle_style))
        elements.append(Paragraph(f"DUE DATE: {invoice_data.due_date}", subtitle_style))
        elements.append(Spacer(1, 12))

        # Customer info
        bill_to_para = Paragraph(
            f"BILL TO:<br/>{invoice_data.bill_to.customer_name}<br/>{invoice_data.bill_to.address.replace(chr(10), '<br/>')}",
            normal_style,
        )

        ship_to_text = "SHIP TO:<br/>"
        if invoice_data.ship_to:
            ship_to_text += f"{invoice_data.ship_to.customer_name}<br/>{invoice_data.ship_to.address.replace(chr(10), '<br/>')}"
        else:
            ship_to_text += "Same as billing"
        ship_to_para = Paragraph(ship_to_text, normal_style)

        # Create a table for the addresses
        address_data = [[bill_to_para, ship_to_para]]
        address_table = Table(address_data, colWidths=[240, 240])
        address_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )

        elements.append(address_table)
        elements.append(Spacer(1, 24))

        # Line items
        data = [["WELL", "ITEM", "DESCRIPTION", "QTY", "UNIT PRICE", "AMOUNT"]]

        for item in invoice_data.line_items:
            data.append(
                [
                    item.well_name or "",
                    item.item,
                    item.description,
                    f"{item.quantity}",
                    f"${item.unit_price:.2f}",
                    f"${item.total_price:.2f}",
                ]
            )

        # Add totals
        data.append(["", "", "", "", "SUBTOTAL:", f"${invoice_data.subtotal:.2f}"])
        data.append(
            ["", "", "", "", "TAX (8.25%):", f"${invoice_data.total_sales_tax:.2f}"]
        )
        data.append(["", "", "", "", "TOTAL DUE:", f"${invoice_data.total:.2f}"])

        # Create table
        table = Table(data, colWidths=[80, 60, 160, 50, 70, 70])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
                ]
            )
        )

        elements.append(table)

    # Build the PDF
    doc.build(elements)
    return output_path


def create_statement_pdf(statement_data, output_path):
    """Create a PDF statement based on the statement data"""

    # Create a PDF document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )

    # Styles
    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    subtitle_style = styles["Heading2"]
    normal_style = styles["Normal"]

    # Create content elements
    elements = []

    # Header
    elements.append(Paragraph("REAGAN POWER COMPRESSION LLC", title_style))
    elements.append(Spacer(1, 12))
    elements.append(
        Paragraph(f"STATEMENT DATE: {statement_data.statement_date}", subtitle_style)
    )
    elements.append(Spacer(1, 12))

    # Customer info
    elements.append(Paragraph("TO:", subtitle_style))
    elements.append(Paragraph(statement_data.to.customer_name, normal_style))
    elements.append(Paragraph(statement_data.to.address, normal_style))
    elements.append(Spacer(1, 24))

    # Transactions
    data = [["DATE", "TRANSACTION", "AMOUNT", "BALANCE"]]

    for transaction in statement_data.transactions:
        data.append(
            [
                transaction["date"],
                transaction["transaction"],
                transaction["amount"],
                transaction["balance"],
            ]
        )

    # Create table
    table = Table(data, colWidths=[80, 240, 80, 80])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
            ]
        )
    )

    elements.append(table)

    # Build the PDF
    doc.build(elements)
    return output_path


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


# ===== Main Execution =====


def generate_synthetic_invoices(count=10, include_degradation=True):
    """Generate a specified number of synthetic invoices"""

    # Ensure directories exist
    os.makedirs("synthetic_invoices/pdf", exist_ok=True)
    os.makedirs("synthetic_invoices/json", exist_ok=True)

    # Track generated files
    generated_files = []

    # Generate invoices
    for i in range(count):
        # Randomly select template type
        template_type = random.choice(["aegis", "reagan", "atkinson"])

        # Generate invoice data and JSON
        json_content, invoice_data = generate_invoice_json(template_type)

        # Create unique filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{template_type}_{timestamp}_{i}"

        # Save JSON
        json_path = f"synthetic_invoices/json/{base_filename}.json"
        with open(json_path, "w") as f:
            f.write(json_content)

        # Create PDF
        pdf_path = f"synthetic_invoices/pdf/{base_filename}.pdf"
        create_invoice_pdf(invoice_data, pdf_path, template_type)

        # Apply degradation if requested, with different levels of degradation
        if include_degradation:
            degraded_pdf_path = f"synthetic_invoices/pdf/{base_filename}_degraded.pdf"
            try:
                # Create a more realistic, less extreme degradation
                degrade_pdf_image(pdf_path, degraded_pdf_path)
                generated_files.append((json_path, degraded_pdf_path))
                
                # Occasionally create a second, slightly more degraded version for comparison
                if random.random() < 0.2:  # 20% chance
                    more_degraded_path = f"synthetic_invoices/pdf/{base_filename}_more_degraded.pdf"
                    # This will use the default degradation which is already toned down
                    degrade_pdf_image(degraded_pdf_path, more_degraded_path)
                    generated_files.append((json_path, more_degraded_path))
            except Exception as e:
                print(f"Error applying degradation: {e}")
                generated_files.append((json_path, pdf_path))
        else:
            generated_files.append((json_path, pdf_path))

        print(f"Generated {template_type} invoice: {base_filename}")

    # Generate a few statements
    for i in range(max(1, count // 5)):  # 20% of count, at least 1
        # Generate statement data and JSON
        json_content, statement_data = generate_statement_json()

        # Create unique filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"statement_{timestamp}_{i}"

        # Save JSON
        json_path = f"synthetic_invoices/json/{base_filename}.json"
        with open(json_path, "w") as f:
            f.write(json_content)

        # Create PDF
        pdf_path = f"synthetic_invoices/pdf/{base_filename}.pdf"
        create_statement_pdf(statement_data, pdf_path)

        # Apply degradation if requested, with different levels of degradation
        if include_degradation:
            degraded_pdf_path = f"synthetic_invoices/pdf/{base_filename}_degraded.pdf"
            try:
                # Create a more realistic, less extreme degradation
                degrade_pdf_image(pdf_path, degraded_pdf_path)
                generated_files.append((json_path, degraded_pdf_path))
                
                # Occasionally create a second, slightly more degraded version for comparison
                if random.random() < 0.2:  # 20% chance
                    more_degraded_path = f"synthetic_invoices/pdf/{base_filename}_more_degraded.pdf"
                    # This will use the default degradation which is already toned down
                    degrade_pdf_image(degraded_pdf_path, more_degraded_path)
                    generated_files.append((json_path, more_degraded_path))
            except Exception as e:
                print(f"Error applying degradation: {e}")
                generated_files.append((json_path, pdf_path))
        else:
            generated_files.append((json_path, pdf_path))

        print(f"Generated statement: {base_filename}")

    return generated_files


def validate_invoices(generated_files):
    """Validate the generated invoices"""
    validation_results = []

    for json_path, pdf_path in generated_files:
        try:
            # Load the JSON data
            with open(json_path, "r") as f:
                json_data = json.load(f)

            # Perform validation
            if "invoice_number" in json_data:
                # This is an invoice
                if "line_items" in json_data:
                    # Calculate expected subtotal
                    expected_subtotal = sum(
                        float(item["quantity"]) * float(item["unit_price"])
                        for item in json_data["line_items"]
                    )

                    # Calculate expected tax
                    expected_tax = round(expected_subtotal * 0.0825, 2)

                    # Calculate expected total
                    expected_total = expected_subtotal + expected_tax

                    # Compare with actual values
                    actual_subtotal = float(json_data.get("subtotal", 0))
                    actual_tax = float(json_data.get("tax", 0))
                    actual_total = float(json_data.get("total", 0))

                    # Check if values match
                    subtotal_valid = abs(expected_subtotal - actual_subtotal) < 0.01
                    tax_valid = abs(expected_tax - actual_tax) < 0.01
                    total_valid = abs(expected_total - actual_total) < 0.01

                    validation_results.append(
                        {
                            "file": json_path,
                            "valid": subtotal_valid and tax_valid and total_valid,
                            "errors": []
                            if (subtotal_valid and tax_valid and total_valid)
                            else [
                                f"Subtotal mismatch: expected {expected_subtotal}, got {actual_subtotal}"
                                if not subtotal_valid
                                else None,
                                f"Tax mismatch: expected {expected_tax}, got {actual_tax}"
                                if not tax_valid
                                else None,
                                f"Total mismatch: expected {expected_total}, got {actual_total}"
                                if not total_valid
                                else None,
                            ],
                        }
                    )
                else:
                    validation_results.append(
                        {"file": json_path, "valid": True, "errors": []}
                    )
            else:
                # This is a statement
                validation_results.append(
                    {"file": json_path, "valid": True, "errors": []}
                )
        except Exception as e:
            validation_results.append(
                {"file": json_path, "valid": False, "errors": [str(e)]}
            )

    return validation_results


if __name__ == "__main__":
    import argparse
    from io import BytesIO

    parser = argparse.ArgumentParser(
        description="Generate synthetic invoices for oil & gas companies"
    )
    parser.add_argument(
        "--count", type=int, default=10, help="Number of invoices to generate"
    )
    parser.add_argument(
        "--no-degradation", action="store_true", help="Skip image degradation"
    )
    parser.add_argument(
        "--validate", action="store_true", help="Validate generated invoices"
    )

    args = parser.parse_args()

    print(f"Generating {args.count} synthetic invoices...")
    generated_files = generate_synthetic_invoices(args.count, not args.no_degradation)

    if args.validate:
        print("\nValidating generated invoices...")
        validation_results = validate_invoices(generated_files)

        valid_count = sum(1 for result in validation_results if result["valid"])
        print(
            f"\nValidation complete: {valid_count}/{len(validation_results)} files are valid"
        )

        # Print errors for invalid files
        for result in validation_results:
            if not result["valid"]:
                print(f"\nErrors in {result['file']}:")
                for error in result["errors"]:
                    if error:
                        print(f"  - {error}")

    print("\nGeneration complete!")
    print("JSON files saved to: synthetic_invoices/json/")
    print("PDF files saved to: synthetic_invoices/pdf/")
