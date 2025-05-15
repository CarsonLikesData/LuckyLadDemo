import base64
import vertexai
from vertexai.generative_models import GenerativeModel, SafetySetting, Part
from google.cloud import documentai
import os
import glob
import json
import csv
import re

# Document AI Processing Function
def get_text(text_anchor: documentai.Document.TextAnchor, text: str) -> str:
    response = ""
    for segment in text_anchor.text_segments:
        start_index = int(segment.start_index)
        end_index = int(segment.end_index)
        response += text[start_index:end_index]
    return response.strip().replace("\n", " ")

def process_document_ai(project_id: str, location: str, processor_id: str, file_path: str, mime_type: str):
    print(f"--- Starting Document AI Processing for: {os.path.basename(file_path)} ---")
    # Placeholder for actual Document AI call - assumes it returns:
    # extracted_data (dict), pdf_content_bytes (bytes), pdf_mime_type (str)
    # In a real scenario, this function contains the google.cloud.documentai client code
    # from the previous examples. For brevity here, we'll simulate its output structure slightly.

    # --- SIMULATION --- # Replace this block with actual DocAI call/parsing
    client = documentai.DocumentProcessorServiceClient()
    processor_name = client.processor_path(project_id, location, processor_id)
    try:
        with open(file_path, "rb") as document_file:
            document_content = document_file.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None, None, None
    raw_document = documentai.RawDocument(content=document_content, mime_type=mime_type)
    request = documentai.ProcessRequest(name=processor_name, raw_document=raw_document)
    try:
        result = client.process_document(request=request)
        document = result.document
    except Exception as e:
        print(f"Error processing document with Document AI ({os.path.basename(file_path)}): {e}")
        return None, document_content, mime_type # Return content even on error
    extracted_data = {}
    if hasattr(document, 'entities') and document.entities:
        for entity in document.entities:
            entity_type = entity.type_
            value = entity.mention_text
            normalized_value = entity.normalized_value.text if entity.normalized_value else None
            extracted_data[entity_type] = value if normalized_value is None else normalized_value
    # Add potential form field parsing as fallback
    for page in document.pages:
        if page.form_fields:
            for field in page.form_fields:
                field_name = get_text(field.field_name.text_anchor, document.text)
                field_value = get_text(field.field_value.text_anchor, document.text)
                # Use form field label as potential key if not already extracted as an entity
                form_key = field_name.lower().replace(":", "").replace(" ", "_").replace("%","pct") # Basic cleaning
                if form_key not in extracted_data and form_key: # Check if key is not empty
                     # Attempt to store based on common labels seen in examples
                     # This part requires knowing how DocAI parses YOUR specific forms
                     if "tank" in form_key and "size" in form_key:
                          extracted_data['tank_size'] = extracted_data.get('tank_size', []) + [field_value] # Collect multiple sizes?
                     elif "tank" in form_key and "before" in form_key:
                          extracted_data['tank_percentage_before'] = field_value
                     elif "tank" in form_key and "after" in form_key:
                          extracted_data['tank_percentage_after'] = field_value
                     elif form_key not in extracted_data: # Add other fields if not present
                         extracted_data[form_key] = field_value

    print(f"--- Finished Document AI Processing for: {os.path.basename(file_path)} ---")
    # --- END SIMULATION --- #
    return extracted_data, document_content, mime_type


# --- Vertex AI Response Parsing Function (unchanged) ---
def parse_vertex_response(response_text: str) -> dict:
    parsed_results = {}
    match_pattern = re.compile(r"^\s*\*?\s*(.+?)\s*:\s*Match\s*$", re.IGNORECASE | re.MULTILINE)
    not_found_pattern = re.compile(r"^\s*\*?\s*(.+?)\s*:\s*Not Found(?: in PDF)?\s*$", re.IGNORECASE | re.MULTILINE)
    mismatch_pattern = re.compile(r"^\s*\*?\s*(.+?)\s*:\s*Mismatch\s*-\s*PDF value is\s*\"(.*?)\"\s*$", re.IGNORECASE | re.MULTILINE)
    lines = response_text.splitlines()
    for line in lines:
        line = line.strip()
        if not line: continue
        m = match_pattern.match(line)
        if m:
            field_name = m.group(1).strip().replace("**", "")
            parsed_results[f"{field_name} Status"] = "Match"
            parsed_results[f"{field_name} PDF Value"] = ""
            continue
        m = not_found_pattern.match(line)
        if m:
            field_name = m.group(1).strip().replace("**", "")
            parsed_results[f"{field_name} Status"] = "Not Found"
            parsed_results[f"{field_name} PDF Value"] = ""
            continue
        m = mismatch_pattern.match(line)
        if m:
            field_name = m.group(1).strip().replace("**", "")
            pdf_value = m.group(2).strip()
            parsed_results[f"{field_name} Status"] = "Mismatch"
            parsed_results[f"{field_name} PDF Value"] = pdf_value
            continue
    return parsed_results

# --- Configuration ---
pdf_directory = "sample_invoices" # <--- SET THIS
doc_ai_project_id = "invoiceprocessing-450716"
doc_ai_location = "us"
doc_ai_processor_id = "5486fff89ef396e2"
doc_ai_mime_type = "application/pdf"
vertex_ai_project = "invoiceprocessing-450716"
vertex_ai_location = "us-central1"
json_output_file = "verification_results.json"
csv_output_file = "verification_results.csv"

# System Instruction (unchanged)
si_text1 = """You are an AI data validation specialist comparing Google Document AI output against a PDF.
For each field provided in the text prompt:
1. Locate the field in the attached PDF.
2. Compare the PDF value to the 'Document AI extracted' value from the text prompt.
3. Respond for EACH field using ONE of the following formats EXACTLY:
    * '[Field Name]: Match'
    * '[Field Name]: Mismatch - PDF value is "[Correct value from PDF]"'
    * '[Field Name]: Not Found in PDF'
Focus ONLY on visual verification in the PDF."""

# Generation Config (unchanged)
generation_config = { "max_output_tokens": 2048, "temperature": 0.1, "top_p": 0.95 }
# Safety Settings (unchanged)
safety_settings = [
    SafetySetting( category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
    SafetySetting( category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
    SafetySetting( category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
    SafetySetting( category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
]

def multiturn_generate_content():
    print("--- Initializing Vertex AI ---")
    vertexai.init(project=vertex_ai_project, location=vertex_ai_location)

    pdf_files = glob.glob(os.path.join(pdf_directory, '*.pdf')) + \
                glob.glob(os.path.join(pdf_directory, '*.PDF'))

    if not pdf_files: print(f"No PDF files found in directory: {pdf_directory}"); return
    print(f"Found {len(pdf_files)} PDF files to process.")

    all_results = []

    for current_file_path in pdf_files:
        file_basename = os.path.basename(current_file_path)
        print(f"\n=== Processing File: {file_basename} ===")

        extracted_data, pdf_content_bytes, pdf_mime_type = process_document_ai(
            project_id=doc_ai_project_id, location=doc_ai_location,
            processor_id=doc_ai_processor_id, file_path=current_file_path,
            mime_type=doc_ai_mime_type
        )

        if pdf_content_bytes is None:
            print(f"Skipping Vertex AI verification for {file_basename} due to previous error.")
            all_results.append({"filename": file_basename, "Error": "Failed to read or process file with Document AI"})
            continue
        if extracted_data is None:
            print(f"Warning: Document AI failed to extract data for {file_basename}. Proceeding.")
            extracted_data = {}

        # --- Prepare Dynamic Prompt based on Vendor ---
        vendor_name = str(extracted_data.get('vendor_name', '')).lower()
        dynamic_prompt_text = ""
        vendor_specific_fields_to_get = {} # Store specific fields requested for this vendor

        # Helper to safely get data
        def get_docai_value(key_list):
            # Special handling for potentially list-based fields like tank_size
            if 'tank_size' in key_list and isinstance(extracted_data.get('tank_size'), list):
                 return ", ".join(map(str, extracted_data.get('tank_size', [])))

            for key in key_list:
                value = extracted_data.get(key)
                if value is not None: return str(value)
            return "Not Extracted by DocAI"

        # Define generic keys
        invoice_id_keys = ['invoice_id', 'invoice_#', 'invoice_number']
        invoice_date_keys = ['invoice_date', 'date']
        due_date_keys = ['due_date']
        bill_to_name_keys = ['bill_to_name', 'customer_name', 'sold_to']
        ship_to_name_keys = ['ship_to_name']
        subtotal_keys = ['subtotal', 'sub_total']
        tax_keys = ['total_tax_amount', 'tax', 'sales_tax']
        total_amount_keys = ['total_amount', 'total', 'amount_due', 'balance_due', 'total_payment_due']

        # Base prompt part
        base_prompt = f"""Please verify the following fields extracted by Document AI against the attached PDF document ({file_basename}):

Generic Fields:
1.  **Invoice Number:** Document AI extracted = "{get_docai_value(invoice_id_keys)}"
2.  **Invoice Date:** Document AI extracted = "{get_docai_value(invoice_date_keys)}"
3.  **Due Date:** Document AI extracted = "{get_docai_value(due_date_keys)}"
4.  **Vendor Name:** Document AI extracted = "{extracted_data.get('vendor_name', 'Not Extracted by DocAI')}"
5.  **Bill To Name:** Document AI extracted = "{get_docai_value(bill_to_name_keys)}"
6.  **Ship To Name:** Document AI extracted = "{get_docai_value(ship_to_name_keys)}"
7.  **Subtotal:** Document AI extracted = "{get_docai_value(subtotal_keys)}"
8.  **Sales Tax:** Document AI extracted = "{get_docai_value(tax_keys)}"
9.  **Total Amount / Balance Due:** Document AI extracted = "{get_docai_value(total_amount_keys)}"
"""

        # --- Vendor Specific Logic ---
        if "atkinson" in vendor_name or "atkinson" in file_basename.lower():
            print("Applying ATKINSON PROPANE specific validation...")
            # Define specific keys for Atkinson Propane [cite: 3]
            # IMPORTANT: Adjust these keys based on actual Document AI output for this vendor
            tank_size_keys = ['tank_size'] # Might be extracted multiple times or need custom parsing
            tank_before_keys = ['tank_percentage_before', 'before']
            tank_after_keys = ['tank_percentage_after', 'after']
            gallons_keys = ['gallons']
            price_per_gal_keys = ['price_per_gal', 'price/gal']

            vendor_specific_fields_to_get = {
                 "Tank Size": tank_size_keys,
                 "Tank % Before": tank_before_keys,
                 "Tank % After": tank_after_keys,
                 "Gallons": gallons_keys,
                 "Price Per Gallon": price_per_gal_keys,
            }
            specific_prompt = "\nAtkinson Propane Specific Fields:\n"
            start_num = len(base_prompt.splitlines()) -1 # Continue numbering
            for i, (field_label, keys) in enumerate(vendor_specific_fields_to_get.items()):
                 specific_prompt += f"{start_num + i}.  **{field_label}:** Document AI extracted = \"{get_docai_value(keys)}\"\n"
            dynamic_prompt_text = base_prompt + specific_prompt

        elif "aegis" in vendor_name or "inv734477" in file_basename.lower():
             print("Applying AEGIS CHEMICAL specific validation...")
             # Define specific keys for Aegis Chemical [cite: 4]
             customer_id_keys = ['customer_id']
             lease_name_keys = ['lease_name']
             area_keys = ['area']
             service_date_keys = ['service_date']
             # Line items might need separate, more complex handling TBD
             vendor_specific_fields_to_get = {
                  "Customer ID": customer_id_keys,
                  "Lease Name": lease_name_keys,
                  "Area": area_keys,
                  "Service Date": service_date_keys,
             }
             specific_prompt = "\nAegis Chemical Specific Fields:\n"
             start_num = len(base_prompt.splitlines()) - 1
             for i, (field_label, keys) in enumerate(vendor_specific_fields_to_get.items()):
                 specific_prompt += f"{start_num + i}.  **{field_label}:** Document AI extracted = \"{get_docai_value(keys)}\"\n"
             dynamic_prompt_text = base_prompt + specific_prompt

        elif "chem-ray" in vendor_name or "1124132" in file_basename:
             print("Applying CHEM-RAY specific validation...")
             # Define specific keys for Chem-Ray [cite: 1]
             unit_no_keys = ['unit_no']
             terms_keys = ['terms']
             vendor_specific_fields_to_get = {
                  "Unit No.": unit_no_keys,
                  "Terms": terms_keys,
             }
             specific_prompt = "\nChem-Ray Specific Fields:\n"
             start_num = len(base_prompt.splitlines()) -1
             for i, (field_label, keys) in enumerate(vendor_specific_fields_to_get.items()):
                  specific_prompt += f"{start_num + i}.  **{field_label}:** Document AI extracted = \"{get_docai_value(keys)}\"\n"
             dynamic_prompt_text = base_prompt + specific_prompt

        elif "production hookup" in vendor_name or "20240701_112438" in file_basename:
             print("Applying PRODUCTION HOOKUP specific validation...")
             # Define specific keys for Production Hookup [cite: 2]
             field_loc_keys = ['field'] # Example 'Godchaux #3'
             ordered_by_keys = ["ord'd_by", 'ordered_by']
             # Labor/Materials might need complex handling
             vendor_specific_fields_to_get = {
                  "Field Location": field_loc_keys,
                  "Ordered By": ordered_by_keys,
             }
             specific_prompt = "\nProduction Hookup Specific Fields:\n"
             start_num = len(base_prompt.splitlines()) - 1
             for i, (field_label, keys) in enumerate(vendor_specific_fields_to_get.items()):
                 specific_prompt += f"{start_num + i}.  **{field_label}:** Document AI extracted = \"{get_docai_value(keys)}\"\n"
             dynamic_prompt_text = base_prompt + specific_prompt

        elif "reagan power" in vendor_name or "reagan_power" in file_basename.lower():
             print("Applying REAGAN POWER (Statement) specific validation...")
             # Define specific keys for Reagan Power Statement [cite: 5]
             statement_date_keys = ['statement_date', 'date'] # Check if 'date' is statement date
             current_due_keys = ['current']
             over_90_days_keys = ['over_90_days_past_due']
             total_due_aging_keys = ['amount_due'] # From aging table
             vendor_specific_fields_to_get = {
                  "Statement Date": statement_date_keys,
                  "Current Due (Aging)": current_due_keys,
                  "Over 90 Days Due (Aging)": over_90_days_keys,
                  "Total Due (Aging)": total_due_aging_keys,
             }
             specific_prompt = "\nReagan Power Statement Specific Fields:\n"
             # Use a simpler base for statements? Or just add specific fields? Adding for now.
             start_num = len(base_prompt.splitlines()) - 1 # Continue numbering from generic base
             for i, (field_label, keys) in enumerate(vendor_specific_fields_to_get.items()):
                 specific_prompt += f"{start_num + i}.  **{field_label}:** Document AI extracted = \"{get_docai_value(keys)}\"\n"
             dynamic_prompt_text = base_prompt + specific_prompt # Add specific fields to generic ones

        else:
            print("Applying GENERIC validation prompt.")
            dynamic_prompt_text = base_prompt + "\nNo vendor-specific fields requested for this document."

        # --- Step 3: Prepare PDF Part ---
        try:
            pdf_part = Part.from_data(data=pdf_content_bytes, mime_type=pdf_mime_type)
        except Exception as e:
            print(f"Error creating PDF Part for Vertex AI ({file_basename}): {e}")
            all_results.append({"filename": file_basename, "Error": f"Failed to create PDF Part: {e}"})
            continue

        # --- Step 4: Call Vertex AI ---
        try:
            model = GenerativeModel("gemini-1.5-pro-preview-0514", system_instruction=[si_text1])
            chat = model.start_chat()
            response = chat.send_message(
                [dynamic_prompt_text, pdf_part],
                generation_config=generation_config, safety_settings=safety_settings,
            )

            print(f"--- Vertex AI Verification Result for: {file_basename} ---")
            response_text = ""
            if response.candidates and response.candidates[0].content.parts:
                 response_text = response.candidates[0].content.parts[0].text
                 print(response_text)
            else:
                 print("Vertex AI returned an empty or unexpected response format.")
                 all_results.append({"filename": file_basename, "Error": "Vertex AI returned empty response", "Prompt": dynamic_prompt_text})
                 continue

            # --- Step 5: Parse Vertex AI Response and Store ---
            parsed_verification = parse_vertex_response(response_text)

            # Build the result dictionary, including generic AND specific fields requested
            file_result_data = { "filename": file_basename }
            # Add generic DocAI values
            file_result_data["Invoice Number DocAI"] = get_docai_value(invoice_id_keys)
            file_result_data["Invoice Date DocAI"] = get_docai_value(invoice_date_keys)
            file_result_data["Due Date DocAI"] = get_docai_value(due_date_keys)
            file_result_data["Vendor Name DocAI"] = extracted_data.get('vendor_name', 'Not Extracted by DocAI')
            file_result_data["Bill To Name DocAI"] = get_docai_value(bill_to_name_keys)
            file_result_data["Ship To Name DocAI"] = get_docai_value(ship_to_name_keys)
            file_result_data["Subtotal DocAI"] = get_docai_value(subtotal_keys)
            file_result_data["Sales Tax DocAI"] = get_docai_value(tax_keys)
            file_result_data["Total/Balance DocAI"] = get_docai_value(total_amount_keys)

            # Add specific DocAI values IF they were requested for this vendor
            for field_label, keys in vendor_specific_fields_to_get.items():
                 file_result_data[f"{field_label} DocAI"] = get_docai_value(keys)

            # Add the parsed verification statuses/PDF values
            file_result_data.update(parsed_verification)

            all_results.append(file_result_data)
            print("--- Parsed and Stored Verification ---")

        except Exception as e:
            print(f"Error calling Vertex AI or parsing response for {file_basename}: {e}")
            all_results.append({"filename": file_basename, "Error": f"Vertex AI call or parsing failed: {e}", "Prompt": dynamic_prompt_text})

    # --- Step 6: Write Aggregated Results ---
    print("\n=== Finished processing all PDF files ===")
    if not all_results: print("No results generated."); return

    # Write JSON
    try:
        print(f"Writing results to {json_output_file}...")
        with open(json_output_file, 'w', encoding='utf-8') as f_json:
            json.dump(all_results, f_json, indent=4, ensure_ascii=False)
        print("JSON output complete.")
    except Exception as e: print(f"Error writing JSON file: {e}")

    # Write CSV
    try:
        print(f"Writing results to {csv_output_file}...")
        # Gather all possible headers from all results (including specific fields)
        all_headers = set()
        for result in all_results:
            all_headers.update(result.keys())
        # Define a preferred order if possible, placing filename first, errors last
        ordered_headers = sorted(list(all_headers), key=lambda x: (x != 'filename', x == 'Error', x))

        if ordered_headers:
             with open(csv_output_file, 'w', newline='', encoding='utf-8') as f_csv:
                 writer = csv.DictWriter(f_csv, fieldnames=ordered_headers, extrasaction='ignore') # ignore fields not in headers
                 writer.writeheader()
                 writer.writerows(all_results)
             print("CSV output complete.")
        else: print("Could not determine headers for CSV file.")
    except Exception as e: print(f"Error writing CSV file: {e}")


# --- Run Script ---
if __name__ == "__main__":
    if not os.path.isdir(pdf_directory):
        print(f"Error: Specified PDF directory does not exist: {pdf_directory}")
    else:
        multiturn_generate_content()