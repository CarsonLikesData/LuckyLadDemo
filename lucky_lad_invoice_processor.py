"""
Lucky Lad Invoice Processor
----------------------------
An automated invoice processing system that:
1. Monitors Email for invoice PDFs
2. Uses Google Document AI for initial data extraction
3. Validates and standardizes data with Vertex AI
4. Stores processed data in Snowflake
"""


# TODO:
# 1. Add in a system to flag invoices as paid or unpaid. Update powerbi dashboard upon status change.
# 2. Automate job shceduling, client wants to run AM and PM. - Azure handles this, need to confirm scheduling
# 3. Make application deployable. - What are Azure's requirements for this?

# Email and PDF processing imports
import os
import email
import json
from email.utils import parsedate_to_datetime
from datetime import datetime
from imaplib import IMAP4_SSL
from dateutil import parser as dateutil_parser

# RAG Engine import
from rag_engine import get_rag_engine

# Outlook/Exchange imports
try:
    from exchangelib import Credentials, Account, Configuration, DELEGATE, FileAttachment
    from exchangelib.protocol import BaseProtocol, NoVerifyHTTPAdapter
    import requests
    OUTLOOK_AVAILABLE = True
except ImportError:
    print("Warning: exchangelib not installed. Outlook functionality will be disabled.")
    OUTLOOK_AVAILABLE = False

# Google Cloud and Vertex AI imports
from google.cloud import documentai
from google.api_core.client_options import ClientOptions
import vertexai
from vertexai.generative_models import GenerativeModel, SafetySetting

# Data processing imports
import pandas as pd
import snowflake.connector

# ===== Configuration =====

# GCP configuration
PROJECT_ID = "invoiceprocessing-450716"
LOCATION = "us"
PROCESSOR_ID = "5486fff89ef396e2"
PROCESSOR_VERSION_ID = "57f4f1dda43d5c50"
MIME_TYPE = "application/pdf"
FIELD_MASK = "text,entities,pages.pageNumber"

# Invoice storage configuration
INVOICE_BASE_DIR = "processed_invoices"
REVIEW_DIR = "invoices_for_review"  # Directory for invoices that need human review

# Email configuration

# COMMENT OUT OR REMOVE GMAIL CONFIGURATION BEFORE DEPLOYING - IMPORTANT

# Gmail configuration
GMAIL_USERNAME = "lucky.lad.test.df@gmail.com"
# In production, use environment variables or a secrets manager
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD", "your_app_password_here")

# Outlook configuration
USE_OUTLOOK = os.environ.get("USE_OUTLOOK", "False").lower() == "true"
OUTLOOK_EMAIL = os.environ.get("OUTLOOK_EMAIL", "")
OUTLOOK_PASSWORD = os.environ.get("OUTLOOK_PASSWORD", "")
OUTLOOK_SERVER = os.environ.get("OUTLOOK_SERVER", "outlook.office365.com")
# Set to True to disable SSL certificate verification (use only in development)
OUTLOOK_DISABLE_VERIFY_SSL = os.environ.get("OUTLOOK_DISABLE_VERIFY_SSL", "False").lower() == "true"

# Snowflake configuration
SNOWFLAKE_ACCOUNT = "ifb67743.us-east-1"
SNOWFLAKE_USER = os.environ.get("LLE_SNOWFLAKE_SVC_ACC")
SNOWFLAKE_PASSWORD = os.environ.get("LLE_SNOWFLAKE_SVC_ACC_PW")
SNOWFLAKE_DATABASE = "OCCLUSION"
SNOWFLAKE_SCHEMA = "WELLS"
SNOWFLAKE_WAREHOUSE = "COMPUTE_WH"
SNOWFLAKE_TABLE = "LUCKY_LAD_INVOICE_PROCESSOR"

# Vertex AI configuration
VERTEX_AI_PROJECT = "invoiceprocessing-450716"
VERTEX_AI_LOCATION = "us-central1"
VERTEX_AI_API_ENDPOINT = "aiplatform.googleapis.com"
VERTEX_AI_MODEL = "gemini-pro"  
# ===== System Instructions for Vertex AI =====

SYSTEM_INSTRUCTION = """
You are an AI data validation specialist comparing Document AI extractions with PDF invoices for an oil and gas company.

INSTRUCTIONS:
1. Compare each field extracted by Document AI against the original PDF
2. For each field, provide the EXACT value found in the PDF (not just "Match")
3. Pay SPECIAL ATTENTION to fields that identify well names, particularly:
   - Any field labeled "CHARGE" or "Charge" (often contains well name)
   - Fields containing "Well" or "well" in their name or value
   - Ship To or Bill To fields that might contain well identifiers
   - Description fields that mention well names or locations
4. Follow this consistent format in your response:

General Information Verification:
Invoice Number: [Value]
Invoice Date: [Value]
Due Date: [Value]
Vendor Name: [Value]
Bill To Name: [Value]
Ship To Name: [Value]
Well Name: [Value] (Extract from CHARGE field or other relevant fields)
Field Name: [Value] (If present)

Financial Details Verification:
Subtotal: [Value]
Sales Tax: [Value]
Total Amount Due: [Value]
Balance Due: [Value]

Line Item Verification:
Description 1: [Value]
Quantity 1: [Value]
Unit Price 1: [Value]
Total Amount 1: [Value]
CHARGE 1: [Value] (If present)

Description 2: [Value]
Quantity 2: [Value]
Unit Price 2: [Value]
Total Amount 2: [Value]
CHARGE 2: [Value] (If present)

[... continue for all line items ...]

Statement Specific Verification:
Statement Date: [Value]
Amount Due (from the summary/aging): [Value]

IMPORTANT:
1. Always use standardized field names as shown above
2. If you find a well name in ANY field, include it in the "Well Name" field
3. For propane invoices, check tank information for potential well identifiers
4. For oil/lubricant invoices, check the ship to location and charge fields
"""

MESSAGE_TEMPLATE = """
I need you to verify and extract information from the following oil and gas invoice data.
The original document text and extracted entities are provided below.

Document Content:
{document_text}

Extracted Entities:
{entities}

This is for an oil and gas company that needs to track expenses by well name.
IMPORTANT: Pay special attention to any fields that might contain well names, especially:
1. Fields labeled "CHARGE" or "Charge"
2. Ship To or location information
3. Description fields that mention wells
4. Any field containing words like "Well", "Field", or specific well identifiers

Please extract and verify all invoice information following the format in your instructions.
For any field that isn't found in the document, respond with "Not found".
"""

# Vertex AI generation config
GENERATION_CONFIG = {
    "max_output_tokens": 2048,
    "temperature": 0.2,
    "top_p": 0.95,
}

# Vertex AI safety settings for gemini-pro
SAFETY_SETTINGS = [
    SafetySetting(
        category="HARM_CATEGORY_HATE_SPEECH",
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_NONE,
    ),
    SafetySetting(
        category="HARM_CATEGORY_DANGEROUS_CONTENT",
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_NONE,
    ),
    SafetySetting(
        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_NONE,
    ),
    SafetySetting(
        category="HARM_CATEGORY_HARASSMENT",
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_NONE,
    ),
]
# ===== Email Functions =====

# ----- Gmail Functions -----

def get_gmail_service(username, password):
    """Connect to Gmail via IMAP and return the IMAP object"""
    try:
        mail = IMAP4_SSL("imap.gmail.com")
        mail.login(username, password)
        mail.select("inbox")
        return mail
    except IMAP4_SSL.error as e:
        print(f"IMAP Error: {e}")
        return None
    except Exception as e:
        print(f"Error getting Gmail service: {e}")
        return None


# ----- Outlook Functions -----

def disable_ssl_verification():
    """Disable SSL verification for Outlook connections (development only)"""
    if not OUTLOOK_AVAILABLE:
        return
        
    BaseProtocol.HTTP_ADAPTER_CLS = NoVerifyHTTPAdapter
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


def get_outlook_service(email_address, password, server):
    """Connect to Outlook/Exchange and return the Account object"""
    if not OUTLOOK_AVAILABLE:
        print("Error: exchangelib not installed. Cannot connect to Outlook.")
        return None
        
    try:
        # Disable SSL verification if configured (for development environments)
        if OUTLOOK_DISABLE_VERIFY_SSL:
            disable_ssl_verification()
            
        # Set up credentials and connect
        credentials = Credentials(username=email_address, password=password)
        config = Configuration(server=server, credentials=credentials)
        account = Account(
            primary_smtp_address=email_address,
            config=config,
            autodiscover=False,
            access_type=DELEGATE
        )
        return account
    except Exception as e:
        print(f"Error connecting to Outlook: {e}")
        return None


def process_outlook_email(attachment, email_datetime):
    """Process a single Outlook email attachment"""
    extracted_data = []
    
    try:
        if attachment.name.lower().endswith('.pdf'):
            # Get the PDF content
            payload = attachment.content
            pdf_title_text = "No Title Found"
            
            try:
                document = process_document_from_memory(
                    image_content=payload,
                    mime_type=MIME_TYPE,
                    project_id=PROJECT_ID,
                    location=LOCATION,
                    processor_id=PROCESSOR_ID,
                    field_mask=FIELD_MASK,
                    processor_version_id=PROCESSOR_VERSION_ID,
                )
                
                if document.text:
                    pdf_title_text = " ".join(document.text.split()[:10]) + "..."
                
                text = document.text
                entities = document.entities
                
                extracted_entities = {}
                for entity in entities:
                    extracted_entities[entity.type_] = entity.mention_text
                
                document_data = {
                    "text": text,
                    "entities": [
                        {"type_": e.type_, "mention_text": e.mention_text}
                        for e in entities
                    ],
                }
                
                extracted_data.append(
                    {
                        "filename": attachment.name,
                        "email_datetime": email_datetime,
                        "text": text,
                        "entities": extracted_entities,
                        "document_json": json.dumps(document_data),
                        "gmail_search_query": f'in:inbox "{pdf_title_text}"',  # For compatibility
                        "pdf_content": payload,  # Store the PDF content for later use
                    }
                )
                
                print(f"Extracted from {attachment.name}: {text[:100]}...")
            except Exception as e:
                print(f"Error processing {attachment.name}: {e}")
    except Exception as e:
        print(f"Error processing attachment: {e}")
        
    return extracted_data


def process_outlook_pdfs(email_address, password, server):
    """Main function to process PDFs from Outlook"""
    if not OUTLOOK_AVAILABLE:
        print("Error: exchangelib not installed. Cannot process Outlook emails.")
        return []
        
    outlook_account = get_outlook_service(email_address, password, server)
    if outlook_account is None:
        return []
    
    all_extracted_data = []
    
    try:
        # Get unread emails from inbox
        inbox = outlook_account.inbox
        unread_emails = list(inbox.filter(is_read=False).order_by('-datetime_received'))
        
        # Create a folder for this month's invoices if it doesn't exist
        now = datetime.now()
        folder_name = now.strftime("%B_%Y_Invoices")
        
        # Check if folder exists, create if it doesn't
        try:
            invoice_folder = outlook_account.root / folder_name
            # Test if folder exists by accessing it
            _ = invoice_folder.total_count
        except Exception:
            # Folder doesn't exist, create it
            invoice_folder = outlook_account.inbox.create_folder(folder_name)
            print(f"Created folder '{folder_name}'")
        
        # Process each email
        for email_item in unread_emails:
            try:
                # Process attachments
                for attachment in email_item.attachments:
                    if isinstance(attachment, FileAttachment):
                        extracted_data = process_outlook_email(
                            attachment,
                            email_item.datetime_received
                        )
                        all_extracted_data.extend(extracted_data)
                
                # Mark as read and move to invoice folder
                email_item.is_read = True
                email_item.save()
                email_item.move(invoice_folder)
                print(f"Processed email from {email_item.sender} received at {email_item.datetime_received}")
            except Exception as e:
                print(f"Error processing email: {e}")
    
    except Exception as e:
        print(f"An error occurred while processing Outlook emails: {e}")
    
    return all_extracted_data



# ===== Document AI Functions =====


def process_document_from_memory(
    image_content,
    mime_type,
    project_id,
    location,
    processor_id,
    field_mask=None,
    processor_version_id=None,
):
    """Process a document using Google Document AI with confidence tracking"""
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)

    if processor_version_id:
        name = client.processor_version_path(
            project_id, location, processor_id, processor_version_id
        )
    else:
        name = client.processor_path(project_id, location, processor_id)

    raw_document = documentai.RawDocument(content=image_content, mime_type=mime_type)
    process_options = documentai.ProcessOptions(
        individual_page_selector=documentai.ProcessOptions.IndividualPageSelector(
            pages=[1]
        )
    )

    request = documentai.ProcessRequest(
        name=name,
        raw_document=raw_document,
        field_mask=field_mask,
        process_options=process_options,
    )

    result = client.process_document(request=request)
    document = result.document
    
    # Track confidence scores for entities
    low_confidence_entities = []
    for entity in document.entities:
        if hasattr(entity, 'confidence') and entity.confidence < 0.7:  # Threshold for low confidence
            low_confidence_entities.append({
                'type': entity.type_,
                'mention_text': entity.mention_text,
                'confidence': entity.confidence
            })
    
    # Log low confidence entities for potential human review
    if low_confidence_entities:
        print(f"Found {len(low_confidence_entities)} low-confidence entities that may need review")
        # These will be handled during the Vertex AI processing stage
    
    return document


# ===== Vertex AI Functions =====


def generate_content_with_vertex_ai(document_json_string, filename="Unknown"):
    """
    Send document data to Vertex AI for validation and standardization
    with RAG enhancement
    """
    vertexai.init(
        project=VERTEX_AI_PROJECT,
        location=VERTEX_AI_LOCATION,
        api_endpoint=VERTEX_AI_API_ENDPOINT,
    )

    model = GenerativeModel(VERTEX_AI_MODEL, system_instruction=SYSTEM_INSTRUCTION)

    # Parse the document JSON to access text and entities
    try:
        doc_data = json.loads(document_json_string)
        document_text = doc_data.get("text", "")

        # Extract entities in a more readable format
        entities_list = doc_data.get("entities", [])
        entities_formatted = "\n".join(
            [f"{entity['type_']}: {entity['mention_text']}" for entity in entities_list]
        )
        
        # Convert entities list to dictionary for RAG
        entities_dict = {entity['type_']: entity['mention_text'] for entity in entities_list}
        
        # Get RAG engine and retrieve similar invoices
        rag = get_rag_engine()
        similar_invoices = rag.retrieve_similar_invoices(document_text, entities_dict)
        
        # Detect if this is a new invoice type
        is_new_invoice_type = len(similar_invoices) == 0 or all(
            similar_invoice.get('metadata', {}).get('similarity_score', 0) < 0.5
            for similar_invoice in similar_invoices
        )
        
        # Generate context from similar invoices
        rag_context = rag.generate_context_for_vertex_ai(similar_invoices)
        
        # Format the message with actual document content
        formatted_message = MESSAGE_TEMPLATE.format(
            document_text=document_text[:3000],  # Limit text length if needed
            entities=entities_formatted,
        )
        
        # Add RAG context if available
        if rag_context:
            formatted_message += f"\n\n{rag_context}"
            
        # If this is a new invoice type, add a note to the prompt
        if is_new_invoice_type:
            formatted_message += "\n\nNOTE: This appears to be a new invoice type not seen before. " \
                                "Please pay extra attention to field extraction and validation."
            
            # Flag for human review
            flag_for_human_review(
                {
                    "document_text": document_text,
                    "entities": entities_dict,
                    "document_json": document_json_string,
                    "filename": filename
                },
                "New invoice type detected"
            )

        # Send to model
        chat = model.start_chat()
        response = chat.send_message(
            formatted_message,
            generation_config=GENERATION_CONFIG,
            safety_settings=SAFETY_SETTINGS,
        )
        
        # After successful processing, add the invoice to RAG database if it's not already there
        if not is_new_invoice_type:
            metadata = {"filename": filename, "processing_time": datetime.now().isoformat()}
            rag.add_invoice(document_text, entities_dict, metadata)
        
        return response.text
    except json.JSONDecodeError as e:
        print(
            f"Error: Invalid JSON provided in generate_content_with_vertex_ai. Details: {str(e)}"
        )
        # Optionally log the first few characters of the problematic JSON for debugging
        if document_json_string:
            print(f"JSON snippet: {document_json_string[:100]}...")
        return None
    except Exception as e:
        print(f"Error calling Vertex AI: {e}")
        return None


def process_vertex_response(response_content):
    """
    Process the Vertex AI response by organizing data into sections

    Args:
        response_content (str): The text response from Vertex AI

    Returns:
        dict: Structured data extracted from the response, organized by sections
    """
    if not response_content:
        return {}

    # Initialize data dictionary with sections
    data = {
        "General Information": {},
        "Financial Details": {},
        "Line Items": [],
        "Statement Specific": {},
        "Other": {},  # For fields not belonging to a recognized section
    }

    current_section = "Other"  # Default section
    current_line_item = {}
    line_item_index = 0

    # Process each line
    for line in response_content.splitlines():
        line = line.strip()
        if not line:
            continue

        # Check if this line is a section header
        if line.endswith("Verification:") or line.endswith("Verification"):
            # Extract section name without the "Verification" suffix
            section_name = (
                line.replace("Verification:", "").replace("Verification", "").strip()
            )

            # Map to our predefined sections
            if "General Information" in section_name:
                current_section = "General Information"
            elif "Financial Details" in section_name:
                current_section = "Financial Details"
            elif "Line Item" in section_name:
                current_section = "Line Items"
            elif "Statement Specific" in section_name:
                current_section = "Statement Specific"
            else:
                current_section = "Other"

            # If we were building a line item, add it to the list
            if current_line_item and current_section != "Line Items":
                if all(
                    key in current_line_item
                    for key in ["Description", "Quantity", "Unit Price", "Total Amount"]
                ):
                    data["Line Items"].append(current_line_item)
                    current_line_item = {}

            continue

        # Parse field and value
        if ":" in line:
            try:
                field, value = line.split(":", 1)
                field = field.strip()
                value = value.strip()

                # Handle line items specially
                if current_section == "Line Items":
                    # Check if this is a new line item
                    if field.startswith("Description") and current_line_item:
                        # Save previous line item if it has required fields
                        if all(
                            key in current_line_item
                            for key in [
                                "Description",
                                "Quantity",
                                "Unit Price",
                                "Total Amount",
                            ]
                        ):
                            data["Line Items"].append(current_line_item)
                        current_line_item = {}
                        line_item_index += 1

                    # Extract the base field name without the index
                    base_field = field.rstrip("0123456789").strip()
                    current_line_item[base_field] = value
                else:
                    # Store in the appropriate section
                    data[current_section][field] = value
            except ValueError:
                # Handle lines that don't split properly
                print(f"Warning: Could not parse line: {line}")
                continue

    # Add the last line item if it exists
    if current_line_item and current_section == "Line Items":
        if all(
            key in current_line_item
            for key in ["Description", "Quantity", "Unit Price", "Total Amount"]
        ):
            data["Line Items"].append(current_line_item)

    # Flatten the structure if needed for backward compatibility
    flat_data = {}
    for section, section_data in data.items():
        if isinstance(section_data, dict):
            flat_data.update(section_data)

    # Add line items in a flat format
    for i, item in enumerate(data["Line Items"], 1):
        for key, value in item.items():
            flat_data[f"{key} {i}"] = value

    return flat_data


def sort_invoices_by_well_name(processed_data, pdf_filename, pdf_content=None):
    """
    Sort invoices into directories based on the Well Name found in the invoice.
    Organizes invoices in a hierarchical structure:
    /processed_invoices/[Well Name]/[YYYY-MM-Month]/[invoice_file.pdf]

    Args:
        processed_data (dict): The processed data from Vertex AI
        pdf_filename (str): The original PDF filename
        pdf_content (bytes, optional): The PDF file content if available

    Returns:
        str: The path where the invoice was saved
    """
    # Create base directory if it doesn't exist
    if not os.path.exists(INVOICE_BASE_DIR):
        os.makedirs(INVOICE_BASE_DIR)

    # Look for well name in various possible fields
    well_name = None

    # First priority: Check if Vertex AI already extracted a Well Name field
    if "Well Name" in processed_data:
        well_name = processed_data["Well Name"]
        print(f"Found well name in 'Well Name' field: {well_name}")

    # Second priority: Check for CHARGE field (common in oil & gas invoices)
    if not well_name:
        for key, value in processed_data.items():
            if isinstance(value, str) and "CHARGE" in key.upper():
                well_name = value
                print(f"Found well name in '{key}' field: {well_name}")
                break

    # Third priority: Check in line items for CHARGE field
    if not well_name:
        for i in range(1, 20):  # Assuming we won't have more than 20 line items
            charge_key = f"CHARGE {i}"
            if charge_key in processed_data:
                well_name = processed_data[charge_key]
                print(f"Found well name in '{charge_key}' field: {well_name}")
                break

            # Also check in description fields for CHARGE keyword
            description_key = f"Description {i}"
            if description_key in processed_data:
                description = processed_data[description_key]
                if isinstance(description, str) and "CHARGE" in description.upper():
                    # Extract well name from the description
                    parts = description.split(":")
                    if len(parts) > 1:
                        well_name = parts[1].strip()
                        print(f"Extracted well name from description: {well_name}")
                        break

    # Fourth priority: Check Ship To and Bill To fields for well identifiers
    if not well_name:
        location_fields = [
            "Ship To",
            "ShipTo",
            "Bill To",
            "BillTo",
            "Sold To",
            "SoldTo",
        ]
        for field in location_fields:
            if field in processed_data and processed_data[field]:
                location_text = processed_data[field]

                # Look for common well name patterns
                if isinstance(location_text, str):
                    # Pattern: Name followed by Tank Battery or TB
                    if (
                        "TANK BATTERY" in location_text.upper()
                        or " TB " in location_text.upper()
                    ):
                        parts = location_text.split(
                            "Tank Battery" if "Tank Battery" in location_text else "TB"
                        )
                        if parts[0].strip():
                            well_name = parts[0].strip()
                            print(
                                f"Extracted well name from location field: {well_name}"
                            )
                            break

                    # Pattern: Contains well number format (e.g., #1, #2H, etc.)
                    elif "#" in location_text and any(
                        char.isdigit() for char in location_text
                    ):
                        import re

                        well_pattern = re.search(
                            r"([A-Za-z\s]+#\d+[A-Za-z]*)", location_text
                        )
                        if well_pattern:
                            well_name = well_pattern.group(1)
                            print(
                                f"Extracted well name pattern from location: {well_name}"
                            )
                            break

    # Fifth priority: Check Field Name
    if not well_name and "Field Name" in processed_data:
        field_name = processed_data["Field Name"]
        if field_name and field_name.lower() != "not found":
            well_name = field_name
            print(f"Using Field Name as well identifier: {well_name}")

    # Last resort: Check all fields for well-related keywords
    if not well_name:
        well_keywords = [
            "WELL",
            "LEASE",
            "FIELD",
            "GODCHAUX",
            "MCINIS",
            "KIRBY",
            "TEMPLE",
        ]
        for key, value in processed_data.items():
            if isinstance(value, str):
                for keyword in well_keywords:
                    if keyword in value.upper() or keyword in key.upper():
                        well_name = value
                        print(
                            f"Found potential well name in '{key}' field with keyword '{keyword}': {well_name}"
                        )
                        break
                if well_name:
                    break

    # If we still don't have a well name, use invoice-specific logic based on filename
    if not well_name:
        # Check if filename contains potential well identifiers
        if "ATKINSON" in pdf_filename.upper():
            # For Atkinson Propane invoices, check for tank serial numbers or addresses
            if "Tank Serial Number" in processed_data:
                tank_id = processed_data["Tank Serial Number"]
                well_name = f"Tank-{tank_id}"
                print(f"Using tank serial number as well identifier: {well_name}")
            elif (
                "Sold To" in processed_data and "Address:" in processed_data["Sold To"]
            ):
                # Extract location from address
                address = processed_data["Sold To"]
                if "Temple" in address:
                    well_name = "Temple"
                    print(
                        f"Using location from address as well identifier: {well_name}"
                    )

        # For Reagan Power Compression invoices
        elif "REAGAN" in pdf_filename.upper():
            well_name = "Reagan Compression"
            print(
                f"Using vendor name as identifier for compression service: {well_name}"
            )

    # If we still don't have a well name, use "Unclassified"
    if not well_name or well_name.strip() == "":
        well_name = "Unclassified"
        print("No well name found, using 'Unclassified'")

    # Clean up well name to be directory-friendly
    well_name = well_name.replace("/", "_").replace("\\", "_").strip()
    well_name = well_name.replace(":", "_").replace("*", "_").replace("?", "_")
    well_name = well_name.replace("<", "_").replace(">", "_").replace("|", "_")
    well_name = well_name.replace('"', "_").replace("'", "_")

    # Create directory for this well if it doesn't exist
    well_dir = os.path.join(INVOICE_BASE_DIR, well_name)
    if not os.path.exists(well_dir):
        os.makedirs(well_dir)
        print(f"Created directory for well: {well_dir}")

    # Create a date-based subdirectory if we have invoice date
    invoice_date = None
    date_fields = ["Invoice Date", "Date", "InvoiceDate"]
    for field in date_fields:
        if field in processed_data and processed_data[field]:
            invoice_date = processed_data[field]
            break

    if invoice_date:
        try:
            # Try to parse and standardize the date format
            parsed_date = dateutil_parser.parse(invoice_date)
            # Create a more descriptive month directory format: YYYY-MM-MonthName
            month_name = parsed_date.strftime("%B")  # Full month name
            date_dir = parsed_date.strftime(f"%Y-%m-{month_name}")

            # Create the month directory within the well directory
            month_dir = os.path.join(well_dir, date_dir)
            if not os.path.exists(month_dir):
                os.makedirs(month_dir)
                print(f"Created month subdirectory: {month_dir}")

            # Update well_dir to point to the month directory for file saving
            well_dir = month_dir
        except (ValueError, TypeError, OverflowError) as e:
            # If date parsing fails, just use the original well directory
            print(f"Could not parse invoice date: {invoice_date}. Error: {str(e)}")

    # Determine the destination path
    dest_path = os.path.join(well_dir, pdf_filename)

    # If we have the PDF content, save it to the destination
    if pdf_content:
        with open(dest_path, "wb") as f:
            f.write(pdf_content)
        print(f"Saved invoice to {dest_path}")
    else:
        print(f"Would save invoice to {dest_path} (PDF content not available)")

    # Add the path and well name to the processed data for reference
    processed_data["Invoice_Path"] = dest_path
    processed_data["Well_Name"] = well_name  # Store the detected well name

    return dest_path


# ===== Email Processing Functions =====


def process_email(gmail_service, msg, num, label_name):
    """Process a single email with potential PDFs"""
    date_str = msg["Date"]
    email_datetime = parsedate_to_datetime(date_str) if date_str else datetime.now()
    extracted_data = []

    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        if part.get("Content-Disposition") is None:
            continue

        filename = part.get_filename()
        if filename and filename.lower().endswith(".pdf"):
            payload = part.get_payload(decode=True)
            pdf_title_text = "No Title Found"

            try:
                document = process_document_from_memory(
                    image_content=payload,
                    mime_type=MIME_TYPE,
                    project_id=PROJECT_ID,
                    location=LOCATION,
                    processor_id=PROCESSOR_ID,
                    field_mask=FIELD_MASK,
                    processor_version_id=PROCESSOR_VERSION_ID,
                )

                if document.text:
                    pdf_title_text = " ".join(document.text.split()[:10]) + "..."

                text = document.text
                entities = document.entities

                extracted_entities = {}
                for entity in entities:
                    extracted_entities[entity.type_] = entity.mention_text

                document_data = {
                    "text": text,
                    "entities": [
                        {"type_": e.type_, "mention_text": e.mention_text}
                        for e in entities
                    ],
                }

                extracted_data.append(
                    {
                        "filename": filename,
                        "email_datetime": email_datetime,
                        "text": text,
                        "entities": extracted_entities,
                        "document_json": json.dumps(document_data),
                        "gmail_search_query": f'in:inbox "{pdf_title_text}"',
                        "pdf_content": payload,  # Store the PDF content for later use
                    }
                )

                print(f"Extracted from {filename}: {text[:100]}...")
            except Exception as e:
                print(f"Error processing {filename}: {e}")

    # Label the email
    try:
        status, data = gmail_service.store(num, "+X-GM-LABELS", label_name)
        if status == "OK":
            print(f"Applied label '{label_name}' to email {num}")
        else:
            print(f"Failed to apply label '{label_name}' to email {num}")
    except Exception as e:
        print(f"Error applying label: {e}")

    print(f"Processed email from {email_datetime}")
    return extracted_data


def process_gmail_pdfs(username, password):
    """Main function to process PDFs from Gmail"""
    gmail_service = get_gmail_service(username, password)
    if gmail_service is None:
        return []

    all_extracted_data = []

    try:
        # Search for unread emails
        _, data = gmail_service.search(None, "UNSEEN", "ALL")
        mail_ids = data[0]
        id_list = mail_ids.split()

        # Create a label for this month's invoices
        now = datetime.now()
        label_name = now.strftime("%B_%Y_Invoices")

        status, data = gmail_service.list()
        if status == "OK":
            label_exists = False
            for item in data:
                if label_name in str(item):
                    label_exists = True
                    break

            # Create label if it doesn't exist
            if not label_exists:
                status, data = gmail_service.create('"' + label_name + '"')
                if status == "OK":
                    print(f"Created label '{label_name}'")
                else:
                    print(f"Failed to create label '{label_name}'")
        else:
            print("Failed to list labels.")

        # Process each email
        for num in id_list:
            _, data = gmail_service.fetch(num, "(RFC822)")
            for response_part in data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    extracted_data = process_email(gmail_service, msg, num, label_name)
                    all_extracted_data.extend(extracted_data)

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        try:
            gmail_service.close()
            gmail_service.logout()
        except Exception:
            pass

    return all_extracted_data


# ===== Snowflake Functions =====


def add_missing_columns(df: pd.DataFrame):
    """Add any missing columns to the Snowflake table"""
    ctx = None
    cs = None

    try:
        ctx = snowflake.connector.connect(
            account=SNOWFLAKE_ACCOUNT,
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA,
            warehouse=SNOWFLAKE_WAREHOUSE,
        )

        cs = ctx.cursor()

        # Get DataFrame columns
        df_columns = set(df.columns)

        # Get existing table columns
        table_columns_sql = f"""
        SELECT column_name
        FROM {SNOWFLAKE_DATABASE}.INFORMATION_SCHEMA.COLUMNS
        WHERE table_catalog = '{SNOWFLAKE_DATABASE}'
          AND table_schema = '{SNOWFLAKE_SCHEMA}'
          AND table_name = '{SNOWFLAKE_TABLE}'
        """

        cs.execute(table_columns_sql)
        existing_columns = {row[0].upper() for row in cs.fetchall()}

        # Find new columns to add
        new_columns_to_add = df_columns - existing_columns

        # Add each new column
        for col in new_columns_to_add:
            alter_table_sql = f"""
            ALTER TABLE {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_TABLE}
            ADD COLUMN {col} VARCHAR;
            """

            try:
                cs.execute(alter_table_sql)
                print(f"Added column '{col}' to table '{SNOWFLAKE_TABLE}'.")
            except snowflake.connector.errors.ProgrammingError as e:
                print(f"Error adding column '{col}': {e}")
            except snowflake.connector.errors.DatabaseError as e:
                print(f"Database Error adding column '{col}': {e}")
            except Exception as e:
                print(f"General error adding column '{col}': {e}")

        ctx.commit()

    except snowflake.connector.errors.Error as e:
        print(f"Snowflake Error in add_missing_columns: {e}")

    finally:
        if cs:
            cs.close()
        if ctx:
            ctx.close()


def check_for_duplicate_invoice(cs, vendor_name, invoice_number):
    """
    Check if an invoice with the same Vendor Name and Invoice Number already exists in Snowflake
    
    Args:
        cs: Snowflake cursor
        vendor_name: Name of the vendor
        invoice_number: Invoice number to check
        
    Returns:
        bool: True if duplicate exists, False otherwise
    """
    if not vendor_name or not invoice_number:
        # If either value is missing, we can't check for duplicates properly
        return False
        
    try:
        # Query to check for duplicates
        query = f"""
        SELECT COUNT(*)
        FROM {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_TABLE}
        WHERE UPPER(VENDORNAME) = UPPER(%s)
        AND UPPER(INVOICENUMBER) = UPPER(%s)
        """
        
        # Execute query with parameters
        cs.execute(query, (vendor_name, invoice_number))
        
        # Get result
        count = cs.fetchone()[0]
        
        # Return True if duplicate exists
        return count > 0
    except Exception as e:
        print(f"Error checking for duplicate invoice: {e}")
        # In case of error, return False to allow insertion (better to have duplicates than missing data)
        return False


def add_dataframe_to_snowflake(df: pd.DataFrame):
    """Add DataFrame data to Snowflake table"""
    if df.empty:
        print("DataFrame is empty. Nothing to add to Snowflake.")
        return

    ctx = None
    cs = None
    
    # Track statistics
    total_rows = len(df)
    inserted_rows = 0
    duplicate_rows = 0

    try:
        ctx = snowflake.connector.connect(
            account=SNOWFLAKE_ACCOUNT,
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA,
            warehouse=SNOWFLAKE_WAREHOUSE,
        )

        cs = ctx.cursor()

        # Ensure all necessary columns exist
        add_missing_columns(df)

        # Prepare SQL for inserting data
        columns = ", ".join(df.columns)
        placeholders = ", ".join(["%s"] * len(df.columns))
        sql = f"INSERT INTO {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_TABLE} ({columns}) VALUES ({placeholders})"

        # Insert each row
        for row in df.itertuples(index=False):
            try:
                # Convert row to dictionary for easier access
                row_dict = df.iloc[row.Index].to_dict()
                
                # Check for duplicate invoice
                vendor_name = row_dict.get('VendorName')
                invoice_number = row_dict.get('InvoiceNumber')
                
                if check_for_duplicate_invoice(cs, vendor_name, invoice_number):
                    print(f"Skipping duplicate invoice: Vendor={vendor_name}, Invoice Number={invoice_number}")
                    duplicate_rows += 1
                    continue
                
                # Insert if not a duplicate
                cs.execute(sql, row)
                inserted_rows += 1
            except snowflake.connector.errors.ProgrammingError as e:
                print(f"Error inserting row: {row}")
                print(f"Snowflake Programming Error: {e}")
            except Exception as e:
                print(f"General error inserting row: {row}")
                print(f"Python Error: {e}")

        ctx.commit()
        print(
            f"Successfully processed {total_rows} rows: {inserted_rows} inserted, {duplicate_rows} duplicates skipped"
        )

    except snowflake.connector.errors.Error as e:
        print(f"Snowflake Error in add_dataframe_to_snowflake: {e}")

    finally:
        if ctx:
            cs.close()
            ctx.close()


# ===== Debugging Functions =====


def debug_vertex_input(document_json_string):
    """Debug what's being sent to Vertex AI"""
    try:
        doc_data = json.loads(document_json_string)
        print("\n=== Document JSON Structure ===")
        print(f"Text length: {len(doc_data.get('text', ''))}")
        print(f"Number of entities: {len(doc_data.get('entities', []))}")

        print("\n=== First Few Entities ===")
        for i, entity in enumerate(doc_data.get("entities", [])[:5]):
            print(f"Entity {i + 1}: {entity['type_']} = {entity['mention_text']}")

        print("\n=== First 200 chars of text ===")
        print(doc_data.get("text", "")[:200])

        return True
    except json.JSONDecodeError:
        print("ERROR: Invalid JSON structure")
        print("First 100 chars of string:")
        print(document_json_string[:100])
        return False
    except Exception as e:
        print(f"Error inspecting document JSON: {e}")
        return False


def debug_vertex_output(response_content):
    """Debug what's coming back from Vertex AI"""
    print("\n=== Vertex AI Response Analysis ===")
    print(f"Response length: {len(response_content)}")

    sections = {}
    current_section = "Unsectioned"

    for line in response_content.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.endswith("Verification:") or line.endswith("Verification"):
            current_section = line
            sections[current_section] = []
        else:
            sections.setdefault(current_section, []).append(line)

    print("\n=== Response Sections ===")
    for section, lines in sections.items():
        print(f"\n{section} ({len(lines)} lines)")
        for line in lines[:3]:  # Show first 3 lines of each section
            print(f"  {line}")
        if len(lines) > 3:
            print(f"  ... and {len(lines) - 3} more lines")

    return sections


# ===== Main Process =====


def process_all_responses(vertex_ai_responses, extracted_data):
    """Process all Vertex AI responses into a DataFrame"""
    all_processed_data = []

    for i, (response_name, response_content) in enumerate(vertex_ai_responses.items()):
        # Process the response
        processed_data = process_vertex_response(response_content)

        # Add document metadata if available
        if extracted_data and i < len(extracted_data):
            processed_data["PDF Filename"] = extracted_data[i].get("filename")

            # Sort invoice by well name and save to appropriate directory
            if "filename" in extracted_data[i] and "pdf_content" in extracted_data[i]:
                sort_invoices_by_well_name(
                    processed_data,
                    extracted_data[i]["filename"],
                    extracted_data[i]["pdf_content"],
                )

        all_processed_data.append(processed_data)

    # Create DataFrame from all processed data
    if all_processed_data:
        final_df = pd.DataFrame(all_processed_data)

        # Clean column names (remove spaces)
        final_df.columns = [col.replace(" ", "") for col in final_df.columns]

        return final_df
    else:
        return pd.DataFrame()


def flag_for_human_review(invoice_data, reason):
    """Flag an invoice for human review and store it for later processing"""
    if not os.path.exists(REVIEW_DIR):
        os.makedirs(REVIEW_DIR)
    
    # Create a unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{REVIEW_DIR}/review_{timestamp}.json"
    
    # Store the invoice data and reason for review
    review_data = {
        "invoice_data": invoice_data,
        "reason": reason,
        "timestamp": timestamp,
        "status": "pending_review"
    }
    
    with open(filename, 'w') as f:
        json.dump(review_data, f, indent=2)
    
    print(f"Flagged invoice for human review: {filename}")
    return filename


def add_to_document_ai_dataset(project_id, location, processor_id, dataset_id,
                              document_content, ground_truth_entities):
    """Add a corrected document to a Document AI dataset for retraining"""
    try:
        from google.cloud import documentai_v1 as documentai_dataset
        
        # Initialize Document AI client
        client = documentai_dataset.DocumentProcessorServiceClient()
        
        # Format the dataset path
        dataset_path = client.dataset_path(project_id, location, processor_id, dataset_id)
        
        # Create the document with ground truth annotations
        # This is a simplified example - actual implementation would be more complex
        document = {
            "raw_document": {
                "content": document_content,
                "mime_type": "application/pdf"
            },
            "ground_truth": {
                "entities": ground_truth_entities
            }
        }
        
        # Add document to dataset
        response = client.add_dataset_schema_document(
            request={"dataset": dataset_path, "document": document}
        )
        
        print(f"Added document to dataset: {response}")
        return response
    except Exception as e:
        print(f"Error adding document to Document AI dataset: {e}")
        return None


def main(debug_mode=False):
    """Main function to run the invoice processor"""
    print("=== Lucky Lad Invoice Processor ===")
    print(f"Starting at {datetime.now()}")

    # Initialize variables
    extracted_data = []
    vertex_ai_responses = {}
    
    # Process emails based on configuration
    if USE_OUTLOOK and OUTLOOK_AVAILABLE and OUTLOOK_EMAIL and OUTLOOK_PASSWORD:
        print("\nChecking for new invoices in Outlook...")
        outlook_data = process_outlook_pdfs(OUTLOOK_EMAIL, OUTLOOK_PASSWORD, OUTLOOK_SERVER)
        extracted_data.extend(outlook_data)
        print(f"Found {len(outlook_data)} new invoices in Outlook")
    else:
        print("\nOutlook processing skipped (not configured or library not available)")
        
    # Always process Gmail for testing purposes unless explicitly disabled
    if GMAIL_USERNAME and GMAIL_PASSWORD:
        print("\nChecking for new invoices in Gmail...")
        gmail_data = process_gmail_pdfs(GMAIL_USERNAME, GMAIL_PASSWORD)
        extracted_data.extend(gmail_data)
        print(f"Found {len(gmail_data)} new invoices in Gmail")
    else:
        print("\nGmail processing skipped (not configured)")

    # Call Vertex AI for each document
    if extracted_data:
        print(f"\nProcessing {len(extracted_data)} documents with Vertex AI...")

        for i, data in enumerate(extracted_data):
            filename = data.get('filename', 'Unknown')
            print(f"\nProcessing document {i + 1}: {filename}")
            document_json_string = data["document_json"]

            # Debug info if requested
            if debug_mode:
                print("\n--- DEBUG MODE: Vertex AI Input ---")
                debug_vertex_input(document_json_string)

            # Call Vertex AI with RAG enhancement
            vertex_ai_response = generate_content_with_vertex_ai(document_json_string, filename)

            if vertex_ai_response:
                response_variable_name = f"vertex_ai_response_{i + 1}"
                vertex_ai_responses[response_variable_name] = vertex_ai_response

                # Debug info if requested
                if debug_mode:
                    print("\n--- DEBUG MODE: Vertex AI Output ---")
                    debug_vertex_output(vertex_ai_response)

                print(f"Successfully processed document {i + 1}")
            else:
                print(f"Vertex AI call failed for document {i + 1}")
    else:
        print("No new invoices found to process.")

    # Process responses
    if vertex_ai_responses:
        print("\nCreating structured data from Vertex AI responses...")

        # Process responses into a DataFrame
        final_df = process_all_responses(vertex_ai_responses, extracted_data)

        if not final_df.empty:
            # Convert all columns to string to avoid Snowflake type issues
            final_df = final_df.astype(str)

            # Display the DataFrame
            print("\n--- Final DataFrame ---")
            print(f"DataFrame shape: {final_df.shape}")
            print(final_df.head())

            # Add to Snowflake
            try:
                print("\nUploading data to Snowflake...")
                add_dataframe_to_snowflake(final_df)
                print("Successfully added data to Snowflake.")
            except Exception as e:
                print(f"Error adding data to Snowflake: {e}")
                
            # Update RAG database with processed invoices
            print("\nUpdating RAG database with processed invoices...")
            rag = get_rag_engine()
            for i, data in enumerate(extracted_data):
                if i < len(vertex_ai_responses):
                    document_text = data.get("text", "")
                    entities_dict = data.get("entities", {})
                    metadata = {
                        "filename": data.get("filename", "unknown"),
                        "email_datetime": data.get("email_datetime", datetime.now()).isoformat(),
                        "processed_data": final_df.iloc[i].to_dict() if i < len(final_df) else {}
                    }
                    success = rag.add_invoice(document_text, entities_dict, metadata)
                    if success:
                        print(f"Added invoice {data.get('filename', 'unknown')} to RAG database")
                    else:
                        print(f"Failed to add invoice {data.get('filename', 'unknown')} to RAG database")
        else:
            print("No data could be extracted from Vertex AI responses.")
    else:
        print("No Vertex AI responses to process.")

    print(f"\nScript finished at {datetime.now()}.")
    return True


if __name__ == "__main__":
    # Set environment variable for GCP authentication
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "path/to/your/application_default_credentials.json",
    )

    # Run the main process
    # Set debug_mode=True for detailed logging
    main(debug_mode=False)
