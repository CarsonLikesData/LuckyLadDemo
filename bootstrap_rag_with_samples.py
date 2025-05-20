"""
Bootstrap RAG Engine with Sample Invoices

This script loads the sample invoices and their processed data into the RAG engine
to establish an initial reference before processing new invoices.
"""

import os
import json
from typing import Dict, Any, List, Tuple
import logging
from rag_engine import get_rag_engine
from lucky_lad_invoice_processor import process_document_from_memory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bootstrap_rag")

# Directories
SAMPLE_INVOICES_DIR = "sample_invoices"
PROCESSED_DATA_DIR = "SI_and_prompt_templates"

def load_pdf_content(pdf_path: str) -> bytes:
    """Load PDF file content as bytes."""
    try:
        with open(pdf_path, 'rb') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading PDF file {pdf_path}: {e}")
        return None

def load_processed_data(json_path: str) -> Dict[str, Any]:
    """Load processed invoice data from JSON file."""
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading JSON file {json_path}: {e}")
        return {}

def find_matching_json(pdf_filename: str) -> str:
    """Find the matching JSON file for a given PDF filename."""
    # Extract base name without extension
    base_name = os.path.splitext(os.path.basename(pdf_filename))[0]
    
    # Handle special cases with brackets or other characters
    if '[' in base_name:
        base_name = base_name.split('[')[0]
    
    # Check for exact match first
    exact_match = os.path.join(PROCESSED_DATA_DIR, f"{base_name}.json")
    if os.path.exists(exact_match):
        return exact_match
    
    # Check for case-insensitive match
    for json_file in os.listdir(PROCESSED_DATA_DIR):
        if json_file.lower().endswith('.json'):
            json_base = os.path.splitext(json_file)[0].lower()
            if base_name.lower() in json_base or json_base in base_name.lower():
                return os.path.join(PROCESSED_DATA_DIR, json_file)
    
    # Special case mappings
    special_mappings = {
        "ATKINSON PROPANE CO. INC": "atkinson",
        "Statement1_from_REAGAN_POWER_COMPRESSION_LLC15308": "statement"
    }
    
    for pattern, json_prefix in special_mappings.items():
        if pattern.lower() in base_name.lower():
            json_path = os.path.join(PROCESSED_DATA_DIR, f"{json_prefix}.json")
            if os.path.exists(json_path):
                return json_path
    
    return None

def extract_document_text_and_entities(pdf_content: bytes) -> Tuple[str, Dict[str, str]]:
    """
    Extract text and entities from PDF using Document AI.
    
    Args:
        pdf_content: The binary content of the PDF file
        
    Returns:
        Tuple containing:
        - document_text: The extracted text from the PDF
        - doc_entities: The entities extracted by Document AI
    """
    try:
        # Google Cloud Document AI configuration
        PROJECT_ID = "invoiceprocessing-450716"
        LOCATION = "us"
        PROCESSOR_ID = "5486fff89ef396e2"
        PROCESSOR_VERSION_ID = "57f4f1dda43d5c50"
        MIME_TYPE = "application/pdf"
        FIELD_MASK = "text,entities,pages.pageNumber"
        
        # Process the document using Document AI
        document = process_document_from_memory(
            image_content=pdf_content,
            mime_type=MIME_TYPE,
            project_id=PROJECT_ID,
            location=LOCATION,
            processor_id=PROCESSOR_ID,
            field_mask=FIELD_MASK,
            processor_version_id=PROCESSOR_VERSION_ID,
        )
        
        # Extract text and entities
        document_text = document.text
        
        # Convert Document AI entities to dictionary
        doc_entities = {}
        for entity in document.entities:
            doc_entities[entity.type_] = entity.mention_text
        
        return document_text, doc_entities
    except Exception as e:
        logger.error(f"Error extracting text with Document AI: {e}")
        return "", {}

def convert_json_to_entities(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert the JSON data to a format compatible with the RAG engine."""
    entities = {}
    
    # Add top-level fields
    for key, value in json_data.items():
        if isinstance(value, (str, int, float)) and value is not None:
            entities[key] = str(value)
    
    # Handle nested objects
    if "bill_to" in json_data and isinstance(json_data["bill_to"], dict):
        # Add full bill_to as a single entity for better context
        bill_to_parts = []
        for key, value in json_data["bill_to"].items():
            if value:
                entities[f"bill_to_{key}"] = str(value)
                bill_to_parts.append(f"{key}: {value}")
        
        if bill_to_parts:
            entities["bill_to"] = "\n".join(bill_to_parts)
    
    if "ship_to" in json_data and isinstance(json_data["ship_to"], dict):
        # Add full ship_to as a single entity for better context
        ship_to_parts = []
        for key, value in json_data["ship_to"].items():
            if value:
                entities[f"ship_to_{key}"] = str(value)
                ship_to_parts.append(f"{key}: {value}")
        
        if ship_to_parts:
            entities["ship_to"] = "\n".join(ship_to_parts)
    
    # Handle line items
    if "line_items" in json_data and isinstance(json_data["line_items"], list):
        # Create a consolidated line_items entity for better context
        line_items_text = []
        
        for i, item in enumerate(json_data["line_items"], 1):
            # Add individual line item fields
            for key, value in item.items():
                if value:
                    entities[f"line_item_{i}_{key}"] = str(value)
            
            # Add well names to a special field for easier retrieval
            if "well_name" in item and item["well_name"]:
                well_name = item["well_name"]
                if "well_names" not in entities:
                    entities["well_names"] = well_name
                elif well_name not in entities["well_names"]:
                    entities["well_names"] += f", {well_name}"
            
            # Create a text representation of this line item
            line_item_parts = [f"Line Item {i}:"]
            for key, value in item.items():
                if value:
                    line_item_parts.append(f"  {key}: {value}")
            
            line_items_text.append("\n".join(line_item_parts))
        
        # Add consolidated line items
        if line_items_text:
            entities["line_items_text"] = "\n\n".join(line_items_text)
    
    # Add special fields for RAG retrieval
    
    # Vendor name (from bill_to or directly)
    if "vendor_name" not in entities:
        if "bill_to" in json_data and isinstance(json_data["bill_to"], dict):
            if "customer_name" in json_data["bill_to"]:
                entities["vendor_name"] = json_data["bill_to"]["customer_name"]
    
    # Well name (from lease_name, well_name, or line items)
    if "well_name" not in entities or not entities["well_name"]:
        if "lease_name" in json_data and json_data["lease_name"]:
            entities["well_name"] = json_data["lease_name"]
        elif "well_names" in entities:
            entities["well_name"] = entities["well_names"].split(",")[0].strip()
    
    # Create a summary field for better retrieval
    summary_parts = []
    
    if "invoice_number" in entities:
        summary_parts.append(f"Invoice: {entities['invoice_number']}")
    
    if "vendor_name" in entities:
        summary_parts.append(f"Vendor: {entities['vendor_name']}")
    
    if "well_name" in entities and entities["well_name"]:
        summary_parts.append(f"Well: {entities['well_name']}")
    
    if "total" in entities:
        summary_parts.append(f"Total: {entities['total']}")
    
    if summary_parts:
        entities["summary"] = " | ".join(summary_parts)
    
    return entities

def get_sample_invoices() -> List[Tuple[str, str]]:
    """Get list of sample invoice PDFs and their matching JSON files."""
    sample_pairs = []
    
    for filename in os.listdir(SAMPLE_INVOICES_DIR):
        if filename.lower().endswith(('.pdf', '.PDF')):
            pdf_path = os.path.join(SAMPLE_INVOICES_DIR, filename)
            json_path = find_matching_json(filename)
            
            if json_path:
                sample_pairs.append((pdf_path, json_path))
            else:
                logger.warning(f"No matching JSON found for {filename}")
    
    return sample_pairs

def bootstrap_rag_engine():
    """Main function to bootstrap the RAG engine with sample invoices."""
    logger.info("Starting RAG engine bootstrap with sample invoices")
    
    # Get the RAG engine instance
    rag_engine = get_rag_engine()
    
    # Get sample invoice pairs (PDF + JSON)
    sample_pairs = get_sample_invoices()
    logger.info(f"Found {len(sample_pairs)} sample invoice pairs")
    
    # Process each sample
    for pdf_path, json_path in sample_pairs:
        pdf_filename = os.path.basename(pdf_path)
        logger.info(f"Processing sample invoice: {pdf_filename}")
        
        # Load PDF content
        pdf_content = load_pdf_content(pdf_path)
        if not pdf_content:
            logger.error(f"Failed to load PDF content for {pdf_filename}")
            continue
        
        # Load processed data
        json_data = load_processed_data(json_path)
        if not json_data:
            logger.error(f"Failed to load JSON data for {pdf_filename}")
            continue
        
        # Extract document text and entities using Document AI
        document_text, doc_entities = extract_document_text_and_entities(pdf_content)
        
        if not document_text:
            logger.warning(f"Document AI extraction failed for {pdf_filename}, using JSON data only")
            document_text = f"Invoice {json_data.get('invoice_number', 'Unknown')} from {json_data.get('bill_to', {}).get('customer_name', 'Unknown Customer')}"
        
        # Combine Document AI entities with our processed JSON data
        # The JSON data is more structured and accurate, but Document AI gives us the raw text
        entities = convert_json_to_entities(json_data)
        
        # Add Document AI entities as a fallback for any missing fields
        for key, value in doc_entities.items():
            if key not in entities:
                entities[key] = value
        
        # Add to RAG engine
        metadata = {
            "filename": pdf_filename,
            "source": "sample_invoice",
            "processed_date": "2024-05-16"  # Current date as a placeholder
        }
        
        success = rag_engine.add_invoice(document_text, entities, metadata)
        
        if success:
            logger.info(f"Successfully added {pdf_filename} to RAG engine")
        else:
            logger.error(f"Failed to add {pdf_filename} to RAG engine")
    
    logger.info("RAG engine bootstrap completed")
    
    # Get the count of invoices in the vector database
    invoice_count = len(rag_engine.metadata)
    logger.info(f"RAG engine now contains {invoice_count} invoices")
    
    # Test retrieval to verify the bootstrap worked
    if invoice_count > 0:
        logger.info("Testing retrieval with a sample query...")
        # Create a simple test query using one of the invoices
        if sample_pairs:
            test_pdf_path, test_json_path = sample_pairs[0]
            test_json_data = load_processed_data(test_json_path)
            
            if test_json_data:
                # Create a simple query from the invoice data
                query_text = f"Invoice from {test_json_data.get('bill_to', {}).get('customer_name', 'Unknown')}"
                query_entities = {
                    "invoice_number": test_json_data.get("invoice_number", ""),
                    "vendor_name": test_json_data.get("bill_to", {}).get("customer_name", "")
                }
                
                # Retrieve similar invoices
                similar_invoices = rag_engine.retrieve_similar_invoices(query_text, query_entities)
                
                logger.info(f"Retrieved {len(similar_invoices)} similar invoices for test query")
                for i, invoice in enumerate(similar_invoices):
                    metadata = invoice.get("metadata", {})
                    logger.info(f"  Similar invoice {i+1}: {metadata.get('filename', 'Unknown')}")

if __name__ == "__main__":
    bootstrap_rag_engine()