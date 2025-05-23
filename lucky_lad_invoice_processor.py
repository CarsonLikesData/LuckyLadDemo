"""
Lucky Lad Invoice Processor
----------------------------
An automated invoice processing system that:
1. Monitors Email for invoice PDFs
2. Uses Google Document AI for initial data extraction
3. Validates and standardizes data with Vertex AI
4. Stores processed data in Snowflake
"""

# Standard library imports
import os
import email
import json
from email.utils import parsedate_to_datetime
from datetime import datetime
from imaplib import IMAP4_SSL

# Third-party imports
from dateutil import parser as dateutil_parser
import pandas as pd
import snowflake.connector

# RAG Engine import
from rag_engine import get_rag_engine

# Outlook/Exchange imports
try:
    from exchangelib import (
        Credentials,
        Account,
        Configuration,
        DELEGATE,
        FileAttachment,
    )
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

# Statement handling configuration
STATEMENT_PROCESSOR_ID = "7892fff45ef396e3"  # Separate processor for statements
STATEMENT_PROCESSOR_VERSION_ID = "57f4f1dda43d5c51"
STATEMENT_STORAGE_DIR = "processed_statements"  # Directory for processed statements


# Function to detect if a document is a statement rather than an invoice
def is_statement(document_text, filename):
    """
    Determine if a document is a statement rather than an invoice

    Args:
        document_text (str): The extracted text from the document
        filename (str): The filename of the document

    Returns:
        bool: True if the document is a statement, False otherwise
    """
    # Check filename for statement indicators
    if "statement" in filename.lower():
        return True

    # Check document text for statement indicators
    statement_indicators = [
        "statement of account",
        "account statement",
        "statement date",
        "aging summary",
        "payment history",
        "balance forward",
        "previous balance",
        "current activity",
        "account summary",
    ]

    # Count how many statement indicators are present
    indicator_count = sum(
        1 for indicator in statement_indicators if indicator in document_text.lower()
    )

    # If multiple indicators are present, it's likely a statement
    if indicator_count >= 2:
        return True

    return False


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


# Gmail configuration
GMAIL_USERNAME = "dft.luckylad.test@gmail.com"

GMAIL_PASSWORD = "iwfy wjrz atpu edyt"

# GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD", "iwfywjrzatpuedyt")

# Outlook configuration
USE_OUTLOOK = os.environ.get("USE_OUTLOOK", "False").lower() == "true"
OUTLOOK_EMAIL = os.environ.get("OUTLOOK_EMAIL", "")
OUTLOOK_PASSWORD = os.environ.get("OUTLOOK_PASSWORD", "")
OUTLOOK_SERVER = os.environ.get("OUTLOOK_SERVER", "outlook.office365.com")
# Set to True to disable SSL certificate verification (use only in development)
OUTLOOK_DISABLE_VERIFY_SSL = (
    os.environ.get("OUTLOOK_DISABLE_VERIFY_SSL", "False").lower() == "true"
)

# Snowflake configuration
SNOWFLAKE_ACCOUNT = "ifb67743.us-east-1"
SNOWFLAKE_USER = os.environ.get("LLE_SNOWFLAKE_SVC_ACC")
SNOWFLAKE_PASSWORD = os.environ.get("LLE_SNOWFLAKE_SVC_ACC_PW")
SNOWFLAKE_DATABASE = "OCCLUSION"
SNOWFLAKE_SCHEMA = "WELLS"
SNOWFLAKE_WAREHOUSE = "COMPUTE_WH"
# Snowflake table configuration
SNOWFLAKE_INVOICE_HEADER_TABLE = "LLE_INVOICE_HEADER"
SNOWFLAKE_INVOICE_LINE_ITEMS_TABLE = "LLE_INVOICE_LINE_ITEMS"
SNOWFLAKE_STATEMENTS_TABLE = "LLE_STATEMENTS"
SNOWFLAKE_STATEMENT_TRANSACTIONS_TABLE = "LLE_STATEMENT_TRANSACTIONS"

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
Statement Period: [Value]
Previous Balance: [Value]
Current Charges: [Value]
Payments Received: [Value]
Amount Due (from the summary/aging): [Value]
Payment Due Date: [Value]
Account Number: [Value]

# For cross-validation with invoices
Related Invoices: [List invoice numbers referenced in statement]
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

DOCUMENT TYPE: {document_type}

IMPORTANT: Pay special attention to any fields that might contain well names, especially:
1. Fields labeled "CHARGE" or "Charge"
2. Ship To or location information
3. Description fields that mention wells
4. Any field containing words like "Well", "Field", or specific well identifiers

{statement_specific_instructions}
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

# ----- Gmail Functions ----- #TODO GMAIL CODE BLOCK NEEDS TO BE REMOVED OR COMMENTED OUT BEFORE DEPLOYMENT


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
    requests.packages.urllib3.disable_warnings(
        requests.packages.urllib3.exceptions.InsecureRequestWarning
    )


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
            access_type=DELEGATE,
        )
        return account
    except Exception as e:
        print(f"Error connecting to Outlook: {e}")
        return None


def process_outlook_email(attachment, email_datetime):
    """Process a single Outlook email attachment"""
    extracted_data = []

    try:
        if attachment.name.lower().endswith(".pdf"):
            # Get the PDF content
            payload = attachment.content
            pdf_title_text = "No Title Found"

            try:
                # First get some text to determine if this is a statement
                initial_document = process_document_from_memory(
                    image_content=payload,
                    mime_type=MIME_TYPE,
                    project_id=PROJECT_ID,
                    location=LOCATION,
                    processor_id=PROCESSOR_ID,
                    field_mask="text",  # Just get text for initial detection
                    processor_version_id=PROCESSOR_VERSION_ID,
                )

                # Check if this is a statement
                is_statement_doc = is_statement(initial_document.text, attachment.name)

                # Now process with the appropriate processor
                document = process_document_from_memory(
                    image_content=payload,
                    mime_type=MIME_TYPE,
                    project_id=PROJECT_ID,
                    location=LOCATION,
                    processor_id=PROCESSOR_ID,
                    field_mask=FIELD_MASK,
                    processor_version_id=PROCESSOR_VERSION_ID,
                    is_statement_doc=is_statement_doc,
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
        unread_emails = list(inbox.filter(is_read=False).order_by("-datetime_received"))

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
                            attachment, email_item.datetime_received
                        )
                        all_extracted_data.extend(extracted_data)

                # Mark as read and move to invoice folder
                email_item.is_read = True
                email_item.save()
                email_item.move(invoice_folder)
                print(
                    f"Processed email from {email_item.sender} received at {email_item.datetime_received}"
                )
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
    is_statement_doc=False,
):
    """Process a document using Google Document AI with confidence tracking"""
    # If this is a statement, use the statement processor instead
    if is_statement_doc:
        processor_id = STATEMENT_PROCESSOR_ID
        processor_version_id = STATEMENT_PROCESSOR_VERSION_ID
        print(f"Using statement processor: {processor_id}")
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
        if (
            hasattr(entity, "confidence") and entity.confidence < 0.7
        ):  # Threshold for low confidence
            low_confidence_entities.append(
                {
                    "type": entity.type_,
                    "mention_text": entity.mention_text,
                    "confidence": entity.confidence,
                }
            )

    # Log low confidence entities for potential human review
    if low_confidence_entities:
        print(
            f"Found {len(low_confidence_entities)} low-confidence entities that may need review"
        )
        # These will be handled during the Vertex AI processing stage

    return document


# ===== Vertex AI Functions =====


def generate_content_with_vertex_ai(
    document_json_string, filename="Unknown", is_statement_doc=False
):
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

        # Determine if this is a statement if not already specified
        if not is_statement_doc:
            is_statement_doc = is_statement(document_text, filename)

        document_type = "STATEMENT" if is_statement_doc else "INVOICE"
        print(f"Document type detected: {document_type}")

        # Extract entities in a more readable format
        entities_list = doc_data.get("entities", [])
        entities_formatted = "\n".join(
            [f"{entity['type_']}: {entity['mention_text']}" for entity in entities_list]
        )

        # Convert entities list to dictionary for RAG
        entities_dict = {
            entity["type_"]: entity["mention_text"] for entity in entities_list
        }

        # Get RAG engine and retrieve similar invoices
        rag = get_rag_engine()
        similar_invoices = rag.retrieve_similar_invoices(document_text, entities_dict)

        # Detect if this is a new invoice type
        is_new_invoice_type = len(similar_invoices) == 0 or all(
            similar_invoice.get("metadata", {}).get("similarity_score", 0) < 0.5
            for similar_invoice in similar_invoices
        )

        # Generate context from similar invoices
        rag_context = rag.generate_context_for_vertex_ai(similar_invoices)

        # Add statement-specific instructions if needed
        statement_specific_instructions = ""
        if is_statement_doc:
            statement_specific_instructions = """
            For STATEMENTS:
            1. Extract all invoice numbers mentioned in the statement
            2. Pay special attention to aging summaries and payment history
            3. Note any discrepancies between statement totals and individual invoice amounts
            4. Extract account number and customer information for cross-referencing
            """

        # Format the message with actual document content
        formatted_message = MESSAGE_TEMPLATE.format(
            document_text=document_text[:3000],  # Limit text length if needed
            entities=entities_formatted,
            document_type=document_type,
            statement_specific_instructions=statement_specific_instructions,
        )

        # Add RAG context if available
        if rag_context:
            formatted_message += f"\n\n{rag_context}"

        # If this is a new invoice type, add a note to the prompt
        if is_new_invoice_type:
            formatted_message += (
                "\n\nNOTE: This appears to be a new invoice type not seen before. "
                "Please pay extra attention to field extraction and validation."
            )

            # Flag for human review
            flag_for_human_review(
                {
                    "document_text": document_text,
                    "entities": entities_dict,
                    "document_json": document_json_string,
                    "filename": filename,
                },
                "New invoice type detected",
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
            metadata = {
                "filename": filename,
                "processing_time": datetime.now().isoformat(),
            }
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


# TODO Current file sorting is for local storage, do we have ability to store in Azure?
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


def sort_statements_by_vendor(processed_data, pdf_filename, pdf_content=None):
    """
    Sort statements into directories based on the Vendor Name found in the statement.
    Organizes statements in a hierarchical structure:
    /processed_statements/[Vendor Name]/[YYYY-MM-Month]/[statement_file.pdf]

    Also extracts invoice references for cross-validation.

    Args:
        processed_data (dict): The processed data from Vertex AI
        pdf_filename (str): The original PDF filename
        pdf_content (bytes, optional): The PDF file content if available

    Returns:
        tuple: (path where the statement was saved, list of referenced invoice numbers)
    """
    # Create base directory if it doesn't exist
    if not os.path.exists(STATEMENT_STORAGE_DIR):
        os.makedirs(STATEMENT_STORAGE_DIR)

    # Extract vendor name
    vendor_name = None
    if "Vendor Name" in processed_data:
        vendor_name = processed_data["Vendor Name"]
        print(f"Found vendor name: {vendor_name}")

    # If no vendor name found, try to extract from filename
    if not vendor_name or vendor_name.lower() == "not found":
        # Try to extract vendor name from filename
        parts = pdf_filename.split("_from_")
        if len(parts) > 1:
            vendor_parts = parts[1].split(".")
            vendor_name = vendor_parts[0].replace("_", " ")
            print(f"Extracted vendor name from filename: {vendor_name}")

    # If still no vendor name, use "Unknown Vendor"
    if not vendor_name or vendor_name.strip() == "":
        vendor_name = "Unknown Vendor"
        print("No vendor name found, using 'Unknown Vendor'")

    # Clean up vendor name to be directory-friendly
    vendor_name = vendor_name.replace("/", "_").replace("\\", "_").strip()
    vendor_name = vendor_name.replace(":", "_").replace("*", "_").replace("?", "_")
    vendor_name = vendor_name.replace("<", "_").replace(">", "_").replace("|", "_")
    vendor_name = vendor_name.replace('"', "_").replace("'", "_")

    # Create directory for this vendor if it doesn't exist
    vendor_dir = os.path.join(STATEMENT_STORAGE_DIR, vendor_name)
    if not os.path.exists(vendor_dir):
        os.makedirs(vendor_dir)
        print(f"Created directory for vendor: {vendor_dir}")

    # Create a date-based subdirectory if we have statement date
    statement_date = None
    date_fields = ["Statement Date", "Date", "StatementDate"]
    for field in date_fields:
        if field in processed_data and processed_data[field]:
            statement_date = processed_data[field]
            break

    if statement_date:
        try:
            # Try to parse and standardize the date format
            parsed_date = dateutil_parser.parse(statement_date)
            # Create a more descriptive month directory format: YYYY-MM-MonthName
            month_name = parsed_date.strftime("%B")  # Full month name
            date_dir = parsed_date.strftime(f"%Y-%m-{month_name}")

            # Create the month directory within the vendor directory
            month_dir = os.path.join(vendor_dir, date_dir)
            if not os.path.exists(month_dir):
                os.makedirs(month_dir)
                print(f"Created month subdirectory: {month_dir}")

            # Update vendor_dir to point to the month directory for file saving
            vendor_dir = month_dir
        except (ValueError, TypeError, OverflowError) as e:
            # If date parsing fails, just use the original vendor directory
            print(f"Could not parse statement date: {statement_date}. Error: {str(e)}")

    # Determine the destination path
    dest_path = os.path.join(vendor_dir, pdf_filename)

    # If we have the PDF content, save it to the destination
    if pdf_content:
        with open(dest_path, "wb") as f:
            f.write(pdf_content)
        print(f"Saved statement to {dest_path}")
    else:
        print(f"Would save statement to {dest_path} (PDF content not available)")

    # Extract referenced invoice numbers for cross-validation
    referenced_invoices = []

    # Check for Related Invoices field
    if "Related Invoices" in processed_data:
        invoice_text = processed_data["Related Invoices"]
        if invoice_text and invoice_text.lower() != "not found":
            # Split by commas, semicolons, or newlines
            import re

            invoice_list = re.split(r"[,;\n]", invoice_text)
            referenced_invoices = [inv.strip() for inv in invoice_list if inv.strip()]
            print(f"Found {len(referenced_invoices)} referenced invoices in statement")

    # Also look for invoice numbers in line items
    for key, value in processed_data.items():
        if isinstance(value, str) and "invoice" in key.lower():
            if value and value.lower() != "not found":
                referenced_invoices.append(value.strip())
                print(f"Found invoice reference in {key}: {value}")

    # Add the path and vendor name to the processed data for reference
    processed_data["Statement_Path"] = dest_path
    processed_data["Vendor_Name"] = vendor_name
    processed_data["Referenced_Invoices"] = ", ".join(referenced_invoices)

    return dest_path, referenced_invoices


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
                # First get some text to determine if this is a statement
                initial_document = process_document_from_memory(
                    image_content=payload,
                    mime_type=MIME_TYPE,
                    project_id=PROJECT_ID,
                    location=LOCATION,
                    processor_id=PROCESSOR_ID,
                    field_mask="text",  # Just get text for initial detection
                    processor_version_id=PROCESSOR_VERSION_ID,
                )

                # Check if this is a statement
                is_statement_doc = is_statement(initial_document.text, filename)

                # Now process with the appropriate processor
                document = process_document_from_memory(
                    image_content=payload,
                    mime_type=MIME_TYPE,
                    project_id=PROJECT_ID,
                    location=LOCATION,
                    processor_id=PROCESSOR_ID,
                    field_mask=FIELD_MASK,
                    processor_version_id=PROCESSOR_VERSION_ID,
                    is_statement_doc=is_statement_doc,
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


def add_missing_columns(df: pd.DataFrame, table_name: str):
    """Add any missing columns to the specified Snowflake table"""
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
          AND table_name = '{table_name}'
        """

        cs.execute(table_columns_sql)
        existing_columns = {row[0].upper() for row in cs.fetchall()}

        # Find new columns to add
        new_columns_to_add = df_columns - existing_columns

        # Add each new column
        for col in new_columns_to_add:
            alter_table_sql = f"""
            ALTER TABLE {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{table_name}
            ADD COLUMN {col} VARCHAR;
            """

            try:
                cs.execute(alter_table_sql)
                print(f"Added column '{col}' to table '{table_name}'.")
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


def check_for_duplicate_invoice(cs, invoice_number):
    """
    Check if an invoice with the same Invoice Number already exists in Snowflake

    Args:
        cs: Snowflake cursor
        invoice_number: Invoice number to check

    Returns:
        bool: True if duplicate exists, False otherwise
    """
    if not invoice_number:
        # If invoice number is missing, we can't check for duplicates properly
        return False

    try:
        # Query to check for duplicates
        query = f"""
        SELECT COUNT(*)
        FROM {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_INVOICE_HEADER_TABLE}
        WHERE UPPER(INVOICE_NUMBER) = UPPER(%s)
        """

        # Execute query with parameters
        cs.execute(query, (invoice_number,))

        # Get result
        count = cs.fetchone()[0]

        # Return True if duplicate exists
        return count > 0
    except Exception as e:
        print(f"Error checking for duplicate invoice: {e}")
        # In case of error, return False to allow insertion (better to have duplicates than missing data)
        return False


def check_for_duplicate_statement(cs, statement_id):
    """
    Check if a statement with the same Statement ID already exists in Snowflake

    Args:
        cs: Snowflake cursor
        statement_id: Statement ID to check

    Returns:
        bool: True if duplicate exists, False otherwise
    """
    if not statement_id:
        # If statement ID is missing, we can't check for duplicates properly
        return False

    try:
        # Query to check for duplicates
        query = f"""
        SELECT COUNT(*)
        FROM {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_STATEMENTS_TABLE}
        WHERE UPPER(STATEMENT_ID) = UPPER(%s)
        """

        # Execute query with parameters
        cs.execute(query, (statement_id,))

        # Get result
        count = cs.fetchone()[0]

        # Return True if duplicate exists
        return count > 0
    except Exception as e:
        print(f"Error checking for duplicate statement: {e}")
        # In case of error, return False to allow insertion (better to have duplicates than missing data)
        return False


def prepare_invoice_header_data(processed_data):
    """
    Prepare data for the LLE_INVOICE_HEADER table

    Args:
        processed_data (dict): Processed invoice data

    Returns:
        dict: Data formatted for the invoice header table
    """
    # Map processed data fields to invoice header table columns
    header_data = {
        "INVOICE_NUMBER": processed_data.get("InvoiceNumber"),
        "VENDOR_NAME": processed_data.get("VendorName"),
        "INVOICE_DATE": processed_data.get("InvoiceDate"),
        "SUBTOTAL": processed_data.get("Subtotal"),
        "TAX": processed_data.get("SalesTax"),
        "TOTAL_AMOUNT_DUE": processed_data.get("TotalAmountDue"),
        "CUSTOMER_ID": processed_data.get("CustomerID"),
        "SHIP_TO_ADDRESS": processed_data.get("ShipToAddress"),
        "PROCESSED_DATE": datetime.now().strftime("%Y-%m-%d"),
    }

    # Add any extra details as JSON in EXTRA_DETAILS column
    extra_details = {}
    for key, value in processed_data.items():
        if (
            key
            not in [
                "InvoiceNumber",
                "VendorName",
                "InvoiceDate",
                "Subtotal",
                "SalesTax",
                "TotalAmountDue",
                "CustomerID",
                "ShipToAddress",
            ]
            and value
        ):
            extra_details[key] = value

    if extra_details:
        header_data["EXTRA_DETAILS"] = json.dumps(extra_details)

    return header_data


def prepare_invoice_line_items(processed_data):
    """
    Prepare data for the LLE_INVOICE_LINE_ITEMS table

    Args:
        processed_data (dict): Processed invoice data

    Returns:
        list: List of dictionaries for each line item
    """
    line_items = []
    invoice_number = processed_data.get("InvoiceNumber")

    # Extract line items from processed data
    # Line items are typically numbered (e.g., Description 1, Quantity 1, etc.)
    item_count = 0
    while True:
        item_count += 1
        description_key = f"Description{item_count}"
        quantity_key = f"Quantity{item_count}"
        unit_price_key = f"UnitPrice{item_count}"
        line_total_key = f"TotalAmount{item_count}"
        well_name_key = f"CHARGE{item_count}"

        # Check if this line item exists
        if (
            description_key not in processed_data
            and description_key.replace("Description", "Description ")
            not in processed_data
        ):
            # Try with space
            description_key = description_key.replace("Description", "Description ")
            quantity_key = quantity_key.replace("Quantity", "Quantity ")
            unit_price_key = unit_price_key.replace("UnitPrice", "Unit Price ")
            line_total_key = line_total_key.replace("TotalAmount", "Total Amount ")
            well_name_key = well_name_key.replace("CHARGE", "CHARGE ")

            # Check again with space
            if description_key not in processed_data:
                # No more line items
                break

        # Extract line item data
        description = processed_data.get(description_key)
        quantity = processed_data.get(quantity_key)
        unit_price = processed_data.get(unit_price_key)
        line_total = processed_data.get(line_total_key)
        well_name = processed_data.get(well_name_key)

        # Skip if no description (likely not a valid line item)
        if not description or description.lower() == "not found":
            continue

        # Create line item record
        line_item = {
            "INVOICE_NUMBER": invoice_number,
            "WELL_NAME": well_name,
            "ITEM_DESCRIPTION": description,
            "QUANTITY": quantity,
            "UNIT_PRICE": unit_price,
            "LINE_TOTAL": line_total,
        }

        # Add any extra details as JSON
        extra_details = {}
        for key, value in processed_data.items():
            if key.startswith(f"LineItem{item_count}") and value:
                extra_details[key] = value

        if extra_details:
            line_item["EXTRA_DETAILS"] = json.dumps(extra_details)

        line_items.append(line_item)

    return line_items


def prepare_statement_data(processed_data):
    """
    Prepare data for the LLE_STATEMENTS table

    Args:
        processed_data (dict): Processed statement data

    Returns:
        dict: Data formatted for the statements table
    """
    # Generate a statement ID if not present
    statement_id = processed_data.get("StatementID")
    if not statement_id:
        vendor_name = processed_data.get("VendorName", "Unknown")
        statement_date = processed_data.get(
            "StatementDate", datetime.now().strftime("%Y-%m-%d")
        )
        statement_id = f"{vendor_name}_{statement_date}_{hash(vendor_name + statement_date) % 10000}"

    # Map processed data fields to statements table columns
    statement_data = {
        "STATEMENT_ID": statement_id,
        "VENDOR_NAME": processed_data.get("VendorName"),
        "CUSTOMER_NAME": processed_data.get("CustomerName", "Lucky Lad Energy"),
        "STATEMENT_DATE": processed_data.get("StatementDate"),
        "TOTAL_AMOUNT_DUE": processed_data.get("TotalAmountDue"),
        "CURRENT_AMOUNT": processed_data.get("CurrentAmount"),
        "PAST_DUE_1_30": processed_data.get("PastDue1_30"),
        "PAST_DUE_31_60": processed_data.get("PastDue31_60"),
        "PAST_DUE_61_90": processed_data.get("PastDue61_90"),
        "PAST_DUE_OVER_90": processed_data.get("PastDueOver90"),
        "CREATED_AT": datetime.now(),
        "UPDATED_AT": datetime.now(),
    }

    return statement_data


def prepare_statement_transactions(processed_data, statement_id):
    """
    Prepare data for the LLE_STATEMENT_TRANSACTIONS table

    Args:
        processed_data (dict): Processed statement data
        statement_id (str): The ID of the parent statement

    Returns:
        list: List of dictionaries for each transaction
    """
    transactions = []

    # Note: Referenced invoices extraction removed as it wasn't used in this function

    # Process each transaction
    transaction_count = 0
    while True:
        transaction_count += 1

        # Check for transaction fields with different possible naming patterns
        date_key = f"TransactionDate{transaction_count}"
        desc_key = f"Description{transaction_count}"
        amount_key = f"Amount{transaction_count}"
        balance_key = f"BalanceAfter{transaction_count}"

        # Try with spaces in keys
        if date_key not in processed_data:
            date_key = date_key.replace("TransactionDate", "Transaction Date ")
            desc_key = desc_key.replace("Description", "Description ")
            amount_key = amount_key.replace("Amount", "Amount ")
            balance_key = balance_key.replace("BalanceAfter", "Balance After ")

        # Check if this transaction exists
        if date_key not in processed_data and desc_key not in processed_data:
            # No more transactions
            break

        # Extract transaction data
        transaction_date = processed_data.get(date_key)
        description = processed_data.get(desc_key)
        amount = processed_data.get(amount_key)
        balance_after = processed_data.get(balance_key)

        # Skip if no description or amount (likely not a valid transaction)
        if (not description or description.lower() == "not found") and (
            not amount or amount.lower() == "not found"
        ):
            continue

        # Generate transaction ID
        transaction_id = f"{statement_id}_TRANS_{transaction_count}"

        # Try to extract invoice number from description
        invoice_number = None
        well_name = None
        due_date = None
        original_amount = None
        transaction_type = "UNKNOWN"

        if description:
            # Look for invoice number pattern
            import re

            invoice_match = re.search(
                r"(?:INV|INVOICE)[:\s#]*(\w+)", description, re.IGNORECASE
            )
            if invoice_match:
                invoice_number = invoice_match.group(1)
                transaction_type = "INVOICE"

            # Look for well name
            well_patterns = [
                r"(?:WELL|LEASE)[:\s#]*(\w+(?:\s+\w+)?)",
                r"(GODCHAUX|MCINIS|KIRBY|TEMPLE)",
            ]

            for pattern in well_patterns:
                well_match = re.search(pattern, description, re.IGNORECASE)
                if well_match:
                    well_name = well_match.group(1)
                    break

            # Look for due date
            due_match = re.search(r"DUE[:\s]*([\d/]+)", description, re.IGNORECASE)
            if due_match:
                due_date = due_match.group(1)

            # Look for original amount
            amount_match = re.search(
                r"ORIGINAL[:\s]*\$?([\d,.]+)", description, re.IGNORECASE
            )
            if amount_match:
                original_amount = amount_match.group(1)

            # Determine transaction type
            if "PAYMENT" in description.upper() or "PAID" in description.upper():
                transaction_type = "PAYMENT"
            elif "CREDIT" in description.upper():
                transaction_type = "CREDIT"
            elif "JOURNAL" in description.upper() or "REVERSAL" in description.upper():
                transaction_type = "JOURNAL_REVERSAL"

        # Create transaction record
        transaction = {
            "TRANSACTION_ID": transaction_id,
            "STATEMENT_ID": statement_id,
            "TRANSACTION_DATE": transaction_date,
            "DESCRIPTION": description,
            "AMOUNT": amount,
            "BALANCE_AFTER": balance_after,
            "DUE_DATE": due_date,
            "ORIGINAL_AMOUNT": original_amount,
            "WELL_NAME": well_name,
            "TRANSACTION_TYPE": transaction_type,
        }

        transactions.append(transaction)

    return transactions


def upload_to_snowflake_tables(processed_data_list):
    """
    Upload processed data to appropriate Snowflake tables based on document type

    Args:
        processed_data_list (list): List of processed document data

    Returns:
        dict: Statistics about the upload operation
    """
    if not processed_data_list:
        print("No data to upload to Snowflake.")
        return {"success": False, "message": "No data to upload"}

    ctx = None
    cs = None

    # Track statistics
    stats = {
        "total_documents": len(processed_data_list),
        "invoices_processed": 0,
        "statements_processed": 0,
        "invoice_headers_inserted": 0,
        "invoice_line_items_inserted": 0,
        "statements_inserted": 0,
        "statement_transactions_inserted": 0,
        "errors": [],
    }

    try:
        # Connect to Snowflake
        ctx = snowflake.connector.connect(
            account=SNOWFLAKE_ACCOUNT,
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA,
            warehouse=SNOWFLAKE_WAREHOUSE,
        )

        cs = ctx.cursor()

        # Process each document
        for processed_data in processed_data_list:
            try:
                # Determine document type
                document_type = processed_data.get("DocumentType", "UNKNOWN")

                if document_type == "INVOICE":
                    # Process invoice
                    stats["invoices_processed"] += 1

                    # Check for duplicate invoice
                    invoice_number = processed_data.get("InvoiceNumber")
                    if check_for_duplicate_invoice(cs, invoice_number):
                        print(
                            f"Skipping duplicate invoice: Invoice Number={invoice_number}"
                        )
                        continue

                    # Prepare and insert invoice header
                    header_data = prepare_invoice_header_data(processed_data)
                    if header_data and header_data["INVOICE_NUMBER"]:
                        # Convert header_data to DataFrame
                        header_df = pd.DataFrame([header_data])

                        # Ensure all necessary columns exist
                        add_missing_columns(header_df, SNOWFLAKE_INVOICE_HEADER_TABLE)

                        # Insert header data
                        columns = ", ".join(header_df.columns)
                        placeholders = ", ".join(["%s"] * len(header_df.columns))
                        sql = f"INSERT INTO {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_INVOICE_HEADER_TABLE} ({columns}) VALUES ({placeholders})"

                        cs.execute(sql, tuple(header_df.iloc[0].values))
                        stats["invoice_headers_inserted"] += 1

                        # Prepare and insert line items
                        line_items = prepare_invoice_line_items(processed_data)
                        if line_items:
                            # Convert line_items to DataFrame
                            line_items_df = pd.DataFrame(line_items)

                            # Ensure all necessary columns exist
                            add_missing_columns(
                                line_items_df, SNOWFLAKE_INVOICE_LINE_ITEMS_TABLE
                            )

                            # Insert each line item
                            columns = ", ".join(line_items_df.columns)
                            placeholders = ", ".join(
                                ["%s"] * len(line_items_df.columns)
                            )
                            sql = f"INSERT INTO {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_INVOICE_LINE_ITEMS_TABLE} ({columns}) VALUES ({placeholders})"

                            for _, row in line_items_df.iterrows():
                                cs.execute(sql, tuple(row.values))
                                stats["invoice_line_items_inserted"] += 1

                elif document_type == "STATEMENT":
                    # Process statement
                    stats["statements_processed"] += 1

                    # Prepare statement data
                    statement_data = prepare_statement_data(processed_data)

                    # Check for duplicate statement
                    statement_id = statement_data.get("STATEMENT_ID")
                    if check_for_duplicate_statement(cs, statement_id):
                        print(
                            f"Skipping duplicate statement: Statement ID={statement_id}"
                        )
                        continue

                    # Insert statement data
                    if statement_data and statement_id:
                        # Convert statement_data to DataFrame
                        statement_df = pd.DataFrame([statement_data])

                        # Ensure all necessary columns exist
                        add_missing_columns(statement_df, SNOWFLAKE_STATEMENTS_TABLE)

                        # Insert statement data
                        columns = ", ".join(statement_df.columns)
                        placeholders = ", ".join(["%s"] * len(statement_df.columns))
                        sql = f"INSERT INTO {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_STATEMENTS_TABLE} ({columns}) VALUES ({placeholders})"

                        cs.execute(sql, tuple(statement_df.iloc[0].values))
                        stats["statements_inserted"] += 1

                        # Prepare and insert transactions
                        transactions = prepare_statement_transactions(
                            processed_data, statement_id
                        )
                        if transactions:
                            # Convert transactions to DataFrame
                            transactions_df = pd.DataFrame(transactions)

                            # Ensure all necessary columns exist
                            add_missing_columns(
                                transactions_df, SNOWFLAKE_STATEMENT_TRANSACTIONS_TABLE
                            )

                            # Insert each transaction
                            columns = ", ".join(transactions_df.columns)
                            placeholders = ", ".join(
                                ["%s"] * len(transactions_df.columns)
                            )
                            sql = f"INSERT INTO {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_STATEMENT_TRANSACTIONS_TABLE} ({columns}) VALUES ({placeholders})"

                            for _, row in transactions_df.iterrows():
                                cs.execute(sql, tuple(row.values))
                                stats["statement_transactions_inserted"] += 1

                else:
                    # Unknown document type
                    print(f"Unknown document type: {document_type}")
                    stats["errors"].append(f"Unknown document type: {document_type}")

            except Exception as e:
                error_msg = f"Error processing document: {str(e)}"
                print(error_msg)
                stats["errors"].append(error_msg)

        # Commit all changes
        ctx.commit()

        print(f"Successfully processed {stats['total_documents']} documents:")
        print(
            f"  - Invoices: {stats['invoices_processed']} (Headers: {stats['invoice_headers_inserted']}, Line Items: {stats['invoice_line_items_inserted']})"
        )
        print(
            f"  - Statements: {stats['statements_processed']} (Headers: {stats['statements_inserted']}, Transactions: {stats['statement_transactions_inserted']})"
        )

        if stats["errors"]:
            print(f"  - Errors: {len(stats['errors'])}")

        stats["success"] = True

    except snowflake.connector.errors.Error as e:
        error_msg = f"Snowflake Error: {str(e)}"
        print(error_msg)
        stats["success"] = False
        stats["message"] = error_msg
        stats["errors"].append(error_msg)

    except Exception as e:
        error_msg = f"General Error: {str(e)}"
        print(error_msg)
        stats["success"] = False
        stats["message"] = error_msg
        stats["errors"].append(error_msg)

    finally:
        if cs:
            cs.close()
        if ctx:
            ctx.close()

    return stats


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


def process_all_responses(
    vertex_ai_responses, extracted_data, perform_cross_validation=True
):
    """
    Process all Vertex AI responses into a DataFrame

    Args:
        vertex_ai_responses (dict): Responses from Vertex AI
        extracted_data (list): Extracted data from documents
        perform_cross_validation (bool): Whether to perform cross-validation for statements

    Returns:
        pd.DataFrame: Processed data as a DataFrame
    """
    all_processed_data = []

    for i, (response_name, response_content) in enumerate(vertex_ai_responses.items()):
        # Process the response
        processed_data = process_vertex_response(response_content)

        # Add document metadata if available
        if extracted_data and i < len(extracted_data):
            processed_data["PDF Filename"] = extracted_data[i].get("filename")

            # Determine if this is a statement or invoice
            filename = extracted_data[i].get("filename", "")
            document_text = extracted_data[i].get("text", "")
            is_statement_doc = is_statement(document_text, filename)

            # Add document type to processed data
            processed_data["Document Type"] = (
                "STATEMENT" if is_statement_doc else "INVOICE"
            )

            # Sort and save to appropriate directory based on document type
            if "filename" in extracted_data[i] and "pdf_content" in extracted_data[i]:
                if is_statement_doc:
                    # For statements, sort by vendor and extract referenced invoices
                    statement_path, referenced_invoices = sort_statements_by_vendor(
                        processed_data,
                        extracted_data[i]["filename"],
                        extracted_data[i]["pdf_content"],
                    )

                    # Store referenced invoices for cross-validation
                    processed_data["Referenced Invoices"] = ", ".join(
                        referenced_invoices
                    )
                else:
                    # For invoices, sort by well name
                    sort_invoices_by_well_name(
                        processed_data,
                        extracted_data[i]["filename"],
                        extracted_data[i]["pdf_content"],
                    )

                    # Flag new invoice types for human review
                    if is_statement_doc and "new_statement_type" in processed_data.get(
                        "flags", []
                    ):
                        flag_for_human_review(
                            processed_data, "New statement type detected"
                        )

        all_processed_data.append(processed_data)

    # Create DataFrame from all processed data
    if all_processed_data:
        final_df = pd.DataFrame(all_processed_data)

        # Clean column names (remove spaces)
        final_df.columns = [col.replace(" ", "") for col in final_df.columns]

        # Perform cross-validation for statements if requested
        if perform_cross_validation:
            # Connect to Snowflake for cross-validation
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

                # Find statements in the processed data
                statement_rows = final_df[final_df["DocumentType"] == "STATEMENT"]

                if not statement_rows.empty:
                    print(
                        f"\nPerforming cross-validation for {len(statement_rows)} statements..."
                    )

                    for idx, statement in statement_rows.iterrows():
                        statement_dict = statement.to_dict()

                        # Cross-validate with invoices
                        validation_results = cross_validate_statement_with_invoices(
                            statement_dict, cs
                        )

                        # Update the DataFrame with validation results
                        final_df.at[idx, "ValidationStatus"] = validation_results[
                            "status"
                        ]
                        final_df.at[idx, "DiscrepanciesFound"] = len(
                            validation_results["discrepancies"]
                        )

                        # Flag for human review if discrepancies found
                        if validation_results["discrepancies"]:
                            print(
                                f"Found {len(validation_results['discrepancies'])} discrepancies in statement {statement_dict.get('PDFFilename', '')}"
                            )
                            statement_dict["validation_results"] = validation_results
                            flag_for_human_review(
                                statement_dict,
                                "Discrepancies found during cross-validation",
                            )

                # Close Snowflake connection
                cs.close()
                ctx.close()

            except Exception as e:
                print(f"Error during cross-validation: {e}")
                print("Cross-validation skipped due to error")

        return final_df
    else:
        return pd.DataFrame()


def cross_validate_statement_with_invoices(statement_data, snowflake_cursor):
    """
    Cross-validate statement data with invoices in the database

    Args:
        statement_data (dict): Processed statement data
        snowflake_cursor: Snowflake cursor for database queries

    Returns:
        dict: Validation results with discrepancies
    """
    # Extract referenced invoice numbers
    referenced_invoices = []
    if "Referenced_Invoices" in statement_data:
        invoice_str = statement_data["Referenced_Invoices"]
        if invoice_str and invoice_str.strip():
            referenced_invoices = [inv.strip() for inv in invoice_str.split(",")]

    if not referenced_invoices:
        print("No invoice references found in statement for cross-validation")
        return {"status": "no_references", "discrepancies": []}

    # Get vendor name
    vendor_name = statement_data.get(
        "Vendor_Name", statement_data.get("VendorName", "")
    )
    if not vendor_name:
        print("No vendor name found in statement for cross-validation")
        return {"status": "no_vendor", "discrepancies": []}

    # Query Snowflake for matching invoices
    discrepancies = []
    found_invoices = []

    try:
        for invoice_number in referenced_invoices:
            query = f"""
            SELECT *
            FROM {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.{SNOWFLAKE_INVOICE_HEADER_TABLE}
            WHERE UPPER(VENDOR_NAME) = UPPER(%s)
            AND UPPER(INVOICE_NUMBER) = UPPER(%s)
            """

            snowflake_cursor.execute(query, (vendor_name, invoice_number))
            result = snowflake_cursor.fetchone()

            if result:
                # Convert result to dictionary
                columns = [col[0] for col in snowflake_cursor.description]
                invoice_data = dict(zip(columns, result))
                found_invoices.append(invoice_data)

                # Check for amount discrepancies
                statement_amount = statement_data.get(
                    f"Amount_{invoice_number}",
                    statement_data.get("TotalAmountDue", "0"),
                )
                invoice_amount = invoice_data.get("TOTAL_AMOUNT_DUE", "0")

                # Convert to float for comparison
                try:
                    statement_amount = float(
                        statement_amount.replace("$", "").replace(",", "")
                    )
                    invoice_amount = float(
                        invoice_amount.replace("$", "").replace(",", "")
                    )

                    # Check for discrepancy (allow small rounding differences)
                    if abs(statement_amount - invoice_amount) > 0.01:
                        discrepancies.append(
                            {
                                "invoice_number": invoice_number,
                                "statement_amount": statement_amount,
                                "invoice_amount": invoice_amount,
                                "difference": statement_amount - invoice_amount,
                            }
                        )
                except (ValueError, AttributeError):
                    # If conversion fails, log as potential discrepancy
                    discrepancies.append(
                        {
                            "invoice_number": invoice_number,
                            "statement_amount": statement_amount,
                            "invoice_amount": invoice_amount,
                            "difference": "Could not compare amounts",
                        }
                    )
            else:
                # Invoice referenced in statement not found in database
                discrepancies.append(
                    {
                        "invoice_number": invoice_number,
                        "issue": "Invoice referenced in statement not found in database",
                    }
                )

        # Return validation results
        return {
            "status": "completed",
            "invoices_referenced": len(referenced_invoices),
            "invoices_found": len(found_invoices),
            "discrepancies": discrepancies,
        }

    except Exception as e:
        print(f"Error during statement cross-validation: {e}")
        return {"status": "error", "message": str(e), "discrepancies": []}


def flag_for_human_review(document_data, reason):
    """Flag a document (invoice or statement) for human review and store it for later processing"""
    if not os.path.exists(REVIEW_DIR):
        os.makedirs(REVIEW_DIR)

    # Create a unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Determine document type
    document_type = "invoice"
    if (
        "Document Type" in document_data
        and document_data["Document Type"] == "STATEMENT"
    ):
        document_type = "statement"

    filename = f"{REVIEW_DIR}/review_{document_type}_{timestamp}.json"

    # Store the document data and reason for review
    review_data = {
        "document_data": document_data,
        "document_type": document_type,
        "reason": reason,
        "timestamp": timestamp,
        "status": "pending_review",
    }

    with open(filename, "w") as f:
        json.dump(review_data, f, indent=2)

    print(f"Flagged invoice for human review: {filename}")
    return filename


def add_to_document_ai_dataset(
    project_id,
    location,
    processor_id,
    dataset_id,
    document_content,
    ground_truth_entities,
):
    """Add a corrected document to a Document AI dataset for retraining"""
    try:
        from google.cloud import documentai_v1 as documentai_dataset

        # Initialize Document AI client
        client = documentai_dataset.DocumentProcessorServiceClient()

        # Format the dataset path
        dataset_path = client.dataset_path(
            project_id, location, processor_id, dataset_id
        )

        # Create the document with ground truth annotations
        # This is a simplified example - actual implementation would be more complex
        document = {
            "raw_document": {
                "content": document_content,
                "mime_type": "application/pdf",
            },
            "ground_truth": {"entities": ground_truth_entities},
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


def main(debug_mode=False, cross_validate=True):
    """
    Main function to run the document processor

    Args:
        debug_mode (bool): Whether to run in debug mode with detailed logging
        cross_validate (bool): Whether to perform cross-validation for statements
    """
    print("=== Lucky Lad Document Processor ===")
    print(f"Starting at {datetime.now()}")

    # Initialize variables
    extracted_data = []
    vertex_ai_responses = {}

    # Process emails based on configuration
    if USE_OUTLOOK and OUTLOOK_AVAILABLE and OUTLOOK_EMAIL and OUTLOOK_PASSWORD:
        print("\nChecking for new documents in Outlook...")
        outlook_data = process_outlook_pdfs(
            OUTLOOK_EMAIL, OUTLOOK_PASSWORD, OUTLOOK_SERVER
        )
        extracted_data.extend(outlook_data)
        print(f"Found {len(outlook_data)} new documents in Outlook")
    else:
        print("\nOutlook processing skipped (not configured or library not available)")

    # Always process Gmail for testing purposes unless explicitly disabled
    if GMAIL_USERNAME and GMAIL_PASSWORD:
        print("\nChecking for new documents in Gmail...")
        gmail_data = process_gmail_pdfs(GMAIL_USERNAME, GMAIL_PASSWORD)
        extracted_data.extend(gmail_data)
        print(f"Found {len(gmail_data)} new documents in Gmail")
    else:
        print("\nGmail processing skipped (not configured)")

    # Call Vertex AI for each document
    if extracted_data:
        print(f"\nProcessing {len(extracted_data)} documents with Vertex AI...")

        for i, data in enumerate(extracted_data):
            filename = data.get("filename", "Unknown")
            print(f"\nProcessing document {i + 1}: {filename}")
            document_json_string = data["document_json"]

            # Debug info if requested
            if debug_mode:
                print("\n--- DEBUG MODE: Vertex AI Input ---")
                debug_vertex_input(document_json_string)

            # Determine if this is a statement
            doc_data = json.loads(document_json_string)
            document_text = doc_data.get("text", "")
            is_statement_doc = is_statement(document_text, filename)

            # Call Vertex AI with RAG enhancement and document type
            vertex_ai_response = generate_content_with_vertex_ai(
                document_json_string, filename, is_statement_doc=is_statement_doc
            )

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

        # Process responses into a DataFrame with optional cross-validation
        final_df = process_all_responses(
            vertex_ai_responses, extracted_data, perform_cross_validation=cross_validate
        )

        if not final_df.empty:
            # Convert all columns to string to avoid Snowflake type issues
            final_df = final_df.astype(str)

            # Display the DataFrame
            print("\n--- Final DataFrame ---")
            print(f"DataFrame shape: {final_df.shape}")
            print(final_df.head())

            # Add to Snowflake
            try:
                print("\nUploading data to Snowflake tables...")
                # Convert DataFrame rows to list of dictionaries for processing
                processed_data_list = final_df.to_dict("records")
                upload_stats = upload_to_snowflake_tables(processed_data_list)
                if upload_stats["success"]:
                    print("Successfully added data to Snowflake tables.")
                    print(
                        f"  - Invoices: {upload_stats['invoices_processed']} (Headers: {upload_stats['invoice_headers_inserted']}, Line Items: {upload_stats['invoice_line_items_inserted']})"
                    )
                    print(
                        f"  - Statements: {upload_stats['statements_processed']} (Headers: {upload_stats['statements_inserted']}, Transactions: {upload_stats['statement_transactions_inserted']})"
                    )
                else:
                    print(
                        f"Error adding data to Snowflake: {upload_stats.get('message', 'Unknown error')}"
                    )
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
                        "email_datetime": data.get(
                            "email_datetime", datetime.now()
                        ).isoformat(),
                        "processed_data": final_df.iloc[i].to_dict()
                        if i < len(final_df)
                        else {},
                    }
                    success = rag.add_invoice(document_text, entities_dict, metadata)
                    if success:
                        print(
                            f"Added invoice {data.get('filename', 'unknown')} to RAG database"
                        )
                    else:
                        print(
                            f"Failed to add invoice {data.get('filename', 'unknown')} to RAG database"
                        )
        else:
            print("No data could be extracted from Vertex AI responses.")
    else:
        print("No Vertex AI responses to process.")

    print(f"\nScript finished at {datetime.now()}.")
    return True


if __name__ == "__main__":
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Lucky Lad Document Processor")
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug mode with detailed logging"
    )
    parser.add_argument(
        "--no-cross-validate",
        action="store_true",
        help="Disable cross-validation for statements",
    )
    args = parser.parse_args()

    # Set environment variable for GCP authentication
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "path/to/your/application_default_credentials.json",
    )

    # Run the main process with command line arguments
    main(debug_mode=args.debug, cross_validate=not args.no_cross_validate)
