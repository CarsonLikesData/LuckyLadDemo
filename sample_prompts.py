import csv
import json
import os  # Import the os module

def create_csv_prompt_file(filename, data, variable_order):
    """
    Creates a CSV file in the specified subdirectory.

    Args:
        filename (str): The name of the CSV file to create.
        data (list of dict): A list of dictionaries for CSV rows.
        variable_order (list of str): Order of columns in the CSV.
    """

    subdirectory = "SI_and_prompt_templates"
    # Ensure the subdirectory exists
    os.makedirs(subdirectory, exist_ok=True)  # Create if it doesn't exist

    filepath = os.path.join(subdirectory, filename)  # Full file path
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(variable_order)
        for row in data:
            writer.writerow([row.get(var, '') for var in variable_order])

# --- CSV Data Definitions ---
# (Same data definitions as before)

# 1124132[90].pdf
csv_data_1124132 = [
    {
        "DOCUMENT_TYPE": "invoice",
        "ENTITY_JSON_SCHEMA": """
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
""",
        "ARRAY_FIELD_NAME": "line_items",
        "ADDITIONAL_INSTRUCTIONS": ""
    }
]
csv_variable_order_1124132 = ["DOCUMENT_TYPE", "ENTITY_JSON_SCHEMA", "ARRAY_FIELD_NAME", "ADDITIONAL_INSTRUCTIONS"]
create_csv_prompt_file("1124132_prompt.csv", csv_data_1124132, csv_variable_order_1124132)


# 20240701_112438.PDF
csv_data_20240701 = [
    {
        "DOCUMENT_TYPE": "invoice",
        "ENTITY_JSON_SCHEMA": """
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
""",
        "ARRAY_FIELD_NAME": "N/A",
        "ADDITIONAL_INSTRUCTIONS": 'Extract "Charge Field" and "Parish" exactly as they appear in the document.'
    }
]
csv_variable_order_20240701 = ["DOCUMENT_TYPE", "ENTITY_JSON_SCHEMA", "ARRAY_FIELD_NAME", "ADDITIONAL_INSTRUCTIONS"]
create_csv_prompt_file("20240701_prompt.csv", csv_data_20240701, csv_variable_order_20240701)

# ATKINSON PROPANE CO. INC.pdf
csv_data_atkinson = [
    {
        "DOCUMENT_TYPE": "invoice",
        "ENTITY_JSON_SCHEMA": """
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
""",
        "ARRAY_FIELD_NAME": "N/A",
        "ADDITIONAL_INSTRUCTIONS": 'Extract "CHARGE" exactly as it appears, even if it is circled.'
    }
]
csv_variable_order_atkinson = ["DOCUMENT_TYPE", "ENTITY_JSON_SCHEMA", "ARRAY_FIELD_NAME", "ADDITIONAL_INSTRUCTIONS"]
create_csv_prompt_file("atkinson_prompt.csv", csv_data_atkinson, csv_variable_order_atkinson)

# INV734477.pdf
csv_data_inv734477 = [
    {
        "DOCUMENT_TYPE": "invoice",
        "ENTITY_JSON_SCHEMA": """
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
""",
        "ARRAY_FIELD_NAME": "line_items",
        "ADDITIONAL_INSTRUCTIONS": ""
    }
]
csv_variable_order_inv734477 = ["DOCUMENT_TYPE", "ENTITY_JSON_SCHEMA", "ARRAY_FIELD_NAME", "ADDITIONAL_INSTRUCTIONS"]
create_csv_prompt_file("inv734477_prompt.csv", csv_data_inv734477, csv_variable_order_inv734477)

# Statement1_from_REAGAN_POWER_COMPRESSION_LLC15308.pdf
csv_data_statement = [
    {
        "DOCUMENT_TYPE": "statement",
        "ENTITY_JSON_SCHEMA": """
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
""",
        "ARRAY_FIELD_NAME": "transactions",
        "ADDITIONAL_INSTRUCTIONS": ""
    }
]
csv_variable_order_statement = ["DOCUMENT_TYPE", "ENTITY_JSON_SCHEMA", "ARRAY_FIELD_NAME", "ADDITIONAL_INSTRUCTIONS"]
create_csv_prompt_file("statement_prompt.csv", csv_data_statement, csv_variable_order_statement)


# Create the text files in the subdirectory
subdirectory = "SI_and_prompt_templates"
os.makedirs(subdirectory, exist_ok=True)
with open(os.path.join(subdirectory, "system_instructions_template.txt"), "w") as f:
    f.write("""You are a document entity extraction specialist. Given a document, your task is to extract the text value of the following entities:

{
    [ENTITY_JSON_SCHEMA]
}

-   The JSON schema must be followed during the extraction.
-   The values must only include text found in the document.
-   Do not normalize any entity value (e.g., dates, addresses, etc.). Extract them exactly as they appear in the document.
-   If an entity is not found in the document, set the entity value to null.
-   If there are multiple [ARRAY_FIELD_NAME], extract each as a separate object within the `[ARRAY_FIELD_NAME]` array.
[ADDITIONAL_INSTRUCTIONS]""")

with open(os.path.join(subdirectory, "prompt_template.txt"), "w") as f:
    f.write("""You are a document entity extraction specialist. Given a [DOCUMENT_TYPE], your task is to extract the text value of the following entities:

{
    [ENTITY_JSON_SCHEMA]
}

-   The JSON schema must be followed during the extraction.
-   The values must only include text found in the document.
-   Do not normalize any entity value (e.g., dates, addresses, etc.). Extract them exactly as they appear in the document.
-   If an entity is not found in the document, set the entity value to null.
-   If there are multiple [ARRAY_FIELD_NAME], extract each as a separate object within the `[ARRAY_FIELD_NAME]` array.
[ADDITIONAL_INSTRUCTIONS]""")