# Automating Document AI Retraining with Corrected Invoices

This document explains how to set up an automated process for retraining Document AI with corrected invoice examples. This ensures that Document AI continuously improves its extraction capabilities, especially for new invoice types.

## Overview

I've created a script called `auto_retrain_document_ai.py` that automates the process of:

1. Finding corrected invoices that have been reviewed by humans
2. Submitting them to Document AI for retraining
3. Triggering the retraining process when enough examples have accumulated

## How It Works

The automated retraining process works as follows:

1. The script scans the `invoices_for_review` directory for invoices that have been reviewed and corrected
2. It checks if there are enough corrected invoices to trigger retraining (default: 5)
3. It ensures a minimum cooldown period between retraining jobs (default: 7 days)
4. It formats the corrections in the format required by Document AI
5. It submits the corrections to Document AI for retraining
6. It updates the status of the invoices to indicate they've been submitted
7. It tracks which invoices have been submitted to avoid duplicates

## Setup

### 1. Create a Document AI Dataset

Before using the script, you need to create a dataset in Document AI:

1. Go to the [Document AI Console](https://console.cloud.google.com/ai/document-ai)
2. Select your processor
3. Click on "Datasets" tab
4. Click "Create Dataset"
5. Note the dataset ID for use with the script

### 2. Configure the Script

Edit the `auto_retrain_document_ai.py` script to set:

```python
# Configuration
DOCUMENT_AI_DATASET_ID = "your_dataset_id_here"  # Replace with your dataset ID
MIN_CORRECTIONS_FOR_RETRAINING = 5  # Minimum number of corrected invoices to trigger retraining
RETRAINING_COOLDOWN_DAYS = 7  # Minimum days between retraining jobs
```

### 3. Set Up Scheduled Execution

Set up a scheduled task to run the script regularly:

#### On Linux/Mac (using cron):

```bash
# Run daily at 2 AM
0 2 * * * /path/to/python /path/to/auto_retrain_document_ai.py >> /path/to/retraining.log 2>&1
```

#### On Windows (using Task Scheduler):

1. Open Task Scheduler
2. Create a new task
3. Set the trigger to run daily
4. Set the action to run the script:
   - Program: `python`
   - Arguments: `C:\path\to\auto_retrain_document_ai.py`

## Usage

### Manual Execution

You can also run the script manually:

```bash
# Basic usage
python auto_retrain_document_ai.py

# Specify a different threshold
python auto_retrain_document_ai.py --threshold 10

# Specify a different dataset ID
python auto_retrain_document_ai.py --dataset_id your_dataset_id

# Test without actually submitting to Document AI
python auto_retrain_document_ai.py --dry-run
```

### Monitoring

The script logs all activities to both the console and a log file (`document_ai_retraining.log`). You can check this log to monitor the retraining process.

## Integration with Human Review Process

The automated retraining process integrates with the human review process as follows:

1. When a new invoice type is detected, it's flagged for human review
2. The human reviewer corrects any extraction errors using `human_review_processor.py`
3. The corrected invoice is saved with a "reviewed" status
4. The `auto_retrain_document_ai.py` script picks up these corrected invoices
5. When enough corrected invoices accumulate, Document AI is retrained
6. The improved Document AI model is then used for future invoice processing

## Best Practices

1. **Regular Reviews**: Ensure that flagged invoices are reviewed regularly
2. **Diverse Examples**: Try to include diverse examples of each invoice type
3. **Monitor Performance**: Track Document AI's performance over time to ensure it's improving
4. **Adjust Thresholds**: Adjust the retraining threshold based on your needs
5. **Backup Datasets**: Regularly backup your Document AI datasets

## Troubleshooting

If you encounter issues with the retraining process:

1. **Check Permissions**: Ensure your service account has the necessary permissions
2. **Check Dataset**: Verify that the dataset ID is correct
3. **Check Log Files**: Review the log files for error messages
4. **Test with Dry Run**: Use the `--dry-run` flag to test without actually submitting
5. **Manual Submission**: If automated submission fails, you can manually submit corrected invoices

## Conclusion

By automating the Document AI retraining process, you ensure that your invoice processing system continuously improves over time, especially for new invoice types. This creates a virtuous cycle where:

1. New invoice types are detected and flagged
2. Humans correct the extraction errors
3. Document AI learns from these corrections
4. Future invoices of the same type are processed more accurately