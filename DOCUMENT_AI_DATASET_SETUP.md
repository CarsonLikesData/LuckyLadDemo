# Setting Up a Document AI Dataset for Automated Retraining

This guide provides step-by-step instructions for creating a Document AI dataset and finding its ID for use with the automated retraining system.

## Prerequisites

- A Google Cloud account with Document AI enabled
- A Document AI processor already set up for invoice processing
- Appropriate permissions to create and manage datasets

## Step 1: Access the Document AI Console

1. Go to the Google Cloud Console: https://console.cloud.google.com/
2. Navigate to Document AI by:
   - Clicking on the navigation menu (hamburger icon) in the top-left corner
   - Scrolling down to "Artificial Intelligence"
   - Selecting "Document AI"

## Step 2: Select Your Processor

1. In the Document AI console, you'll see a list of your processors
2. Find and click on the invoice processor you're using with the Lucky Lad Invoice Processor system
3. This will open the processor details page

## Step 3: Create a New Dataset

1. In the processor details page, click on the "Datasets" tab at the top
2. Click the "+ CREATE DATASET" button
3. In the "Create dataset" dialog:
   - Enter a name for your dataset (e.g., "Invoice Corrections")
   - Optionally add a description (e.g., "Dataset for retraining with corrected invoices")
   - Select the appropriate processor version (usually the latest one)
   - Click "CREATE"

## Step 4: Find the Dataset ID

After creating the dataset, you need to find its ID to use with the automated retraining script. There are two ways to do this:

### Method 1: From the URL

1. Click on your newly created dataset in the list
2. Look at the URL in your browser's address bar
3. The URL will have a format like:
   ```
   https://console.cloud.google.com/ai/document-ai/datasets/DATASET_ID?project=PROJECT_ID
   ```
4. Copy the `DATASET_ID` portion from the URL

### Method 2: Using Google Cloud CLI

If you have the Google Cloud CLI installed, you can list all datasets and their IDs with this command:

```bash
gcloud beta ai document-datasets list --project=YOUR_PROJECT_ID --region=YOUR_REGION
```

Replace `YOUR_PROJECT_ID` and `YOUR_REGION` with your actual project ID and region.

## Step 5: Configure the Retraining Script

Now that you have the dataset ID, you need to configure the `auto_retrain_document_ai.py` script:

1. Open the `auto_retrain_document_ai.py` file in a text editor
2. Find the configuration section near the top:
   ```python
   # Configuration
   DOCUMENT_AI_DATASET_ID = "your_dataset_id_here"  # Replace with your dataset ID
   ```
3. Replace `"your_dataset_id_here"` with your actual dataset ID
4. Save the file

## Step 6: Verify Dataset Access

To ensure the script can access the dataset:

1. Run the script with the `--dry-run` flag:
   ```bash
   python auto_retrain_document_ai.py --dry-run
   ```
2. Check the output for any errors related to dataset access
3. If you see errors, verify:
   - The dataset ID is correct
   - Your service account has the necessary permissions
   - You're using the correct project and region

## Common Issues and Solutions

### "Dataset not found" error

- Double-check the dataset ID
- Ensure you're using the same project ID as in your Document AI setup
- Verify the region matches your Document AI processor's region

### Permission errors

- Ensure your service account has the following roles:
  - `roles/documentai.editor`
  - `roles/documentai.datasetAdmin`
- You can add these roles in the IAM section of the Google Cloud Console

### "Processor not found" error

- Verify the processor ID in your configuration matches the one in Document AI
- Ensure the processor is in the same region as specified in your configuration

## Next Steps

After setting up the dataset:

1. Run the automated retraining setup script:
   ```bash
   python setup_retraining_schedule.py
   ```
2. This will create a scheduled task to run the retraining process automatically
3. As corrected invoices accumulate, they will be added to your dataset
4. When enough corrections are available, Document AI will be retrained

## Monitoring Dataset Growth

You can monitor the growth of your dataset in the Document AI Console:

1. Go to the "Datasets" tab of your processor
2. Click on your dataset
3. You'll see statistics about the number of documents and annotations
4. This helps you track how many corrected examples have been added over time