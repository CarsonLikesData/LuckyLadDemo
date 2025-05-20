# Lucky Lad Invoice Processor

An automated invoice processing system for oil and gas companies that extracts, validates, and stores invoice data using AI.

## Overview

The Lucky Lad Invoice Processor is a comprehensive solution that:

1. **Monitors Email** - Automatically checks Gmail and/or Outlook for new invoice PDFs
2. **Extracts Data** - Uses Google Document AI for initial data extraction from PDFs
3. **Validates & Standardizes** - Leverages Vertex AI (Gemini) to validate and enhance extracted data
4. **Organizes Files** - Intelligently sorts invoices by well name and date
5. **Stores Data** - Saves processed information to Snowflake for reporting and analysis

## Features

- **Intelligent Well Name Detection**: Automatically identifies well names from various invoice fields
- **Hierarchical File Organization**: Stores invoices in a structured directory system by well name and date
- **AI-Powered Data Validation**: Uses Vertex AI to verify and standardize extracted information
- **Snowflake Integration**: Seamlessly stores processed data for reporting and analytics
- **Email Processing**: Monitors Gmail and/or Outlook for new invoices and organizes them for tracking

## Requirements

### Dependencies
- Python 3.8+
- Google Cloud Platform account with Document AI and Vertex AI enabled
- Gmail account with IMAP access and/or Outlook/Exchange account
- Optional: exchangelib library for Outlook support
- Snowflake account with appropriate permissions

### API Keys and Credentials
- Google Cloud credentials (application_default_credentials.json)
- Gmail app password (if using Gmail)
- Outlook/Exchange credentials (if using Outlook)
- Snowflake credentials

## Installation

1. Clone the repository
2. Install required packages:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   ```
   export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/application_default_credentials.json"
   export SNOWFLAKE_PASSWORD="your_snowflake_password"
   
   # For Gmail
   export GMAIL_PASSWORD="your_gmail_app_password"
   
   # For Outlook
   export USE_OUTLOOK="true"
   export OUTLOOK_EMAIL="your.email@company.com"
   export OUTLOOK_PASSWORD="your_outlook_password"
   export OUTLOOK_SERVER="your_exchange_server"  # Optional, defaults to outlook.office365.com
   ```

## Configuration

The script uses several configuration variables that can be modified in the code:

- **GCP Configuration**: Project ID, location, processor ID
- **Email Configuration**:
  - Gmail: Username and password
  - Outlook: Email, password, server, and SSL verification settings
- **Snowflake Configuration**: Account, user, database, schema, warehouse, table
- **Vertex AI Configuration**: Project, location, API endpoint, model

## Usage

Run the main script to process new invoices:

```
python lucky_lad_invoice_processor.py
```

For debugging mode with detailed logging:

```
# Modify the debug_mode parameter in the main() function call
main(debug_mode=True)
```

## Directory Structure

Processed invoices are organized in the following structure:
```
processed_invoices/
├── [Well Name]/
│   ├── [YYYY-MM-Month]/
│   │   ├── invoice1.pdf
│   │   ├── invoice2.pdf
│   │   └── ...
│   └── ...
└── ...
```

## Development Roadmap

The following features are planned for future development:

1. RAG engine for enhanced data validation and standardization
2. Manual review system for processed invoices
3. Notification system for new invoice processing
4. Improved error handling
5. ✅ Outlook email processing support (Implemented)
6. Invoice payment status tracking with PowerBI dashboard integration
7. Automated job scheduling (AM and PM runs)
8. Duplicate invoice detection
9. Application deployment improvements

## License

[Specify your license here]

## Contributors

- [Your Name/Team]
- Callaway (mentioned in TODOs)