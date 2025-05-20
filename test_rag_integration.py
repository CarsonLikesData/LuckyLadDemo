"""
Test RAG Integration for Lucky Lad Invoice Processor
---------------------------------------------------
This script demonstrates how to use the RAG engine with a sample invoice.
It shows how the system detects new invoice types and how it uses context
from similar invoices to improve extraction accuracy.
"""

import os
import json
import argparse
from datetime import datetime

# Import from main processor
from lucky_lad_invoice_processor import (
    process_document_from_memory,
    generate_content_with_vertex_ai,
    process_vertex_response,
    MIME_TYPE,
    PROJECT_ID,
    LOCATION,
    PROCESSOR_ID,
    FIELD_MASK,
    PROCESSOR_VERSION_ID
)

# Import RAG engine
from rag_engine import get_rag_engine

def load_sample_invoice(file_path):
    """Load a sample invoice PDF file"""
    try:
        with open(file_path, 'rb') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading sample invoice {file_path}: {e}")
        return None

def process_invoice(pdf_content, filename):
    """Process an invoice using Document AI and Vertex AI with RAG"""
    print(f"\n=== Processing invoice: {filename} ===")
    
    # Step 1: Process with Document AI
    print("\nStep 1: Processing with Document AI...")
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
    text = document.text
    entities = document.entities
    
    # Convert entities to dictionary
    extracted_entities = {}
    for entity in entities:
        extracted_entities[entity.type_] = entity.mention_text
    
    # Create document data for Vertex AI
    document_data = {
        "text": text,
        "entities": [
            {"type_": e.type_, "mention_text": e.mention_text}
            for e in entities
        ],
    }
    
    # Print extracted entities
    print("\nExtracted entities:")
    for entity_type, mention_text in extracted_entities.items():
        print(f"  {entity_type}: {mention_text}")
    
    # Step 2: Check RAG database for similar invoices
    print("\nStep 2: Checking RAG database for similar invoices...")
    rag = get_rag_engine()
    similar_invoices = rag.retrieve_similar_invoices(text, extracted_entities)
    
    if similar_invoices:
        print(f"Found {len(similar_invoices)} similar invoices in RAG database:")
        for i, invoice in enumerate(similar_invoices, 1):
            metadata = invoice.get("metadata", {})
            print(f"  {i}. {metadata.get('filename', 'Unknown')}")
    else:
        print("No similar invoices found in RAG database.")
        print("This appears to be a new invoice type.")
    
    # Step 3: Process with Vertex AI
    print("\nStep 3: Processing with Vertex AI...")
    document_json_string = json.dumps(document_data)
    vertex_ai_response = generate_content_with_vertex_ai(document_json_string, filename)
    
    if vertex_ai_response:
        print("\nVertex AI response received.")
        
        # Step 4: Process the response
        print("\nStep 4: Processing Vertex AI response...")
        processed_data = process_vertex_response(vertex_ai_response)
        
        # Print processed data
        print("\nProcessed data:")
        for section, data in processed_data.items():
            if isinstance(data, dict):
                print(f"\n{section}:")
                for key, value in data.items():
                    print(f"  {key}: {value}")
            elif isinstance(data, list):
                print(f"\n{section} ({len(data)} items):")
                for i, item in enumerate(data, 1):
                    print(f"  Item {i}:")
                    for key, value in item.items():
                        print(f"    {key}: {value}")
        
        # Step 5: Add to RAG database
        print("\nStep 5: Adding to RAG database...")
        metadata = {
            "filename": filename,
            "processing_time": datetime.now().isoformat(),
            "test_run": True
        }
        success = rag.add_invoice(text, extracted_entities, metadata)
        
        if success:
            print("Successfully added invoice to RAG database.")
        else:
            print("Failed to add invoice to RAG database.")
        
        return processed_data
    else:
        print("Vertex AI processing failed.")
        return None

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Test RAG integration with a sample invoice")
    parser.add_argument("--file", required=True, help="Path to sample invoice PDF file")
    
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.exists(args.file):
        print(f"Error: File {args.file} does not exist.")
        return
    
    # Get filename
    filename = os.path.basename(args.file)
    
    # Load sample invoice
    pdf_content = load_sample_invoice(args.file)
    if not pdf_content:
        return
    
    # Process invoice
    processed_data = process_invoice(pdf_content, filename)
    
    if processed_data:
        print("\n=== Processing complete ===")
        print(f"Invoice {filename} processed successfully.")
    else:
        print("\n=== Processing failed ===")
        print(f"Failed to process invoice {filename}.")

if __name__ == "__main__":
    main()