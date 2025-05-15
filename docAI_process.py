# Import the necessary libraries
from google.cloud import documentai

project_id = "invoiceprocessing-450716"
location = "us"  # e.g., 'us' or 'eu'
processor_id = "5486fff89ef396e2"  # The ID of your Document AI processor

# TODO: Replace with the path to your invoice/statement PDF file
file_path = "sample_invoices/1124132[90].pdf"

# TODO: Set the correct MIME type for your file
# Common MIME types: 'application/pdf', 'image/jpeg', 'image/png', 'image/tiff'
mime_type = "application/pdf"

# Optional: Set the GCE endpoint if not using the default (us or eu)
# opts = {"api_endpoint": f"{location}-documentai.googleapis.com"}
# client = documentai.DocumentProcessorServiceClient(client_options=opts)

# Instantiate the Document AI client
# Assumes GOOGLE_APPLICATION_CREDENTIALS environment variable is set
# See: https://cloud.google.com/docs/authentication/provide-credentials-adc#local-dev
client = documentai.DocumentProcessorServiceClient()

# The full resource name of the processor, e.g.:
# projects/project-id/locations/location/processors/processor-id
processor_name = client.processor_path(project_id, location, processor_id)

print(f"Processing document: {file_path}")
print(f"Using processor: {processor_name}")

# Read the file content
try:
    with open(file_path, "rb") as document_file:
        document_content = document_file.read()
except FileNotFoundError:
    print(f"Error: File not found at {file_path}")
    exit()

# Load Binary Data into Document AI RawDocument Object
raw_document = documentai.RawDocument(content=document_content, mime_type=mime_type)

# Configure the process request
# Note: Specific Processors may accept other options like field masks
# Refer to the documentation for the specific processor you are using
request = documentai.ProcessRequest(name=processor_name, raw_document=raw_document)

# Use the Document AI client to process the document
try:
    result = client.process_document(request=request)
    document = result.document
    print("Document processing complete.")
except Exception as e:
    print(f"Error processing document: {e}")
    exit()

# --- Parsing the Response ---

# Helper function to get text from text anchors (from Google examples)
def get_text(text_anchor: documentai.Document.TextAnchor, text: str) -> str:
    """Document AI identifies text in blocks, segments based on Protobuf."""
    response = ""
    # If a text segment spans several lines, it will
    # be stored in different text segments.
    for segment in text_anchor.text_segments:
        start_index = int(segment.start_index)
        end_index = int(segment.end_index)
        response += text[start_index:end_index]
    return response.strip().replace("\n", " ")


extracted_data = {}

# 1. Parse Entities (Common for specialized processors like Invoice Parser)
print("\n--- Entities ---")
if hasattr(document, 'entities') and document.entities:
    for entity in document.entities:
        entity_type = entity.type_
        # Use mention_text for the raw extracted value
        value = entity.mention_text
        # Some entities might have a normalized value (e.g., dates, amounts)
        normalized_value = entity.normalized_value.text if entity.normalized_value else None
        confidence = entity.confidence

        # Store the extracted data (you might want normalized value if available)
        extracted_data[entity_type] = value if normalized_value is None else normalized_value

        print(f"Type: {entity_type}, Value: {value}, Normalized: {normalized_value}, Confidence: {confidence:.2%}")
else:
    print("No entities found (typical for general OCR or Form Parser without specific entity training).")


# 2. Parse Form Fields (Common for Form Parser)
# This can be useful even if entities are present, or as a fallback
print("\n--- Form Fields ---")
has_form_fields = False
for page in document.pages:
    if page.form_fields:
        has_form_fields = True
        print(f"\nPage {page.page_number}:")
        for field in page.form_fields:
            field_name = get_text(field.field_name.text_anchor, document.text)
            field_value = get_text(field.field_value.text_anchor, document.text)
            name_confidence = field.field_name.confidence
            value_confidence = field.field_value.confidence

            # Store form field data (can overwrite entity data if desired, or store separately)
            # Use a simple key conversion for demonstration
            form_key = field_name.lower().replace(":", "").replace(" ", "_")
            if form_key not in extracted_data: # Avoid overwriting entity data unless intended
                extracted_data[form_key] = field_value

            print(f"  Field Name: '{field_name}' (Conf: {name_confidence:.2%})")
            print(f"  Field Value: '{field_value}' (Conf: {value_confidence:.2%})")

if not has_form_fields:
    print("No form fields found.")

# --- Use Extracted Data ---
# Now you have the 'extracted_data' dictionary containing values
# keyed by their entity type (e.g., 'invoice_id', 'total_amount')
# or derived from form field names (e.g., 'invoice_number', 'due_date').

print("\n--- Extracted Data Dictionary ---")
print(extracted_data)

# Example: Get specific values to use in your Vertex AI prompts
# Note: The exact keys ('invoice_id', 'total_amount', etc.) depend heavily
# on the specific Document AI processor you are using. Inspect the output above.
invoice_id_from_doc_ai = extracted_data.get('invoice_id') or extracted_data.get('invoice_#') or extracted_data.get('invoice_number')
total_amount_from_doc_ai = extracted_data.get('total_amount') or extracted_data.get('total') or extracted_data.get('amount_due')
due_date_from_doc_ai = extracted_data.get('due_date')
vendor_name_from_doc_ai = extracted_data.get('vendor_name')

print("\n--- Values for Verification Prompts ---")
print(f"Invoice ID: {invoice_id_from_doc_ai}")
print(f"Total Amount: {total_amount_from_doc_ai}")
print(f"Due Date: {due_date_from_doc_ai}")
print(f"Vendor Name: {vendor_name_from_doc_ai}")

# You would now pass these extracted values (e.g., invoice_id_from_doc_ai)
# into the placeholders of the Vertex AI verification prompts you created earlier.