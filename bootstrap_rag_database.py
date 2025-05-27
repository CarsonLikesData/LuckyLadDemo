"""
Bootstrap RAG Database for Lucky Lad Invoice Processor
-----------------------------------------------------
This script populates the RAG database with sample invoices from the
sample_invoices directory. This helps the system get started with a
pre-populated database, which is important for effective RAG operation.
"""

import os
import json
import argparse
from datetime import datetime

# Import from main processor
from lucky_lad_invoice_processor import (
    process_document_from_memory,
    MIME_TYPE,
    PROJECT_ID,
    LOCATION,
    PROCESSOR_ID,
    FIELD_MASK,
    PROCESSOR_VERSION_ID,
)

# Import RAG engine
from rag_engine import get_rag_engine

# Default sample invoices directory
SAMPLE_INVOICES_DIR = "sample_invoices"


def load_sample_invoice(file_path):
    """Load a sample invoice PDF file"""
    try:
        with open(file_path, "rb") as f:
            return f.read()
    except Exception as e:
        print(f"Error loading sample invoice {file_path}: {e}")
        return None


def process_sample_invoice(file_path):
    """Process a sample invoice and return extracted data"""
    try:
        # Load PDF content
        pdf_content = load_sample_invoice(file_path)
        if not pdf_content:
            return None

        # Process with Document AI
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

        return {
            "text": text,
            "entities": extracted_entities,
            "pdf_content": pdf_content,
        }
    except Exception as e:
        print(f"Error processing sample invoice {file_path}: {e}")
        return None


def add_to_rag_database(file_path, extracted_data):
    """Add a processed invoice to the RAG database"""
    try:
        # Get RAG engine
        rag = get_rag_engine()

        # Prepare metadata
        filename = os.path.basename(file_path)
        metadata = {
            "filename": filename,
            "processing_time": datetime.now().isoformat(),
            "source": "bootstrap",
            "file_path": file_path,
        }

        # Add to RAG database
        success = rag.add_invoice(
            extracted_data["text"], extracted_data["entities"], metadata
        )

        return success
    except Exception as e:
        print(f"Error adding invoice to RAG database: {e}")
        return False


def load_json_metadata(file_path):
    """Load JSON metadata for a sample invoice if available"""
    try:
        # Check if there's a corresponding JSON file
        base_name = os.path.splitext(file_path)[0]
        json_path = f"{base_name}.json"

        if os.path.exists(json_path):
            with open(json_path, "r") as f:
                return json.load(f)

        # Also check in SI_and_prompt_templates directory
        templates_dir = "SI_and_prompt_templates"
        base_filename = os.path.basename(base_name)
        alt_json_path = os.path.join(templates_dir, f"{base_filename}.json")

        if os.path.exists(alt_json_path):
            with open(alt_json_path, "r") as f:
                return json.load(f)

        return None
    except Exception as e:
        print(f"Error loading JSON metadata for {file_path}: {e}")
        return None


def bootstrap_database(sample_dir, force=False):
    """Bootstrap the RAG database with sample invoices"""
    # Get RAG engine
    rag = get_rag_engine()

    # Check if database already has invoices
    if len(rag.metadata) > 0 and not force:
        print(f"RAG database already contains {len(rag.metadata)} invoices.")
        print("Use --force to overwrite existing database.")
        return

    # If force is True, clear the database
    if force and len(rag.metadata) > 0:
        print(f"Clearing existing RAG database with {len(rag.metadata)} invoices...")
        rag.index = rag.index.reset()
        rag.metadata = []
        rag.embeddings = []
        rag._save_index()
        print("RAG database cleared.")

    # Get list of PDF files in sample directory
    pdf_files = []
    for root, _, files in os.walk(sample_dir):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, file))

    if not pdf_files:
        print(f"No PDF files found in {sample_dir}")
        return

    print(f"Found {len(pdf_files)} sample invoices.")

    # Process each sample invoice
    successful = 0
    for i, file_path in enumerate(pdf_files, 1):
        print(f"\nProcessing {i}/{len(pdf_files)}: {os.path.basename(file_path)}")

        # Check if there's JSON metadata
        json_metadata = load_json_metadata(file_path)

        if json_metadata:
            print(f"Found JSON metadata for {os.path.basename(file_path)}")

            # Extract text and entities from JSON
            text = json_metadata.get("text", "")
            entities = json_metadata.get("entities", {})

            # If text is missing, process the PDF to get it
            if not text:
                extracted_data = process_sample_invoice(file_path)
                if extracted_data:
                    text = extracted_data["text"]

            # Add to RAG database
            metadata = {
                "filename": os.path.basename(file_path),
                "processing_time": datetime.now().isoformat(),
                "source": "bootstrap_json",
                "file_path": file_path,
            }

            success = rag.add_invoice(text, entities, metadata)

            if success:
                print(
                    f"Successfully added {os.path.basename(file_path)} to RAG database (from JSON)."
                )
                successful += 1
            else:
                print(
                    f"Failed to add {os.path.basename(file_path)} to RAG database (from JSON)."
                )
        else:
            # Process the PDF
            extracted_data = process_sample_invoice(file_path)

            if extracted_data:
                # Add to RAG database
                success = add_to_rag_database(file_path, extracted_data)

                if success:
                    print(
                        f"Successfully added {os.path.basename(file_path)} to RAG database."
                    )
                    successful += 1
                else:
                    print(
                        f"Failed to add {os.path.basename(file_path)} to RAG database."
                    )

    print(
        f"\nBootstrap complete. Added {successful}/{len(pdf_files)} invoices to RAG database."
    )


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Bootstrap RAG database with sample invoices"
    )
    parser.add_argument(
        "--dir",
        default=SAMPLE_INVOICES_DIR,
        help=f"Directory containing sample invoices (default: {SAMPLE_INVOICES_DIR})",
    )
    parser.add_argument(
        "--force", action="store_true", help="Force overwrite of existing database"
    )

    args = parser.parse_args()

    # Check if directory exists
    if not os.path.exists(args.dir):
        print(f"Error: Directory {args.dir} does not exist.")
        return

    # Bootstrap database
    bootstrap_database(args.dir, args.force)


if __name__ == "__main__":
    main()
