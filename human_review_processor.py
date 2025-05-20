"""
Human Review Processor for Lucky Lad Invoice System
--------------------------------------------------
This utility script processes invoices that have been flagged for human review,
allows for corrections to be made, and submits the corrected data to Document AI
for retraining to improve future extraction accuracy.
"""

import os
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd

# Import from main processor
from lucky_lad_invoice_processor import (
    add_to_document_ai_dataset,
    REVIEW_DIR,
    PROJECT_ID,
    LOCATION,
    PROCESSOR_ID
)

# Import RAG engine
from rag_engine import get_rag_engine

# Document AI dataset ID for retraining
# This would be created in the Google Cloud Console
DOCUMENT_AI_DATASET_ID = "your_dataset_id_here"

def list_pending_reviews():
    """List all pending review files"""
    if not os.path.exists(REVIEW_DIR):
        print(f"Review directory {REVIEW_DIR} does not exist.")
        return []
    
    review_files = []
    for filename in os.listdir(REVIEW_DIR):
        if filename.endswith(".json"):
            file_path = os.path.join(REVIEW_DIR, filename)
            try:
                with open(file_path, 'r') as f:
                    review_data = json.load(f)
                    if review_data.get("status") == "pending_review":
                        review_files.append({
                            "filename": filename,
                            "path": file_path,
                            "timestamp": review_data.get("timestamp"),
                            "reason": review_data.get("reason"),
                            "invoice_filename": review_data.get("invoice_data", {}).get("filename", "Unknown")
                        })
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
    
    return review_files

def display_review_list(review_files):
    """Display a list of pending reviews"""
    if not review_files:
        print("No pending reviews found.")
        return
    
    print(f"\nFound {len(review_files)} pending reviews:")
    print("-" * 80)
    for i, review in enumerate(review_files, 1):
        print(f"{i}. {review['invoice_filename']} - {review['reason']}")
        print(f"   Flagged at: {review['timestamp']}")
        print(f"   File: {review['filename']}")
        print("-" * 80)

def load_review_file(file_path):
    """Load a review file and return its contents"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading review file {file_path}: {e}")
        return None

def display_invoice_data(invoice_data):
    """Display the invoice data for review"""
    print("\n=== Invoice Data ===")
    print(f"Filename: {invoice_data.get('filename', 'Unknown')}")
    
    # Display extracted entities
    entities = invoice_data.get("entities", {})
    if entities:
        print("\nExtracted Entities:")
        for key, value in entities.items():
            print(f"  {key}: {value}")
    
    # Display first 500 characters of document text
    document_text = invoice_data.get("document_text", "")
    if document_text:
        print("\nDocument Text (first 500 chars):")
        print(document_text[:500] + "..." if len(document_text) > 500 else document_text)

def process_corrections(review_data, corrections):
    """Process user corrections and update the review file"""
    invoice_data = review_data.get("invoice_data", {})
    entities = invoice_data.get("entities", {})
    
    # Update entities with corrections
    for field, value in corrections.items():
        entities[field] = value
    
    # Update the invoice data
    invoice_data["entities"] = entities
    review_data["invoice_data"] = invoice_data
    
    # Mark as reviewed
    review_data["status"] = "reviewed"
    review_data["review_timestamp"] = datetime.now().isoformat()
    review_data["corrections"] = corrections
    
    return review_data

def save_review_file(file_path, review_data):
    """Save the updated review file"""
    try:
        with open(file_path, 'w') as f:
            json.dump(review_data, f, indent=2)
        print(f"Saved corrections to {file_path}")
        return True
    except Exception as e:
        print(f"Error saving review file {file_path}: {e}")
        return False

def update_rag_database(review_data):
    """Update the RAG database with the corrected invoice data"""
    try:
        invoice_data = review_data.get("invoice_data", {})
        document_text = invoice_data.get("document_text", "")
        entities = invoice_data.get("entities", {})
        metadata = {
            "filename": invoice_data.get("filename", "unknown"),
            "review_timestamp": review_data.get("review_timestamp"),
            "is_corrected": True
        }
        
        rag = get_rag_engine()
        success = rag.add_invoice(document_text, entities, metadata)
        
        if success:
            print("Successfully added corrected invoice to RAG database")
        else:
            print("Failed to add corrected invoice to RAG database")
        
        return success
    except Exception as e:
        print(f"Error updating RAG database: {e}")
        return False

def submit_to_document_ai(review_data):
    """Submit the corrected document to Document AI for retraining"""
    try:
        invoice_data = review_data.get("invoice_data", {})
        document_content = invoice_data.get("pdf_content", "")
        
        if not document_content:
            print("Error: PDF content not available in review data")
            return False
        
        # Convert entities to Document AI format
        entities = invoice_data.get("entities", {})
        ground_truth_entities = []
        
        for entity_type, mention_text in entities.items():
            # This is a simplified conversion - actual implementation would be more complex
            ground_truth_entity = {
                "type": entity_type,
                "mention_text": mention_text,
                # Additional fields like text_segments would be needed in a real implementation
            }
            ground_truth_entities.append(ground_truth_entity)
        
        # Submit to Document AI
        response = add_to_document_ai_dataset(
            PROJECT_ID,
            LOCATION,
            PROCESSOR_ID,
            DOCUMENT_AI_DATASET_ID,
            document_content,
            ground_truth_entities
        )
        
        if response:
            print("Successfully submitted corrected document to Document AI for retraining")
            return True
        else:
            print("Failed to submit document to Document AI")
            return False
    except Exception as e:
        print(f"Error submitting to Document AI: {e}")
        return False

def interactive_review():
    """Run an interactive review session"""
    review_files = list_pending_reviews()
    display_review_list(review_files)
    
    if not review_files:
        return
    
    while True:
        try:
            choice = input("\nEnter the number of the review to process (or 'q' to quit): ")
            if choice.lower() == 'q':
                break
            
            idx = int(choice) - 1
            if idx < 0 or idx >= len(review_files):
                print("Invalid selection. Please try again.")
                continue
            
            selected_review = review_files[idx]
            review_data = load_review_file(selected_review["path"])
            
            if not review_data:
                continue
            
            invoice_data = review_data.get("invoice_data", {})
            display_invoice_data(invoice_data)
            
            print("\n=== Enter Corrections ===")
            print("Enter field:value pairs, one per line. Leave blank to finish.")
            print("Example: invoice_number:INV-12345")
            
            corrections = {}
            while True:
                correction = input("> ")
                if not correction:
                    break
                
                if ":" in correction:
                    field, value = correction.split(":", 1)
                    corrections[field.strip()] = value.strip()
                else:
                    print("Invalid format. Use field:value")
            
            if corrections:
                updated_review_data = process_corrections(review_data, corrections)
                if save_review_file(selected_review["path"], updated_review_data):
                    print("Corrections saved successfully.")
                    
                    # Update RAG database
                    update_rag_database(updated_review_data)
                    
                    # Submit to Document AI if PDF content is available
                    if "pdf_content" in invoice_data:
                        submit = input("Submit to Document AI for retraining? (y/n): ")
                        if submit.lower() == 'y':
                            submit_to_document_ai(updated_review_data)
                    else:
                        print("PDF content not available, cannot submit to Document AI")
            else:
                print("No corrections made.")
            
            # Refresh the list
            review_files = list_pending_reviews()
            display_review_list(review_files)
            
            if not review_files:
                print("No more pending reviews.")
                break
                
        except ValueError:
            print("Please enter a valid number.")
        except Exception as e:
            print(f"Error: {e}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Process invoices flagged for human review")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    parser.add_argument("--list", action="store_true", help="List pending reviews")
    
    args = parser.parse_args()
    
    if args.list:
        review_files = list_pending_reviews()
        display_review_list(review_files)
    elif args.interactive:
        interactive_review()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()