"""
Invoice Email Test Sender
-------------------------
Sends batches of emails with invoice PDFs attached to test the Lucky Lad Invoice Processor.
Supports both Gmail and Outlook sending methods.
"""

import os
import time
import random
from datetime import datetime
from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import json
import argparse

# Try to import Outlook libraries
try:
    from exchangelib import (
        Credentials,
        Account,
        Configuration,
        DELEGATE,
        Message,
        FileAttachment,
        HTMLBody,
    )
    OUTLOOK_AVAILABLE = True
except ImportError:
    print("Warning: exchangelib not installed. Outlook functionality will be disabled.")
    print("Install with: pip install exchangelib")
    OUTLOOK_AVAILABLE = False

# Configuration class
class EmailConfig:
    """Configuration for email sending"""
    def __init__(self):
        # Gmail settings
        self.gmail_sender = os.environ.get("TEST_GMAIL_SENDER", "your_sender@gmail.com")
        self.gmail_password = os.environ.get("TEST_GMAIL_PASSWORD", "your_app_password")
        self.gmail_recipient = "lucky.lad.test.df@gmail.com"  # From processor code
        
        # Outlook settings
        self.outlook_sender = os.environ.get("TEST_OUTLOOK_SENDER", "")
        self.outlook_password = os.environ.get("TEST_OUTLOOK_PASSWORD", "")
        self.outlook_server = os.environ.get("TEST_OUTLOOK_SERVER", "outlook.office365.com")
        self.outlook_recipient = os.environ.get("OUTLOOK_EMAIL", "")  # From processor code
        
        # Test settings
        self.batch_size = 5  # Number of emails per batch
        self.batch_delay = 30  # Seconds between batches
        self.email_delay = 2  # Seconds between individual emails
        self.max_emails = 50  # Maximum total emails to send
        
        # Invoice folder
        self.invoice_folder = "test_invoices"  # Folder containing PDF invoices
        
        # Email variations for testing
        self.subject_templates = [
            "Invoice #{invoice_num} from {vendor}",
            "Statement of Account - {vendor}",
            "{vendor} - Invoice for {month} {year}",
            "Payment Due - Invoice #{invoice_num}",
            "{vendor} Monthly Statement",
            "New Invoice from {vendor}",
            "Account Statement - {vendor} - {month}",
            "Invoice #{invoice_num} - Well: {well_name}",
        ]
        
        self.body_templates = [
            """
            Dear Lucky Lad Energy,
            
            Please find attached invoice #{invoice_num} for your review.
            
            Vendor: {vendor}
            Date: {date}
            Amount: ${amount}
            
            Best regards,
            {vendor} Accounting
            """,
            """
            Hello,
            
            Attached is your monthly statement from {vendor}.
            
            Statement Date: {date}
            Total Due: ${amount}
            
            Thank you for your business.
            """,
            """
            Lucky Lad Energy,
            
            Invoice #{invoice_num} is attached for services rendered.
            
            Well/Location: {well_name}
            Service Date: {date}
            
            Please remit payment within 30 days.
            
            {vendor}
            """,
        ]
        
        # Test vendor names (from processor code patterns)
        self.vendors = [
            "Atkinson Propane",
            "Reagan Power Compression", 
            "Oil Field Services Inc",
            "Tank Battery Maintenance",
            "Godchaux Well Services",
            "McInis Equipment",
            "Kirby Drilling",
            "Temple Field Operations",
            "ABC Lubricants",
            "XYZ Chemical Supply",
        ]
        
        # Test well names (from processor code patterns)
        self.well_names = [
            "Godchaux #1",
            "McInis #2H",
            "Kirby Tank Battery",
            "Temple TB",
            "Reagan Compression Site",
            "Well #47",
            "Lucky Lad #3",
            "Field Station Alpha",
        ]

class EmailSender:
    """Base class for email sending"""
    def __init__(self, config: EmailConfig):
        self.config = config
        self.sent_count = 0
        self.failed_count = 0
        self.log_file = f"email_test_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.log_data = []
    
    def get_invoice_files(self):
        """Get all PDF files from the invoice folder"""
        invoice_path = Path(self.config.invoice_folder)
        if not invoice_path.exists():
            raise FileNotFoundError(f"Invoice folder not found: {self.config.invoice_folder}")
        
        pdf_files = list(invoice_path.glob("*.pdf"))
        if not pdf_files:
            raise FileNotFoundError(f"No PDF files found in: {self.config.invoice_folder}")
        
        print(f"Found {len(pdf_files)} PDF files in {self.config.invoice_folder}")
        return pdf_files
    
    def generate_email_content(self, pdf_file, index):
        """Generate randomized email content"""
        # Random data for templates
        invoice_num = f"{random.randint(1000, 9999)}"
        vendor = random.choice(self.config.vendors)
        well_name = random.choice(self.config.well_names)
        amount = f"{random.randint(100, 10000)}.{random.randint(0, 99):02d}"
        month = datetime.now().strftime("%B")
        year = datetime.now().year
        date = datetime.now().strftime("%Y-%m-%d")
        
        # Choose random templates
        subject_template = random.choice(self.config.subject_templates)
        body_template = random.choice(self.config.body_templates)
        
        # Format templates
        subject = subject_template.format(
            invoice_num=invoice_num,
            vendor=vendor,
            month=month,
            year=year,
            well_name=well_name
        )
        
        body = body_template.format(
            invoice_num=invoice_num,
            vendor=vendor,
            date=date,
            amount=amount,
            well_name=well_name
        )
        
        return {
            "subject": subject,
            "body": body,
            "invoice_num": invoice_num,
            "vendor": vendor,
            "well_name": well_name,
            "amount": amount,
            "pdf_file": str(pdf_file)
        }
    
    def log_email(self, email_data, status, error_msg=None):
        """Log email sending attempt"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "email_data": email_data,
            "error": error_msg
        }
        self.log_data.append(log_entry)
        
        # Write to log file
        with open(self.log_file, 'w') as f:
            json.dump(self.log_data, f, indent=2)
    
    def send_email(self, email_content, pdf_file):
        """Send a single email - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement send_email")
    
    def run_test(self):
        """Run the email test"""
        print(f"\n{'='*60}")
        print(f"Starting Email Test - {self.__class__.__name__}")
        print(f"{'='*60}")
        print(f"Batch Size: {self.config.batch_size}")
        print(f"Batch Delay: {self.config.batch_delay}s")
        print(f"Max Emails: {self.config.max_emails}")
        print(f"Log File: {self.log_file}")
        print(f"{'='*60}\n")
        
        # Get invoice files
        try:
            pdf_files = self.get_invoice_files()
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return
        
        # Send emails in batches
        email_index = 0
        batch_num = 0
        
        while email_index < min(self.config.max_emails, len(pdf_files) * 10):
            batch_num += 1
            batch_start = email_index
            batch_end = min(batch_start + self.config.batch_size, self.config.max_emails)
            
            print(f"\n--- Batch {batch_num} (Emails {batch_start + 1} to {batch_end}) ---")
            
            for i in range(batch_start, batch_end):
                # Select PDF file (cycle through if needed)
                pdf_file = pdf_files[i % len(pdf_files)]
                
                # Generate email content
                email_content = self.generate_email_content(pdf_file, i)
                
                print(f"\nEmail {i + 1}:")
                print(f"  Subject: {email_content['subject']}")
                print(f"  PDF: {pdf_file.name}")
                print("  Sending...", end="", flush=True)
                
                # Send email
                try:
                    self.send_email(email_content, pdf_file)
                    self.sent_count += 1
                    print(" ✓ Sent")
                    self.log_email(email_content, "sent")
                except Exception as e:
                    self.failed_count += 1
                    print(f" ✗ Failed: {str(e)}")
                    self.log_email(email_content, "failed", str(e))
                
                # Delay between emails
                if i < batch_end - 1:
                    time.sleep(self.config.email_delay)
                
                email_index += 1
            
            # Delay between batches
            if email_index < self.config.max_emails and email_index < len(pdf_files) * 10:
                print(f"\nWaiting {self.config.batch_delay}s before next batch...")
                time.sleep(self.config.batch_delay)
        
        # Print summary
        print(f"\n{'='*60}")
        print("Email Test Complete")
        print(f"{'='*60}")
        print(f"Total Sent: {self.sent_count}")
        print(f"Total Failed: {self.failed_count}")
        print(f"Success Rate: {(self.sent_count / (self.sent_count + self.failed_count) * 100):.1f}%")
        print(f"Log saved to: {self.log_file}")
        print(f"{'='*60}\n")

class GmailSender(EmailSender):
    """Send emails using Gmail SMTP"""
    
    def send_email(self, email_content, pdf_file):
        """Send email via Gmail"""
        msg = MIMEMultipart()
        msg['From'] = self.config.gmail_sender
        msg['To'] = self.config.gmail_recipient
        msg['Subject'] = email_content['subject']
        
        # Add body
        msg.attach(MIMEText(email_content['body'], 'plain'))
        
        # Add PDF attachment
        with open(pdf_file, 'rb') as f:
            part = MIMEBase('application', 'pdf')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{pdf_file.name}"'
            )
            msg.attach(part)
        
        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(self.config.gmail_sender, self.config.gmail_password)
            server.send_message(msg)

class OutlookSender(EmailSender):
    """Send emails using Outlook/Exchange"""
    
    def __init__(self, config: EmailConfig):
        super().__init__(config)
        if not OUTLOOK_AVAILABLE:
            raise ImportError("exchangelib is required for Outlook sending")
        
        # Connect to Outlook
        credentials = Credentials(
            username=self.config.outlook_sender,
            password=self.config.outlook_password
        )
        
        config_obj = Configuration(
            server=self.config.outlook_server,
            credentials=credentials
        )
        
        self.account = Account(
            primary_smtp_address=self.config.outlook_sender,
            config=config_obj,
            autodiscover=False,
            access_type=DELEGATE
        )
    
    def send_email(self, email_content, pdf_file):
        """Send email via Outlook"""
        # Create message
        msg = Message(
            account=self.account,
            subject=email_content['subject'],
            body=HTMLBody(email_content['body'].replace('\n', '<br>')),
            to_recipients=[self.config.outlook_recipient]
        )
        
        # Add attachment
        with open(pdf_file, 'rb') as f:
            content = f.read()
            attachment = FileAttachment(
                name=pdf_file.name,
                content=content
            )
            msg.attach(attachment)
        
        # Send
        msg.send()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Send test emails with invoice attachments')
    parser.add_argument('--method', choices=['gmail', 'outlook', 'both'], default='gmail',
                        help='Email sending method')
    parser.add_argument('--batch-size', type=int, help='Number of emails per batch')
    parser.add_argument('--batch-delay', type=int, help='Seconds between batches')
    parser.add_argument('--max-emails', type=int, help='Maximum emails to send')
    parser.add_argument('--invoice-folder', help='Folder containing invoice PDFs')
    parser.add_argument('--config-file', help='JSON config file to load')
    
    args = parser.parse_args()
    
    # Create config
    config = EmailConfig()
    
    # Load config from file if provided
    if args.config_file:
        with open(args.config_file, 'r') as f:
            config_data = json.load(f)
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    
    # Override with command line args
    if args.batch_size:
        config.batch_size = args.batch_size
    if args.batch_delay:
        config.batch_delay = args.batch_delay
    if args.max_emails:
        config.max_emails = args.max_emails
    if args.invoice_folder:
        config.invoice_folder = args.invoice_folder
    
    # Run tests based on method
    if args.method == 'gmail' or args.method == 'both':
        try:
            gmail_sender = GmailSender(config)
            gmail_sender.run_test()
        except Exception as e:
            print(f"Gmail test failed: {e}")
    
    if args.method == 'outlook' or args.method == 'both':
        try:
            outlook_sender = OutlookSender(config)
            outlook_sender.run_test()
        except Exception as e:
            print(f"Outlook test failed: {e}")

if __name__ == "__main__":
    main()
