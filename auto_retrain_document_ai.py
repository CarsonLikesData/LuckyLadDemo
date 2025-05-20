"""
Automated Document AI Retraining Script
--------------------------------------
This script automates the process of sending corrected invoices to Document AI for retraining.
It scans the invoices_for_review directory for reviewed invoices, formats the corrections
in the format required by Document AI, and submits them for retraining.

Usage:
    python auto_retrain_document_ai.py [--threshold N] [--dataset_id DATASET_ID]

Options:
    --threshold N        Minimum number of corrected invoices required to trigger retraining (default: 5)
    --dataset_id ID      Document AI dataset ID to use for retraining (required if not set in script)
    --dry-run            Run without actually submitting to Document AI (for testing)
"""

import os
import json
import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from google.cloud import documentai_v1 as documentai

# Import from main processor
from lucky_lad_invoice_processor import (
    add_to_document_ai_dataset,
    REVIEW_DIR,
    PROJECT_ID,
    LOCATION,
    PROCESSOR_ID
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("document_ai_retraining.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("auto_retrain")

# Configuration
DOCUMENT_AI_DATASET_ID = "your_dataset_id_here"  # Replace with your dataset ID or use --dataset_id
MIN_CORRECTIONS_FOR_RETRAINING = 5  # Minimum number of corrected invoices to trigger retraining
RETRAINING_COOLDOWN_DAYS = 7  # Minimum days between retraining jobs
LAST_RETRAINING_FILE = "last_retraining.json"  # File to track last retraining date

def load_last_retraining_info():
    """Load information about the last retraining job"""
    if os.path.exists(LAST_RETRAINING_FILE):
        try:
            with open(LAST_RETRAINING_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading last retraining info: {e}")
    
    return {
        "last_retraining_date": None,
        "submitted_reviews": []
    }

def save_last_retraining_info(info):
    """Save information about the last retraining job"""
    try:
        with open(LAST_RETRAINING_FILE, 'w') as f:
            json.dump(info, f, indent=2)
        logger.info(f"Updated retraining info saved to {LAST_RETRAINING_FILE}")
    except Exception as e:
        logger.error(f"Error saving retraining info: {e}")

def find_corrected_reviews():
    """Find all corrected reviews that haven't been submitted to Document AI"""
    if not os.path.exists(REVIEW_DIR):
        logger.warning(f"Review directory {REVIEW_DIR} does not exist.")
        return []
    
    # Load last retraining info to get list of already submitted reviews
    retraining_info = load_last_retraining_info()
    submitted_reviews = set(retraining_info.get("submitted_reviews", []))
    
    corrected_reviews = []
    for filename in os.listdir(REVIEW_DIR):
        if not filename.endswith(".json"):
            continue
        
        file_path = os.path.join(REVIEW_DIR, filename)
        
        # Skip if this review has already been submitted
        if file_path in submitted_reviews:
            continue
        
        try:
            with open(file_path, 'r') as f:
                review_data = json.load(f)
                
                # Check if this review has been corrected
                if review_data.get("status") == "reviewed":
                    # Check if it has corrections
                    if "corrections" in review_data and review_data["corrections"]:
                        corrected_reviews.append({
                            "path": file_path,
                            "data": review_data
                        })
        except Exception as e:
            logger.error(f"Error reading review file {file_path}: {e}")
    
    logger.info(f"Found {len(corrected_reviews)} corrected reviews that haven't been submitted")
    return corrected_reviews

def format_for_document_ai(review_data):
    """Format the corrected data for Document AI training"""
    invoice_data = review_data.get("invoice_data", {})
    corrections = review_data.get("corrections", {})
    
    # Get the PDF content if available
    pdf_content = invoice_data.get("pdf_content")
    if not pdf_content:
        logger.warning("PDF content not available in review data")
        return None
    
    # Get the original entities
    entities_dict = invoice_data.get("entities", {})
    
    # Apply corrections to entities
    for field, value in corrections.items():
        entities_dict[field] = value
    
    # Convert entities to Document AI format
    ground_truth_entities = []
    for entity_type, mention_text in entities_dict.items():
        # This is a simplified conversion - actual implementation would be more complex
        # and would need to include text segments with start/end indices
        ground_truth_entity = {
            "type": entity_type,
            "mention_text": mention_text,
            # In a real implementation, you would need to include:
            # "text_segments": [{"start_index": start, "end_index": end}]
        }
        ground_truth_entities.append(ground_truth_entity)
    
    return {
        "pdf_content": pdf_content,
        "ground_truth_entities": ground_truth_entities
    }

def should_trigger_retraining(corrected_reviews):
    """Determine if retraining should be triggered"""
    # Check if we have enough corrected reviews
    if len(corrected_reviews) < MIN_CORRECTIONS_FOR_RETRAINING:
        logger.info(f"Not enough corrected reviews for retraining. Need {MIN_CORRECTIONS_FOR_RETRAINING}, have {len(corrected_reviews)}")
        return False
    
    # Check if we're within the cooldown period
    retraining_info = load_last_retraining_info()
    last_retraining_date = retraining_info.get("last_retraining_date")
    
    if last_retraining_date:
        last_date = datetime.fromisoformat(last_retraining_date)
        cooldown_until = last_date + timedelta(days=RETRAINING_COOLDOWN_DAYS)
        
        if datetime.now() < cooldown_until:
            days_remaining = (cooldown_until - datetime.now()).days
            logger.info(f"Within cooldown period. {days_remaining} days remaining until next retraining can be triggered.")
            return False
    
    return True

def submit_to_document_ai(corrected_reviews, dataset_id, dry_run=False):
    """Submit corrected reviews to Document AI for retraining"""
    if dry_run:
        logger.info("DRY RUN: Would submit the following reviews to Document AI:")
        for review in corrected_reviews:
            logger.info(f"  - {os.path.basename(review['path'])}")
        return []
    
    submitted_paths = []
    
    for review in corrected_reviews:
        try:
            # Format the data for Document AI
            formatted_data = format_for_document_ai(review["data"])
            if not formatted_data:
                logger.warning(f"Could not format review {review['path']} for Document AI")
                continue
            
            # Submit to Document AI
            response = add_to_document_ai_dataset(
                PROJECT_ID,
                LOCATION,
                PROCESSOR_ID,
                dataset_id,
                formatted_data["pdf_content"],
                formatted_data["ground_truth_entities"]
            )
            
            if response:
                logger.info(f"Successfully submitted {review['path']} to Document AI")
                submitted_paths.append(review["path"])
                
                # Update the review status
                review["data"]["document_ai_submitted"] = True
                review["data"]["document_ai_submission_time"] = datetime.now().isoformat()
                
                with open(review["path"], 'w') as f:
                    json.dump(review["data"], f, indent=2)
            else:
                logger.error(f"Failed to submit {review['path']} to Document AI")
        except Exception as e:
            logger.error(f"Error submitting {review['path']} to Document AI: {e}")
    
    return submitted_paths

def trigger_processor_retraining(dataset_id, dry_run=False):
    """Trigger retraining of the Document AI processor"""
    if dry_run:
        logger.info("DRY RUN: Would trigger Document AI processor retraining")
        return True
    
    try:
        # Initialize Document AI client
        client = documentai.DocumentProcessorServiceClient()
        
        # Format the processor path
        processor_path = client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)
        
        # Format the dataset path
        dataset_path = client.dataset_path(PROJECT_ID, LOCATION, PROCESSOR_ID, dataset_id)
        
        # Create training request
        request = documentai.TrainProcessorVersionRequest(
            processor=processor_path,
            input_data={
                "dataset": dataset_path
            }
        )
        
        # Trigger training
        operation = client.train_processor_version(request)
        
        logger.info(f"Triggered Document AI processor retraining: {operation.operation.name}")
        return True
    except Exception as e:
        logger.error(f"Error triggering Document AI processor retraining: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Automate Document AI retraining with corrected invoices")
    parser.add_argument("--threshold", type=int, default=MIN_CORRECTIONS_FOR_RETRAINING,
                        help=f"Minimum number of corrected invoices required to trigger retraining (default: {MIN_CORRECTIONS_FOR_RETRAINING})")
    parser.add_argument("--dataset_id", type=str, default=DOCUMENT_AI_DATASET_ID,
                        help="Document AI dataset ID to use for retraining")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run without actually submitting to Document AI (for testing)")
    
    args = parser.parse_args()
    
    # Update configuration with command line arguments
    global MIN_CORRECTIONS_FOR_RETRAINING
    MIN_CORRECTIONS_FOR_RETRAINING = args.threshold
    
    dataset_id = args.dataset_id
    if not dataset_id:
        logger.error("No Document AI dataset ID provided. Use --dataset_id or set DOCUMENT_AI_DATASET_ID in the script.")
        return
    
    # Find corrected reviews
    corrected_reviews = find_corrected_reviews()
    
    # Check if we should trigger retraining
    if not should_trigger_retraining(corrected_reviews):
        logger.info("Retraining not triggered. Exiting.")
        return
    
    # Submit corrected reviews to Document AI
    submitted_paths = submit_to_document_ai(corrected_reviews, dataset_id, args.dry_run)
    
    if submitted_paths:
        logger.info(f"Submitted {len(submitted_paths)} corrected reviews to Document AI")
        
        # Trigger processor retraining
        if trigger_processor_retraining(dataset_id, args.dry_run):
            # Update last retraining info
            retraining_info = load_last_retraining_info()
            retraining_info["last_retraining_date"] = datetime.now().isoformat()
            retraining_info["submitted_reviews"].extend(submitted_paths)
            save_last_retraining_info(retraining_info)
            
            logger.info("Document AI retraining process completed successfully")
        else:
            logger.error("Failed to trigger Document AI processor retraining")
    else:
        logger.warning("No reviews were submitted to Document AI")

if __name__ == "__main__":
    main()