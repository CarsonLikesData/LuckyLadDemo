import json

def standardize_invoice(invoice):
    """Standardizes the invoice data."""

    new_invoice = {
        "Invoice Number": invoice.get("Invoice Number") or invoice.get("Invoice #") or invoice.get("Invoice"),
        "Invoice Date": invoice.get("Invoice Date") or invoice.get("Date"), "Due Date": invoice.get("Due Date"),
        "Bill To": {}}

    bill_to = invoice.get("Bill To") or invoice.get("Sold To") or invoice.get("Invoice To")
    if isinstance(bill_to, dict):
      new_invoice["Bill To"]["Customer Name"] = bill_to.get("Customer Name")
      new_invoice["Bill To"]["Customer Address"] = bill_to.get("Customer Address")
    elif isinstance(bill_to, str):
      new_invoice["Bill To"]["Customer Name"] = bill_to

    ship_to = invoice.get("Ship To")
    if ship_to:
      new_invoice["Ship To"] = {}
      if isinstance(ship_to, dict):
        new_invoice["Ship To"]["Customer Name"] = ship_to.get("Customer Name")
        new_invoice["Ship To"]["Customer Address"] = ship_to.get("Customer Address")
      elif isinstance(ship_to, str):
        new_invoice["Ship To"]["Customer Name"] = ship_to


    line_items = invoice.get("Line Items") or []
    if not line_items and invoice.get("Description"):
      line_items = [{"Description": invoice.get("Description")}]
    elif invoice.get("Descriptions"):
      line_items.extend([
          {k:v} for item in invoice.get("Descriptions", []) for k, v in item.items()
      ])
    if line_items:
      new_invoice["Line Items"] = line_items

    if "GALLONS" in invoice and "PRICE/GAL" in invoice and "AMOUNT" in invoice:
        new_invoice["Line Items"] = [{
            "Description": invoice.get("Description", "Propane"),
            "Quantity": invoice["GALLONS"],
            "Unit Price": invoice["PRICE/GAL"],
            "Total Price": invoice["AMOUNT"]
        }]


    for key in ["Customer ID", "Lease Name", "Well Name", "Property No", "AFE/PO No", "Area",
                "Service Date", "Order No", "Sales Person", "Amount Subject to Sales Tax",
                "Amount Exempt from Sales Tax", "Subtotal", "Invoice Discount", "Total Sales Tax",
                "Total", "P.O. No.", "Terms", "Rep", "Ship Date", "Via", "Unit No.", "Qty",
                "Price Each","Amount", "Sales Tax", "Payments/Credits", "Balance Due",
                "Order", "TOTAL", "Parish Tax", "State Tax", "Taxable", "Address", "FAX",
                "TOTAL PAYMENT DUE", "METHOD OF PAYMENT", "Tank Serial Number", "Tank Size",
                "Tank Percentage Before", "Tank Percentage After", "Start Pressure", "End Pressure",
                "Time Held", "Driver Initial", "Company Representative", "Remarks",
                "Customer Signature"]:
        if key in invoice:
            new_invoice[key] = invoice[key]

    return new_invoice


def create_jsonl(filename, data):
    """Creates a JSONL file from a list of dictionaries."""
    with open(filename, 'w') as f:
        for item in data:
            try:
                json_str = json.dumps(item)
                f.write(json_str + '\n')
            except TypeError as e:
                print(f"Error encoding item to JSON: {e}")
                print(f"Item: {item}")

    invoice_data_1 = {
        "Invoice Number": "INV734477",
        "Invoice Date": "4/11/2024",
        "Due Date": "5/11/2024",
        "Bill To": {
            "Customer Name": "Lucky Lad Energy LLC",
            "Customer Address": "PO Box 1379\nConroe, TX 77305\nUSA"
        },
        "Ship To": {
            "Customer Name": "Lucky Lad Energy LLC\nRichard Hopper",
            "Customer Address": "PO Box 1379\nConroe, TX 77305\nUSA"
        },
        "Customer ID": "LUCK001",
        "Lease Name": "Godchaux",
        "Well Name": "Godchaux 1",
        "Property No": None,
        "AFE/PO No": None,
        "Area": "Live Oak",
        "Service Date": "4/10/2024",
        "Order No": None,
        "Sales Person": "Justin Hebert",
        "Line Items": [
            {
                "Well Name": "Godchaux 1",
                "Item": "CS-1148",
                "Description": "Corr-Shield CS-1148",
                "Unit": "GAL",
                "Quantity": 75,
                "Unit Price": 7.15,
                "Total Price": 536.25
            },
            {
                "Well Name": "Godchaux 1",
                "Item": "SS-728",
                "Description": "SCALE-SHIELD SS-728",
                "Unit": "GAL",
                "Quantity": 75,
                "Unit Price": 5.70,
                "Total Price": 427.50
            },
            {
                "Well Name": "Godchaux 1",
                "Item": "METHANOL",
                "Description": "Methanol",
                "Unit": "GAL",
                "Quantity": 100,
                "Unit Price": 2.20,
                "Total Price": 220.00
            },
            {
                "Well Name": "Godchaux 3",
                "Item": "SC-1331",
                "Description": "SC-SHIELD SC-1331",
                "Unit": "GAL",
                "Quantity": 110,
                "Unit Price": 8.15,
                "Total Price": 896.50
            },
            {
                "Well Name": "Godchaux 3",
                "Item": "METHANOL",
                "Description": "Methanol",
                "Unit": "GAL",
                "Quantity": 75,
                "Unit Price": 2.20,
                "Total Price": 165.00
            },
            {
                "Well Name": "Godchaux 3",
                "Item": "PS-653M",
                "Description": "Phase Shield PS-653M",
                "Unit": "GAL",
                "Quantity": 50,
                "Unit Price": 18.80,
                "Total Price": 940.00
            },
            {
                "Well Name": "Godchaux 5 SWD",
                "Item": "DS-129",
                "Description": "D-SHIELD DS-129",
                "Unit": "GAL",
                "Quantity": 120,
                "Unit Price": 11.90,
                "Total Price": 1428.00
            }
        ],
        "Amount Subject to Sales Tax": 4613.25,
        "Amount Exempt from Sales Tax": 0.00,
        "Subtotal": 4613.25,
        "Invoice Discount": 0.00,
        "Total Sales Tax": 378.29,
        "Total": 4991.54
    }

    invoice_data_2 = {
        "Date": "11/12/2024",
        "Invoice #": "1124132",
        "Bill To": "Lucky Lad Energy\nP.O. Box 1379\nConroe, TX 77305",
        "Ship To": "Lucky Lad Energy\nKirby McInnis Tank Battery",
        "P.O. No.": None,
        "Terms": "Net 30",
        "Rep": "CTH",
        "Ship Date": "11/12/2024",
        "Via": "Our Truck",
        "Unit No.": "9856",
        "Qty": 55,
        "Description": "Gallons of OLA-905 (Oil - Low Ash)",
        "Price Each": 15.75,
        "Amount": 866.25,
        "Subtotal": 866.25,
        "Sales Tax": 71.47,
        "Total": 937.72,
        "Payments/Credits": None,
        "Balance Due": 937.72
    }

    invoice_data_3 = {
        "Description": "Rcvd\n\n\nBy\n\n\n:\n\n\nBy\n\n\nOrd'd\n\n\nRomero\n\n\nMr\n\n\nDexter\n\n\nShop\n\n\n \n\n\n/\n\n\nLaf\n\n\nParish\n\n\nField\n\n\nLive\n\n\nOak\n\n\nCharge\n\n\nGodchaux\n\n\n#\n\n\n3\n",
        "Order": None,
        "Date": "6/26/24",
        "Invoice To": "Lucky Lad (invoice@luckylad.com)",
        "Ship To": None,
        "TOTAL": 827.19,
        "Descriptions": [
            {"Seats 1153": 762.74},
            {"Seats 1152 Darts": 16.54},
            {"1307 Assy Rod": 33.08},
            {"Piston 779A": 14.11},
            {"Cylinder 764": 28.22},
            {"Kit 4015 Viton": 45.88},
            {"Repair Materials": 11.47},
            {"Pump Glycol": 156.69},
            {"Kimray - 4015 repair, test, paint and check": 196.29},
            {"5 Hrs Labor @ Shop charges to clean": 92.58},
            {"Ths From Originated Invoice 013797 DT #": 42.00},
            {"TOTAL": 210.00}
        ],
        "Parish Tax": 30.51,
        "State Tax": 33.94,
        "Taxable": None
    }

    invoice_data_4 = {
        "Date": "1-2-24",
        "Sold To": "Lucky Lad Energy",
        "Address": "Temple 26-2 514 232598",
        "GALLONS": 420,
        "PRICE/GAL": 2.97,
        "AMOUNT": 1247.40,
        "FAX": 84.20,
        "TOTAL PAYMENT DUE": 1331.60,
        "METHOD OF PAYMENT": "CHARGE",
        "Tank Serial Number": None,
        "Tank Size": 320,
        "Tank Percentage Before": 5,
        "Tank Percentage After": 16,
        "Start Pressure": 48,
        "End Pressure": 86,
        "Time Held": None,
        "Driver Initial": "Louis",
        "Company Representative": "X",
        "Remarks": "Performed a leak test of the propane system to insure it is leak free",
        "Customer Signature": "X",
        "Invoice #": "101891",
    }

    statement_data_1 = {
        "Date": "1/5/2024",
        "To": "LUCKY LAD ENERGY LLC\nPO BOX 1379\nCONROE, TX 77305-1379",
        "Amount Due": 25152.43,
        "Amount Enc.": None,
        "Transactions": [
            {
                "Date": "09/20/2023",
                "Transaction": "INV #6378. Due 10/20/2023. Orig. Amount $562.20.",
                "Amount": 562.20,
                "Balance": 562.20
            },
            {
                "Date": "09/26/2023",
                "Transaction": "INV #6522. Due 10/26/2023. Orig. Amount $1,451.02.",
                "Amount": 1451.02,
                "Balance": 2013.22
            },
            {
                "Date": "11/30/2023",
                "Transaction": "GENJRNL #23-09-44R. Reverse of GJE 23-09-44- Transfer of Credits for LUCKY LAD ENERGY LLC from LUCKY LAD ENERGY LLC to 10032",
                "Amount": -1708.00,
                "Balance": 305.22
            },
             {
                "Date": "11/30/2023",
                "Transaction": "Theuvenins Creek\nGENJRNL #23-09-46R. Reverse of GJE 23-09-46 Transfer of Credits for LUCKY LAD ENERGY LLC from LUCKY LAD ENERGY LLC to 10032 Theuvenins Creek",
                "Amount": -170.00,
                "Balance": 135.22
            },
            {
                "Date": "12/26/2023",
                "Transaction": "INV #8600. Due 01/25/2024. Orig. Amount $665.12.",
                "Amount": 665.12,
                "Balance": 800.34
            },
            {
                "Date": "11/01/2023",
                "Transaction": "INV #99056445. Due 11/01/2023. Orig. Amount $1,878.80.",
                "Amount": 1878.80,
                "Balance": 2679.14
            },
            {
                "Date": "12/01/2023",
                "Transaction": "INV #99056973. Due 12/01/2023. Orig. Amount $1,878.80.",
                "Amount": 1878.80,
                "Balance": 4557.94
            },
            {
                "Date": "01/01/2024",
                "Transaction": "INV #99057514. Due 01/01/2024. Orig. Amount $1,878.80.",
                "Amount": 1878.80,
                "Balance": 6436.74
            },
            {
                "Date": "10/01/2023",
                "Transaction": "INV #99055894. Due 10/01/2023. Orig. Amount $3,757.60.",
                "Amount": 3757.60,
                "Balance": 10194.34
            },
            {
                "Date": "11/01/2023",
                "Transaction": "INV #99056447. Due 11/01/2023. Orig. Amount $1,878.80.",
                "Amount": 1878.80,
                "Balance": 12073.14
            },
            {
                "Date": "12/01/2023",
                "Transaction": "INV #99056975. Due 12/01/2023. Orig. Amount $1,878.80.",
                "Amount": 1878.80,
                "Balance": 13951.94
            },
            {
                "Date": "01/01/2024",
                "Transaction": "INV #99057516. Due 01/01/2024. Orig. Amount $1,878.80. 10083 DUPLANTIER ESTATE #2-",
                "Amount": 1878.80,
                "Balance": 15830.74
            },
            {
                "Date": "01/01/2024",
                "Transaction": "INV #99057612. Due 01/01/2024. Orig. Amount $1,374.38. 10084 DREYFUS MINERALS #1-",
                "Amount": 1374.38,
                "Balance": 17205.12
            },
            {
                "Date": "01/01/2024",
                "Transaction": "INV #99057613. Due 01/01/2024. Orig. Amount $1,464.08. 10085 DREYFUS MINERALS #2 ALT-",
                "Amount": 1464.08,
                "Balance": 18669.20
            },
            {
                "Date": "01/01/2024",
                "Transaction": "INV #99057614. Due 01/01/2024. Orig. Amount $1,355.63. 10086 JOHNSON BAYOU-",
                "Amount": 1355.63,
                "Balance": 20024.83
            },
             {
                "Date": "01/01/2024",
                "Transaction": "INV #99057517. Due 01/01/2024. Orig. Amount $2,506.80. 10087 GORDON-",
                "Amount": 2506.80,
                "Balance": 22531.63
            },
            {
                "Date": "01/01/2024",
                "Transaction": "INV #99057518. Due 01/01/2024. Orig. Amount $2,620.80.",
                "Amount": 2620.80,
                "Balance": 25152.43
            }

        ],
        "CURRENT": 665.12,
        "1-30 DAYS PAST DUE": 13079.29,
        "31-60 DAYS PAST DUE": 3757.60,
        "61-90 DAYS PAST DUE": 5770.82,
        "OVER 90 DAYS PAST DUE": 1879.60
    }

    # Create examples list
    example = [
        {
            "prompt": f"""
            Data:
            {json.dumps(invoice_data_1)}

            Validation Instructions:
            1.  **Data Completeness & Presence:**
                Verify presence of: Invoice Number, Invoice Date, Due Date, Bill To, Ship To, Item Details (Description, Qty, Unit, Price, Total). Note missing general & Oil/Gas fields (Customer ID, Lease, Well, Property No., AFE/PO, Area).

            2.  **Numerical & Date Validation:**
                Validate:
                    -   Numerical fields (Qty, Price, Totals, Subtotal, Tax, Amount Due) are numeric.
                    -   Qty * Unit = Total for each item.
                    -   Sum of item totals + tax = Amount Due.
                    -   Dates (Invoice, Due, Service) are valid and logically consistent (Due >= Invoice).

            3.  **Consistency & Oil/Gas Validation:**
                Check:
                    -   Bill To vs. Ship To consistency.
                    -   Units of measurement consistency.
                    -   Oil/Gas fields (if present): Logical relationships (Lease/Well), expected formats (Property No., AFE/PO), valid Area (if possible).
            """,
            "response": """
            File: INV734477.pdf
            Completeness: All fields present. Oil and Gas specific fields: Customer ID, Lease Name, Well Name, and Area are present. Property No. and AFE/PO No. are missing.
            Numeric/Date:
                Qty*Price=Total: OK.
                Amount Due Calc: OK.
                Dates: Valid/Consistent.
            Consistency/Oil/Gas:
                Bill To/Ship To: Inconsistent (Richard Hopper).
                Units: OK.
                Oil/Gas: Lease/Well logical. Area: OK.
            """
        },
        {
            "prompt": f"""
                Data:
                {json.dumps(invoice_data_2)}

                Validation Instructions:
                1.  **Data Completeness & Presence:**
                    Verify presence of: Invoice Number, Invoice Date, Due Date, Bill To, Ship To, Item Details (Description, Qty, Unit, Price, Total). Note missing general & Oil/Gas fields (Customer ID, Lease, Well, Property No., AFE/PO, Area).

                2.  **Numerical & Date Validation:**
                    Validate:
                        -   Numerical fields (Qty, Price, Totals, Subtotal, Tax, Amount Due) are numeric.
                        -   Qty * Unit = Total for each item.
                        -   Sum of item totals + tax = Amount Due.
                        -   Dates (Invoice, Due, Service) are valid and logically consistent (Due >= Invoice).

                3.  **Consistency & Oil/Gas Validation:**
                    Check:
                        -   Bill To vs. Ship To consistency.
                        -   Units of measurement consistency.
                        -   Oil/Gas fields (if present): Logical relationships (Lease/Well), expected formats (Property No., AFE/PO), valid Area (if possible).
                """,
            "response": """
                File: 1124132[90].pdf
                Completeness:  All required fields are present.
                Numeric/Date:
                    Qty*Price=Total: OK.
                    Amount Due Calc: OK.
                    Dates: Valid/Consistent.
                Consistency/Oil/Gas:
                    Bill To vs. Ship To:  No inconsistencies found.
                    Units: OK.
                    Oil/Gas: No Oil and Gas fields.
                """
        },
        {
            "prompt": f"""
                Data:
                {json.dumps(invoice_data_3)}

                Validation Instructions:
                1.  **Data Completeness & Presence:**
                    Verify presence of: Invoice Number, Invoice Date, Due Date, Bill To, Ship To, Item Details (Description, Qty, Unit, Price, Total). Note missing general & Oil/Gas fields (Customer ID, Lease, Well, Property No., AFE/PO, Area).

                2.  **Numerical & Date Validation:**
                    Validate:
                        -   Numerical fields (Qty, Price, Totals, Subtotal, Tax, Amount Due) are numeric.
                        -   Qty * Unit = Total for each item.
                        -   Sum of item totals + tax = Amount Due.
                        -   Dates (Invoice, Due, Service) are valid and logically consistent (Due >= Invoice).

                3.  **Consistency & Oil/Gas Validation:**
                    Check:
                        -   Bill To vs. Ship To consistency.
                        -   Units of measurement consistency.
                        -   Oil/Gas fields (if present): Logical relationships (Lease/Well), expected formats (Property No., AFE/PO), valid Area (if possible).
                """,
            "response": """
                File: 20240701_112438.PDF
                Completeness:  All required fields are present.
                Numeric/Date:
                    Item prices and total calculations: OK.
                    Tax and total calculations: OK.
                    Dates: Valid/Consistent.
                Consistency/Oil/Gas:
                    Bill To vs. Ship To:  No inconsistencies found.
                    Units: OK.
                    Oil/Gas:  Area present.
                """
        },
        {
            "prompt": f"""
                Data:
                {json.dumps(invoice_data_4)}

                Validation Instructions:
                1.  **Data Completeness & Presence:**
                    Verify presence of: Invoice Number, Invoice Date, Due Date, Bill To, Ship To, Item Details (Description, Qty, Unit, Price, Total). Note missing general & Oil/Gas fields (Customer ID, Lease, Well, Property No., AFE/PO, Area).

                2.  **Numerical & Date Validation:**
                    Validate:
                        -   Numerical fields (Qty, Price, Totals, Subtotal, Tax, Amount Due) are numeric.
                        -   Qty * Unit = Total for each item.
                        -   Sum of item totals + tax = Amount Due.
                        -   Dates (Invoice, Due, Service) are valid and logically consistent (Due >= Invoice).

                3.  **Consistency & Oil/Gas Validation:**
                    Check:
                        -   Bill To vs. Ship To consistency.
                        -   Units of measurement consistency.
                        -   Oil/Gas fields (if present): Logical relationships (Lease/Well), expected formats (Property No., AFE/PO), valid Area (if possible).
                """,
            "response": """
                File: ATKINSON PROPANE CO. INC.pdf
                Completeness:  All required fields are present.
                Numeric/Date:
                    Item prices and total calculations: OK.
                    Tax and total calculations: OK.
                    Dates: Valid/Consistent.
                Consistency/Oil/Gas:
                    Bill To vs. Ship To:  No inconsistencies found.
                    Units: OK.
                    Oil/Gas: No Oil and Gas fields.
                """
        },
        {
            "prompt": f"""
            Data:
            {json.dumps(statement_data_1)}

            Validation Instructions:
            1.  **Data Completeness & Presence:**
                Verify presence of: Statement Date, Customer, Address, Amount Due, Transaction Details (Date, Description, Amount, Balance). Note any Oil/Gas identifiers in transaction descriptions.

            2.  **Numerical & Date Validation:**
                Validate:
                    -   Amount Due, Transaction Amounts, and Balances are numeric.
                    -   Transaction Dates are valid.
                    -   Balance calculations are correct (previous balance + current transaction amount = current balance).

            3.  **Aging & Oil/Gas Validation:**
                Check:
                    -   If present, Aging Summary amounts are numeric and sum to Amount Due.
                    -   Flag any Oil/Gas identifiers in transaction descriptions for review.
            """,
            "response": """
            File: Statement1_from_REAGAN_POWER_COMPRESSION_LLC15308.pdf
            Completeness: All fields present.
            Numeric/Date:
                Amounts/Balances: OK.
                Dates: Valid.
                Balance Calc: OK.
            Aging/Oil/Gas:
                Aging: OK.
                Oil/Gas: Identifiers in transactions (Theuvenins Creek, etc.) - Review.
            """
        }
    ]

    create_jsonl("validation_json.jsonl",example)
    print(f"JSONL file 'validation_data.jsonl' created successfully.")