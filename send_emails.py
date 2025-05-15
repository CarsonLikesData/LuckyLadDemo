# Import necessary libraries for email handling and SMTP
import smtplib
import time
import os # Used for file/folder operations
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import sys # Used for exiting gracefully

# --- Configuration ---
# --- IMPORTANT: Fill in your details below ---
sender_email = "carson.virden@gmail.com" # Your Gmail address (the one you generated the App Password for)
# --- Use the 16-digit App Password generated in your Google Account Security settings ---
# --- DO NOT use your regular Google password ---
sender_password = "qelm jufn wcrj mlyq" # Replace with your actual 16-digit App Password
receiver_email = "dft.luckylad.test@gmail.com"    # The target Gmail inbox for the demo

# --- Folder containing the PDF invoices ---
pdf_folder_path = "C:\\Users\\carso\\work_projects\\lucky_lad\\ML_Tests_Invoice_Gen\\synthetic_invoices" # IMPORTANT: Replace with the actual path to your PDF folder

# Gmail SMTP Server Details
smtp_server = "smtp.gmail.com"
smtp_port = 587 # Port for TLS/STARTTLS

# Script Settings
num_emails_limit = 10 # Maximum number of emails to send (script will stop if it runs out of PDFs first)


# --- Validate PDF Folder Path ---
if not os.path.isdir(pdf_folder_path):
    print(f"Error: The specified PDF folder does not exist or is not a directory:")
    print(f"'{pdf_folder_path}'")
    print("Please check the 'pdf_folder_path' variable in the script.")
    sys.exit(1) # Exit the script

# --- Get List of PDF Files ---
pdf_files = []
try:
    print(f"Scanning folder for PDF files: {pdf_folder_path}")
    for filename in os.listdir(pdf_folder_path):
        if filename.lower().endswith(".pdf"):
            pdf_files.append(filename)
except OSError as e:
    print(f"Error reading PDF folder: {e}")
    sys.exit(1)

if not pdf_files:
    print(f"No PDF files found in the specified folder: {pdf_folder_path}")
    sys.exit(0) # Exit gracefully if no PDFs are found

print(f"Found {len(pdf_files)} PDF file(s).")
# Determine how many emails to actually send
num_emails_to_send = min(len(pdf_files), num_emails_limit)
print(f"Will send up to {num_emails_to_send} emails (limited by found PDFs or num_emails_limit).")


# --- SMTP Connection and Sending Loop ---
server = None # Initialize server variable
emails_sent_count = 0
print(f"\nAttempting to connect to {smtp_server} on port {smtp_port}...")
try:
    # Establish connection to the Gmail SMTP server
    server = smtplib.SMTP(smtp_server, smtp_port)
    # Secure the connection using TLS (Transport Layer Security)
    server.starttls()
    print("Connection secured with TLS.")

    # Log in to the sender's Gmail account using the App Password
    print(f"Logging in as {sender_email}...")
    server.login(sender_email, sender_password)
    print("SMTP Login successful.")

    # Loop through the found PDF files (up to the limit)
    for i, pdf_filename in enumerate(pdf_files):
        # Stop if we've reached the email limit
        if i >= num_emails_limit:
            print(f"\nReached email limit ({num_emails_limit}). Stopping.")
            break

        current_email_num = i + 1
        print(f"\nPreparing email {current_email_num}/{num_emails_to_send} using '{pdf_filename}'...")

        # Construct the full path to the current PDF file
        full_pdf_path = os.path.join(pdf_folder_path, pdf_filename)

        # Create the email message container (MIMEMultipart)
        msg = MIMEMultipart()
        # Set email headers (Sender, Recipient, Subject)
        # You might want to customize the subject/body based on the filename if needed
        msg['From'] = f"Invoice Dept <{sender_email}>" # Example sender name
        msg['To'] = receiver_email
        # Use PDF filename (without extension) in subject for uniqueness
        invoice_id = os.path.splitext(pdf_filename)[0]
        msg['Subject'] = f"Invoice Attached: {invoice_id}"

        # Create the email body text
        body = f"Dear Customer,\n\nPlease find your invoice '{invoice_id}' attached.\n\nThank you for your business.\n\nBest regards,\nYour Company"
        # Attach the body text to the email message
        msg.attach(MIMEText(body, 'plain'))

        # --- Attach the actual PDF invoice file ---
        try:
            # Open the attachment file in binary read mode
            with open(full_pdf_path, "rb") as attachment:
                # Create a MIMEBase object for the attachment
                # Use 'application/pdf' for PDF files
                part = MIMEBase("application", "pdf")
                # Load the attachment content into the MIMEBase object
                part.set_payload(attachment.read())

            # Encode the attachment content in base64
            encoders.encode_base64(part)

            # Add a header to specify the filename for the attachment in the email
            # Use the original PDF filename
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {pdf_filename}", # Use the actual filename
            )

            # Attach the encoded part (the file) to the main message
            msg.attach(part)
            print(f"Attached file: {pdf_filename}")

        except FileNotFoundError:
            print(f"Error: Attachment file '{full_pdf_path}' not found (should not happen based on earlier check).")
            continue # Skip sending this email
        except IOError as e:
            print(f"Error reading attachment file '{full_pdf_path}': {e}")
            continue # Skip sending this email
        except Exception as e:
            print(f"Error attaching file '{pdf_filename}': {e}")
            continue # Skip sending this email
        # --- End Attachment ---

        # Convert the complete message object to a string
        text = msg.as_string()

        # Send the email
        print(f"Sending email to {receiver_email}...")
        server.sendmail(sender_email, receiver_email, text)
        emails_sent_count += 1
        print(f"Email {current_email_num}/{num_emails_to_send} sent successfully.")

        # --- Wait before sending the next email ---
        # IMPORTANT: Helps avoid hitting Gmail's sending rate limits and spam filters.
        delay = 2 # seconds (increase if needed)
        print(f"Waiting for {delay} seconds...")
        time.sleep(delay)

except smtplib.SMTPAuthenticationError:
    print("\n--- SMTP Authentication Error ---")
    print("Login failed. Please check:")
    print("1. Your 'sender_email' is correct.")
    print("2. You are using a correctly generated 16-digit App Password in 'sender_password'.")
    print("3. 2-Step Verification is enabled for the sending Gmail account.")
    print("4. The App Password has not been revoked.")
except smtplib.SMTPConnectError:
    print("\n--- SMTP Connection Error ---")
    print(f"Could not connect to the server {smtp_server} on port {smtp_port}.")
    print("Check your internet connection and firewall settings.")
except Exception as e:
    # Catch any other unexpected errors during the process
    print(f"\n--- An unexpected error occurred ---")
    print(f"Error details: {e}")
finally:
    # --- Clean up ---
    # Ensure the connection to the SMTP server is closed, regardless of success or failure
    if server:
        try:
            server.quit()
            print("\nSMTP connection closed.")
        except Exception as e:
            print(f"Error closing SMTP connection: {e}")

print(f"\nScript finished. Total emails sent: {emails_sent_count}")
