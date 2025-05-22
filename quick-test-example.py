#!/usr/bin/env python3
"""
Quick test example - sends 5 test emails with invoices
"""

import os
import sys

# Check if invoice folder exists
if not os.path.exists("test_invoices"):
    print("Error: Please create a 'test_invoices' folder with PDF files")
    print("Example: mkdir test_invoices && cp *.pdf test_invoices/")
    sys.exit(1)

# Check for Gmail credentials
if not os.environ.get("TEST_GMAIL_SENDER") or not os.environ.get("TEST_GMAIL_PASSWORD"):
    print("Error: Please set Gmail credentials")
    print("export TEST_GMAIL_SENDER='your_email@gmail.com'")
    print("export TEST_GMAIL_PASSWORD='your_app_password'")
    sys.exit(1)

# Import and run the main script
try:
    from email_test_sender import EmailConfig, GmailSender
except ImportError:
    print("Error: email_test_sender.py not found in current directory")
    sys.exit(1)

# Configure for quick test
config = EmailConfig()
config.max_emails = 5  # Just send 5 emails
config.batch_size = 5  # All in one batch
config.batch_delay = 0  # No delay needed for single batch

print("Starting quick test - sending 5 emails with invoice attachments...")
print(f"From: {config.gmail_sender}")
print(f"To: {config.gmail_recipient}")
print("-" * 60)

# Run test
try:
    sender = GmailSender(config)
    sender.run_test()
    print("\nTest complete! Check the invoice processor to see if emails were received.")
except Exception as e:
    print(f"\nError during test: {e}")
    print("\nTroubleshooting:")
    print("1. Verify Gmail app password is correct")
    print("2. Check internet connection")
    print("3. Ensure 'test_invoices' folder contains PDF files")