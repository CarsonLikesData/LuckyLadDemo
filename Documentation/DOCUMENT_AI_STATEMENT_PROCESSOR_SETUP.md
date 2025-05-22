# Document AI Statement Processor Setup Guide

This guide provides comprehensive instructions for setting up a Google Document AI processor specifically for extracting data from vendor statements in the oil & gas industry. This processor will complement the existing invoice processor to provide complete document processing capabilities.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Statement Processor vs. Invoice Processor](#statement-processor-vs-invoice-processor)
4. [Step-by-Step Setup](#step-by-step-setup)
5. [Field Configuration Guide](#field-configuration-guide)
6. [Training Best Practices](#training-best-practices)
7. [Evaluation and Testing](#evaluation-and-testing)
8. [Integration with Existing Systems](#integration-with-existing-systems)
9. [Troubleshooting](#troubleshooting)
10. [Appendix: Sample Code](#appendix-sample-code)

## Overview

Vendor statements in the oil & gas industry contain critical financial information including aging summaries and transaction histories. Unlike invoices, statements provide a comprehensive view of the account status across multiple invoices and time periods.

The Document AI Statement Processor is designed to extract:
- Vendor and customer information
- Statement dates and totals
- Aging summaries (current, 30/60/90 days past due)
- Detailed transaction history
- Well-specific charges and credits

## Prerequisites

Before setting up the statement processor, ensure you have:

1. **Google Cloud Platform Account**
   - Document AI API enabled
   - Appropriate permissions (documentai.editor or higher)

2. **Training Data**
   - At least 50 synthetic statements generated using the `synthetic_statement_generator.py` tool
   - Properly formatted JSON files with field annotations
   - Both clean and degraded PDF versions for robust training

3. **Google Cloud Storage**
   - A bucket for storing training data
   - Appropriate IAM permissions for Document AI to access the bucket

4. **Development Environment**
   - Python 3.7+ with Google Cloud libraries installed
   - Google Cloud SDK configured

## Statement Processor vs. Invoice Processor

| Feature | Statement Processor | Invoice Processor |
|---------|---------------------|-------------------|
| Document Type | Account statements | Vendor invoices |
| Key Fields | Aging summary, transaction history | Line items, taxes, totals |
| Time Scope | Multiple transactions over time | Single transaction |
| Financial Purpose | Account status tracking | Payment processing |
| Typical Frequency | Monthly | Per transaction |

## Step-by-Step Setup

### 1. Generate Training Data

```bash
# Generate 50 statements with varied formats
python synthetic_statement_generator.py --batch 50 --vendor all --validate

# Generate additional degraded versions
python synthetic_statement_generator.py --batch 20 --vendor all --validate
```

### 2. Prepare Training Dataset Structure

Organize your training data into the following structure:

```
training_data/
├── train/
│   ├── statement1.pdf
│   ├── statement1.json
│   ├── statement2.pdf
│   ├── statement2.json
│   └── ... (70% of your data)
├── test/
│   ├── statement51.pdf
│   ├── statement51.json
│   └── ... (15% of your data)
└── validation/
    ├── statement76.pdf
    ├── statement76.json
    └── ... (15% of your data)
```

Use the following script to organize your data:

```python
import os
import shutil
import random

def organize_training_data(source_dir, target_dir, split=(0.7, 0.15, 0.15)):
    """Organize statement data into train/test/validation splits"""
    # Create target directories
    os.makedirs(os.path.join(target_dir, "train"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "test"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "validation"), exist_ok=True)
    
    # Get all PDF files
    pdf_files = [f for f in os.listdir(os.path.join(source_dir, "pdf")) 
                if f.endswith(".pdf") and not f.endswith("_degraded.pdf")]
    
    # Shuffle files for random split
    random.shuffle(pdf_files)
    
    # Calculate split indices
    train_end = int(len(pdf_files) * split[0])
    test_end = train_end + int(len(pdf_files) * split[1])
    
    # Split files
    train_files = pdf_files[:train_end]
    test_files = pdf_files[train_end:test_end]
    validation_files = pdf_files[test_end:]
    
    # Copy files to respective directories
    for pdf_file in train_files:
        base_name = pdf_file.replace(".pdf", "")
        shutil.copy(
            os.path.join(source_dir, "pdf", pdf_file),
            os.path.join(target_dir, "train", pdf_file)
        )
        shutil.copy(
            os.path.join(source_dir, "json", f"{base_name}.json"),
            os.path.join(target_dir, "train", f"{base_name}.json")
        )
    
    for pdf_file in test_files:
        base_name = pdf_file.replace(".pdf", "")
        shutil.copy(
            os.path.join(source_dir, "pdf", pdf_file),
            os.path.join(target_dir, "test", pdf_file)
        )
        shutil.copy(
            os.path.join(source_dir, "json", f"{base_name}.json"),
            os.path.join(target_dir, "test", f"{base_name}.json")
        )
    
    for pdf_file in validation_files:
        base_name = pdf_file.replace(".pdf", "")
        shutil.copy(
            os.path.join(source_dir, "pdf", pdf_file),
            os.path.join(target_dir, "validation", pdf_file)
        )
        shutil.copy(
            os.path.join(source_dir, "json", f"{base_name}.json"),
            os.path.join(target_dir, "validation", f"{base_name}.json")
        )
    
    print(f"Organized {len(train_files)} training, {len(test_files)} test, and {len(validation_files)} validation files")

# Usage
organize_training_data("synthetic_statements", "training_data")
```

### 3. Upload Training Data to Google Cloud Storage

```bash
# Upload to GCS
gsutil -m cp -r training_data gs://your-bucket/statement-processor/
```

### 4. Create a New Document AI Processor

1. Navigate to the [Document AI section](https://console.cloud.google.com/ai/document-ai) in Google Cloud Console
2. Click "Create Processor"
3. Select "Custom Extraction" as the processor type
4. Configure the processor:
   - Name: "statement-processor-v1"
   - Region: Select your preferred region
   - Click "Create"

### 5. Configure Field Definitions

In the processor configuration, define the following fields:

#### Header Information
- `statement_date` (Date)
- `vendor_name` (Text)
- `vendor_address` (Address)
- `customer_name` (Text)
- `customer_address` (Address)
- `amount_due` (Currency)

#### Aging Summary
- `current_amount` (Currency)
- `days_1_30_amount` (Currency)
- `days_31_60_amount` (Currency)
- `days_61_90_amount` (Currency)
- `days_over_90_amount` (Currency)

#### Transaction Fields
- `transaction_date` (Date)
- `transaction_description` (Text)
- `transaction_amount` (Currency)
- `transaction_balance` (Currency)
- `invoice_number` (Text, optional)
- `well_name` (Text, optional)

### 6. Train the Processor

1. In the Document AI console, select your processor
2. Click "Train New Version"
3. Configure the training:
   - Training data location: `gs://your-bucket/statement-processor/`
   - Training split: Use default or customize (e.g., 70% train, 15% test, 15% validation)
   - Click "Start Training"

Training typically takes 1-4 hours depending on the dataset size.

### 7. Evaluate and Deploy

1. Review the evaluation metrics in the Document AI console
2. If the performance is satisfactory (>85% precision/recall), deploy the processor
3. If not, generate more training data or adjust field definitions

## Field Configuration Guide

### Critical Fields

These fields should be prioritized for high accuracy:

| Field | Description | Type | Example |
|-------|-------------|------|---------|
| `statement_date` | Date of the statement | Date | "1/5/2024" |
| `amount_due` | Total amount due | Currency | "$25,152.43" |
| `current_amount` | Current amount | Currency | "$665.12" |
| `days_1_30_amount` | 1-30 days past due | Currency | "$13,079.29" |
| `days_31_60_amount` | 31-60 days past due | Currency | "$3,757.60" |
| `days_61_90_amount` | 61-90 days past due | Currency | "$5,770.82" |
| `days_over_90_amount` | Over 90 days past due | Currency | "$1,879.60" |

### Transaction Fields

For each transaction in the statement:

| Field | Description | Type | Example |
|-------|-------------|------|---------|
| `transaction_date` | Date of transaction | Date | "09/20/2023" |
| `transaction_description` | Description | Text | "INV #6378. Due 10/20/2023..." |
| `transaction_amount` | Amount | Currency | "$562.20" |
| `transaction_balance` | Running balance | Currency | "$562.20" |

## Training Best Practices

1. **Data Variety**
   - Include statements from multiple vendors
   - Vary aging distributions (current-heavy, past-due-heavy)
   - Include different transaction types (invoices, credits, adjustments)

2. **Quality Control**
   - Validate JSON schema before training
   - Ensure field names match between JSON and processor configuration
   - Check for missing or incorrect data

3. **Degradation Techniques**
   - Include both clean and degraded versions
   - Vary degradation levels (slight, moderate)
   - Test with real-world scanned documents

## Evaluation and Testing

After training, evaluate your processor using:

1. **Built-in Evaluation**
   - Review precision/recall metrics for each field
   - Examine the confusion matrix
   - Check sample documents with extraction results

2. **Manual Testing**
   - Upload sample statements not in the training set
   - Verify extraction accuracy for critical fields
   - Test with real-world statements

3. **Integration Testing**
   - Test with your document processing pipeline
   - Verify data flows correctly to downstream systems
   - Check error handling for edge cases

## Integration with Existing Systems

### RAG Integration

To integrate the statement processor with your RAG system:

```python
# Add to bootstrap_rag_with_samples.py

def process_statements_for_rag(project_id, location, processor_id, bucket_name):
    """Process statements and add to RAG database"""
    from google.cloud import documentai_v1 as documentai
    from google.cloud import storage
    
    # Initialize clients
    doc_client = documentai.DocumentProcessorServiceClient()
    storage_client = storage.Client()
    
    # Format the processor name
    name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"
    
    # List statement files in the bucket
    bucket = storage_client.get_bucket(bucket_name)
    blobs = bucket.list_blobs(prefix="statements/")
    
    for blob in blobs:
        if blob.name.endswith(".pdf"):
            # Download the file
            content = blob.download_as_bytes()
            
            # Process the document
            document = {"content": content, "mime_type": "application/pdf"}
            request = {"name": name, "document": document}
            
            result = doc_client.process_document(request=request)
            document = result.document
            
            # Extract entities
            entities = {}
            for entity in document.entities:
                entities[entity.type_] = entity.mention_text
            
            # Add to RAG database
            add_statement_to_rag(blob.name, entities)
```

### Automated Retraining

Set up automated retraining with:

```python
# Add to auto_retrain_document_ai.py

def schedule_statement_processor_retraining(project_id, location, processor_id, 
                                          bucket_name, schedule="0 0 1 * *"):
    """Schedule monthly retraining of the statement processor"""
    from google.cloud import scheduler_v1
    
    client = scheduler_v1.CloudSchedulerClient()
    parent = f"projects/{project_id}/locations/{location}"
    
    job = {
        "name": f"{parent}/jobs/retrain-statement-processor",
        "description": "Monthly retraining of Document AI statement processor",
        "schedule": schedule,  # Monthly on the 1st
        "time_zone": "America/Chicago",
        "http_target": {
            "uri": f"https://{location}-documentai.googleapis.com/v1/projects/{project_id}/locations/{location}/processors/{processor_id}:train",
            "http_method": scheduler_v1.HttpMethod.POST,
            "body": f"{{\"inputData\": {{\"trainingDataset\": {{\"gcsSource\": {{\"input_uris\": [\"gs://{bucket_name}/statement-processor/*\"]}}}}}}}}}".encode(),
            "oauth_token": {
                "service_account_email": f"service-account@{project_id}.iam.gserviceaccount.com"
            }
        }
    }
    
    client.create_job(parent=parent, job=job)
```

## Troubleshooting

### Common Issues and Solutions

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Low precision/recall | Insufficient training data | Generate more varied statements |
| Missing fields | JSON schema mismatch | Verify field names match processor configuration |
| Incorrect field types | Type definition issues | Check field type definitions |
| Training failures | GCS permissions | Verify Document AI has access to your bucket |
| Extraction errors | Document format variations | Add more format variations to training data |

### Debugging Tips

1. **Check JSON Schema**
   ```bash
   python synthetic_statement_generator.py --validate-schema
   ```

2. **Validate Training Data**
   ```bash
   python synthetic_statement_generator.py --batch 5 --validate
   ```

3. **Test Processor Manually**
   Upload a sample statement to the Document AI console and check extraction results.

## Appendix: Sample Code

### Processing a Statement

```python
from google.cloud import documentai_v1 as documentai
import json

def process_statement(project_id, location, processor_id, file_path):
    """Process a statement using Document AI"""
    client = documentai.DocumentProcessorServiceClient()
    
    # Format the processor name
    name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"
    
    # Read the file
    with open(file_path, "rb") as file:
        content = file.read()
    
    # Configure the process request
    document = {"content": content, "mime_type": "application/pdf"}
    request = {"name": name, "document": document}
    
    # Process the document
    result = client.process_document(request=request)
    document = result.document
    
    # Extract and return the entities
    entities = {}
    for entity in document.entities:
        entities[entity.type_] = entity.mention_text
    
    # Save results to JSON
    output_path = file_path.replace(".pdf", "_extracted.json")
    with open(output_path, "w") as f:
        json.dump(entities, f, indent=2)
    
    print(f"Extraction results saved to: {output_path}")
    return entities

# Usage
process_statement(
    project_id="your-project-id",
    location="us-central1",
    processor_id="statement-processor-id",
    file_path="path/to/statement.pdf"
)
```

### Batch Processing Statements

```python
import os
from google.cloud import documentai_v1 as documentai
from concurrent.futures import ThreadPoolExecutor

def batch_process_statements(project_id, location, processor_id, directory):
    """Process multiple statements in parallel"""
    client = documentai.DocumentProcessorServiceClient()
    name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"
    
    # Get all PDF files
    pdf_files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".pdf")]
    
    def process_file(file_path):
        with open(file_path, "rb") as file:
            content = file.read()
        
        document = {"content": content, "mime_type": "application/pdf"}
        request = {"name": name, "document": document}
        
        result = client.process_document(request=request)
        
        # Save results
        output_path = file_path.replace(".pdf", "_extracted.json")
        with open(output_path, "w") as f:
            entities = {}
            for entity in result.document.entities:
                entities[entity.type_] = entity.mention_text
            json.dump(entities, f, indent=2)
        
        return file_path, "Success"
    
    # Process files in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(process_file, pdf_files))
    
    return results
```

For more information, see the [Google Document AI documentation](https://cloud.google.com/document-ai/docs/processors-custom).