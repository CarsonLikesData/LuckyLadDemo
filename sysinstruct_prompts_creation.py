import json

def read_text_from_file(filename):
    """
    Reads the text content from a file.
    Replace this with your actual file reading logic (e.g., for PDF, TXT).
    """
    # --- Replace this with your file reading code ---
    print(f"Reading text from: {filename}")
    return f"Text from {filename}"  # Placeholder
    # --------------------------------------------

def gemini_extract(text, prompt, system_instructions):
    """
    Calls the Gemini model to extract data.
    Replace this with your actual Gemini API call.
    """
    # --- Replace this with your Gemini API call ---
    print("\n--- Gemini Extraction ---")
    print("Prompt:\n", prompt)
    print("System Instructions:\n", system_instructions)
    print("Text:\n", text)
    return {"extracted_data": "Dummy Data"}  # Placeholder
    # -----------------------------------------

invoices_data = [
    {
        "filename": "1124132[90].pdf",
        "prompt": """You are a document entity extraction specialist. Given an invoice, your task is to extract the text value of the following entities:

{
    "invoice_id": "",
    "invoice_date": "",
    "po_number": "",
    "terms": "",
    "ship_date": "",
    "ship_via": "",
    "unit_number": "",
    "bill_to": {
        "customer_name": "Lucky Lad Energy",
        "address": "P.O. Box 1379 Conroe, TX 77305"
    },
    "ship_to": {
        "customer_name": "Lucky Lad Energy",
        "address": "Kirby McInnis Tank Battery"
    },
    "line_items": [
        {
            "quantity": "",
            "description": "",
            "unit_price": "",
            "amount": ""
        }
    ],
    "subtotal": "",
    "sales_tax": "",
    "total_amount": "",
    "payments_credits": "",
    "balance_due": ""
}
""",
        "system_instructions": """-   The JSON schema above must be strictly followed during the extraction.  Do not add any extra fields or change the field names.
-   The values must only include text found in the document. Do not invent or generate any values.
-   Do not normalize any entity value (e.g., dates, addresses, phone numbers, etc.). Extract them exactly as they appear in the document, preserving original formatting and spelling.
-   If an entity is not found in the document, set the entity value to `null` (without quotes).  Do not leave it empty.
-   If there are multiple line items, extract each as a separate object within the `line_items` array.
-   For date fields, if the date format is ambiguous, extract it as is.  Do not attempt to guess the date."""
    },
    {
        "filename": "20240701_112438.PDF",
        "prompt": """You are a document entity extraction specialist. Given an invoice, your task is to extract the text value of the following entities:

{
    "invoice_id": "",
    "invoice_date": "",
    "order_number": "",
    "charge_field": "",
    "parish": "",
    "quantity": "",
    "description": "",
    "labor": "",
    "materials": "",
    "taxable_total": "",
    "state_tax": "",
    "parish_tax": "",
    "total_amount": "",
    "ship_to": "Lucky Lad (invoice@luckylad.com)",
    "invoice_to": "Shop / Laf",
    "ord_by": "Mr Dexter Romero"
}
""",
        "system_instructions": """-   The JSON schema above must be strictly followed during the extraction.  Do not add any extra fields or change the field names.
-   The values must only include text found in the document. Do not invent or generate any values.
-   Do not normalize any entity value (e.g., dates, addresses, phone numbers, etc.). Extract them exactly as they appear in the document, preserving original formatting and spelling.
-   If an entity is not found in the document, set the entity value to `null` (without quotes).  Do not leave it empty.
-   If there are multiple line items, extract each as a separate object within the `line_items` array.
-   Extract "Charge Field" and "Parish" exactly as they appear in the document."""
    },
    {
        "filename": "ATKINSON PROPANE CO. INC.pdf",
        "prompt": """You are a document entity extraction specialist. Given an invoice, your task is to extract the text value of the following entities:

{
    "invoice_number": "",
    "date": "",
    "sold_to": "Lucky Lad Energy",
    "address": "Temple 26-2 514 232598",
    "gallons": "",
    "price_per_gallon": "",
    "amount": "",
    "fax": "",
    "tax": "",
    "total_payment_due": "",
    "tank_serial_number": "",
    "tank_size": "",
    "before": "",
    "after": "",
    "charge": "",
    "parish": "Bezu."
}
""",
        "system_instructions": """-   The JSON schema above must be strictly followed during the extraction.  Do not add any extra fields or change the field names.
-   The values must only include text found in the document. Do not invent or generate any values.
-   Do not normalize any entity value (e.g., dates, addresses, phone numbers, etc.). Extract them exactly as they appear in the document, preserving original formatting and spelling.
-   If an entity is not found in the document, set the entity value to `null` (without quotes).  Do not leave it empty.
-   Extract "CHARGE" exactly as it appears, even if it is circled."""
    },
    {
        "filename": "INV734477.pdf",
        "prompt": """You are a document entity extraction specialist. Given an invoice, your task is to extract the text value of the following entities:

{
    "invoice_number": "",
    "invoice_date": "",
    "due_date": "",
    "customer_id": "LUCK001",
    "lease_name": "Godchaux",
    "well_name": "",
    "property_no": "",
    "afe_po_no": "",
    "area": "Live Oak",
    "service_date": "4/10/2024",
    "order_no": "",
    "sales_person": "Justin Hebert",
    "bill_to": {
        "customer_name": "Lucky Lad Energy LLC",
        "attention": "Richard Hopper",
        "address": "PO Box 1379\\nConroe, TX 77305\\nUSA"
    },
    "ship_to": {
        "customer_name": "Lucky Lad Energy LLC",
        "attention": "Richard Hopper",
        "address": "PO Box 1379\\nConroe, TX 77305\\nUSA"
    },
    "line_items": [
        {
            "well_name": "",
            "item": "",
            "description": "",
            "unit": "",
            "quantity": "",
            "unit_price": "",
            "total_price": ""
        }
    ],
    "amount_subject_to_sales_tax": "",
    "amount_exempt_from_sales_tax": "",
    "subtotal": "",
    "invoice_discount": "",
    "total_sales_tax": "",
    "total": ""
}
""",
        "system_instructions": """-   The JSON schema above must be strictly followed during the extraction.  Do not add any extra fields or change the field names.
-   The values must only include text found in the document. Do not invent or generate any values.
-   Do not normalize any entity value (e.g., dates, addresses, phone numbers, etc.). Extract them exactly as they appear in the document, preserving original formatting and spelling.
-   If an entity is not found in the document, set the entity value to `null` (without quotes).  Do not leave it empty.
-   If there are multiple line items, extract each as a separate object within the `line_items` array.
-   For date fields, if the date format is ambiguous, extract it as is.  Do not attempt to guess the date."""
    },
    {
        "filename": "Statement1_from_REAGAN_POWER_COMPRESSION_LLC15308.pdf",
        "prompt": """You are a document entity extraction specialist. Given a statement, your task is to extract the text value of the following entities:

{
    "statement_date": "1/5/2024",
    "to": {
        "customer_name": "LUCKY LAD ENERGY LLC",
        "address": "PO BOX 1379\\nCONROE, TX 77305-1379"
    },
    "transactions": [
        {
            "date": "",
            "transaction": "",
            "amount": "",
            "balance": ""
        }
    ],
    "amount_due": "",
    "current": "",
    "days_1_30_past_due": "",
    "days_31_60_past_due": "",
    "days_61_90_past_due": "",
    "over_90_days_past_due": ""
}
""",
        "system_instructions": """-   The JSON schema above must be strictly followed during the extraction.  Do not add any extra fields or change the field names.
-   The values must only include text found in the document. Do not invent or generate any values.
-   Do not normalize any entity value (e.g., dates, addresses, phone numbers, etc.). Extract them exactly as they appear in the document, preserving original formatting and spelling.
-   If an entity is not found in the document, set the entity value to `null` (without quotes).  Do not leave it empty.
-   If there are multiple transactions, extract each as a separate object within the `transactions` array."""
    }
]

all_extracted_data = []

for data in invoices_data:
    filename = data["filename"]
    prompt = data["prompt"]
    system_instructions = data["system_instructions"]

    text = read_text_from_file(filename)  # Read text from the file
    extracted_data = gemini_extract(text, prompt, system_instructions)  # Extract data
    all_extracted_data.append(extracted_data)

print("\n--- All Extracted Data ---")
print(json.dumps(all_extracted_data, indent=4))