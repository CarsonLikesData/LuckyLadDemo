# Email Test Sender Setup Guide

## Overview
This script sends batches of test emails with invoice PDF attachments to test the Lucky Lad Invoice Processor. It supports both Gmail and Outlook, matching what your processor monitors.

## Prerequisites

### 1. Install Required Packages
```bash
# For Gmail only
pip install -r requirements_gmail.txt

# For Outlook support
pip install -r requirements_outlook.txt

# Or install manually
pip install smtplib email pathlib
pip install exchangelib  # For Outlook support
```

### 2. Set Up Email Credentials

#### For Gmail:
1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a password for "Mail"
3. Set environment variables:
```bash
export TEST_GMAIL_SENDER="your_sender@gmail.com"
export TEST_GMAIL_PASSWORD="your_16_char_app_password"
```

#### For Outlook:
```bash
export TEST_OUTLOOK_SENDER="your_email@company.com"
export TEST_OUTLOOK_PASSWORD="your_password"
export TEST_OUTLOOK_SERVER="outlook.office365.com"  # Or your Exchange server
```

### 3. Prepare Invoice PDFs
Create a folder called `test_invoices` and add your test PDF files:
```
test_invoices/
├── invoice_001.pdf
├── invoice_002.pdf
├── statement_001.pdf
└── ...
```

## Usage

### Basic Usage
```bash
# Send test emails via Gmail (default)
python email_test_sender.py

# Send via Outlook
python email_test_sender.py --method outlook

# Send via both Gmail and Outlook
python email_test_sender.py --method both
```

### Advanced Options
```bash
# Custom batch configuration
python email_test_sender.py --batch-size 10 --batch-delay 60 --max-emails 50

# Use different invoice folder
python email_test_sender.py --invoice-folder /path/to/invoices

# Use configuration file
python email_test_sender.py --config-file test_config.json
```

### Command Line Arguments
- `--method`: Choose 'gmail', 'outlook', or 'both'
- `--batch-size`: Number of emails per batch (default: 5)
- `--batch-delay`: Seconds between batches (default: 30)
- `--max-emails`: Maximum total emails to send (default: 50)
- `--invoice-folder`: Folder containing PDF files (default: test_invoices)
- `--config-file`: JSON configuration file to load

## Test Scenarios

### 1. Basic Functionality Test
```bash
# Send 10 emails in batches of 5
python email_test_sender.py --max-emails 10 --batch-size 5
```

### 2. Load Test
```bash
# Send 100 emails to test processor performance
python email_test_sender.py --max-emails 100 --batch-size 20 --batch-delay 10
```

### 3. Statement vs Invoice Test
Name some PDFs with "statement" in the filename to test statement detection:
- `statement_2024_01.pdf`
- `invoice_1234.pdf`
- `atkinson_statement.pdf`

### 4. Well Name Detection Test
The script randomly assigns well names and vendor names to test the processor's extraction logic.

## Monitoring Results

### 1. Check Email Test Log
The script creates a timestamped log file:
```bash
cat email_test_log_20240122_143022.json
```

### 2. Monitor Invoice Processor
Watch your invoice processor logs to see:
- PDFs being detected and processed
- Document AI extraction results
- Vertex AI validation
- Files being sorted into well name directories
- Data being uploaded to Snowflake

### 3. Verify in Snowflake
Check your Snowflake tables:
```sql
-- Check invoice headers
SELECT * FROM OCCLUSION.WELLS.LLE_INVOICE_HEADER 
ORDER BY PROCESSED_DATE DESC;

-- Check line items
SELECT * FROM OCCLUSION.WELLS.LLE_INVOICE_LINE_ITEMS
ORDER BY INVOICE_NUMBER DESC;

-- Check statements
SELECT * FROM OCCLUSION.WELLS.LLE_STATEMENTS
ORDER BY CREATED_AT DESC;
```

### 4. Check File Organization
Verify PDFs are sorted correctly:
```bash
# Check invoice organization by well
ls -la processed_invoices/

# Check statements by vendor  
ls -la processed_statements/

# Check flagged items
ls -la invoices_for_review/
```

## Troubleshooting

### Gmail Issues
- **Authentication failed**: Ensure you're using an App Password, not your regular password
- **Less secure app blocked**: Use App Password with 2FA enabled
- **Rate limiting**: Reduce batch size or increase delays

### Outlook Issues
- **Connection failed**: Check server address and firewall settings
- **Authentication failed**: May need to use domain\username format
- **Certificate errors**: Set `OUTLOOK_DISABLE_VERIFY_SSL=True` for dev environments only

### PDF Issues
- **No PDFs found**: Check the invoice folder path
- **PDF read errors**: Ensure PDFs are not corrupted
- **Large PDFs**: May need to increase email size limits

## Best Practices

1. **Start Small**: Begin with 5-10 emails to verify everything works
2. **Monitor Actively**: Watch both sender and processor logs during testing
3. **Vary Content**: Use different PDF files and email content to test edge cases
4. **Check Results**: Verify data in Snowflake matches PDF content
5. **Clean Up**: The processor marks emails as read and moves them to monthly folders

## Example Test Workflow

```bash
# 1. Set up environment
export TEST_GMAIL_SENDER="test@gmail.com"
export TEST_GMAIL_PASSWORD="abcd1234efgh5678"
mkdir test_invoices
cp /path/to/sample/pdfs/*.pdf test_invoices/

# 2. Run initial test
python email_test_sender.py --max-emails 5

# 3. Check processor picked up emails
# Monitor processor logs...

# 4. Run larger test
python email_test_sender.py --max-emails 50 --batch-size 10

# 5. Verify results in Snowflake
# Run SQL queries to check data...
```

## Configuration File Format
Save as `test_config.json` and use with `--config-file`:
```json
{
  "batch_size": 10,
  "batch_delay": 45,
  "max_emails": 100,
  "invoice_folder": "my_test_invoices",
  "vendors": ["Custom Vendor 1", "Custom Vendor 2"],
  "well_names": ["Test Well #1", "Test Well #2"]
}
```