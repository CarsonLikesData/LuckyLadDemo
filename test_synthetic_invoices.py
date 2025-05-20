"""
Test script for the synthetic invoice generator
"""

import os
import json
import unittest
from synthetic_invoice_generator import (
    generate_invoice_data, 
    generate_statement_data,
    generate_invoice_json,
    generate_statement_json,
    validate_invoices
)

class TestSyntheticInvoiceGenerator(unittest.TestCase):
    
    def setUp(self):
        # Create test directories if they don't exist
        os.makedirs('test_output/json', exist_ok=True)
        os.makedirs('test_output/pdf', exist_ok=True)
    
    def test_invoice_data_generation(self):
        """Test that invoice data is generated correctly"""
        # Test each template type
        for template_type in ["aegis", "reagan", "atkinson"]:
            invoice_data = generate_invoice_data(template_type)
            
            # Basic validation
            self.assertIsNotNone(invoice_data)
            self.assertIsNotNone(invoice_data.invoice_number)
            self.assertIsNotNone(invoice_data.invoice_date)
            self.assertIsNotNone(invoice_data.bill_to)
            self.assertIsNotNone(invoice_data.line_items)
            self.assertTrue(len(invoice_data.line_items) > 0)
            
            # Check template-specific fields
            if template_type == "atkinson":
                self.assertIsNotNone(getattr(invoice_data, 'tank_serial_number', None))
                self.assertIsNotNone(getattr(invoice_data, 'tank_size', None))
                self.assertIsNotNone(getattr(invoice_data, 'before_percentage', None))
                self.assertIsNotNone(getattr(invoice_data, 'after_percentage', None))
    
    def test_statement_data_generation(self):
        """Test that statement data is generated correctly"""
        statement_data = generate_statement_data()
        
        # Basic validation
        self.assertIsNotNone(statement_data)
        self.assertIsNotNone(statement_data.statement_date)
        self.assertIsNotNone(statement_data.to)
        self.assertIsNotNone(statement_data.transactions)
        self.assertTrue(len(statement_data.transactions) > 0)
    
    def test_invoice_json_generation(self):
        """Test that invoice JSON is generated correctly"""
        # Test each template type
        for template_type in ["aegis", "reagan", "atkinson"]:
            json_content, invoice_data = generate_invoice_json(template_type)
            
            # Basic validation
            self.assertIsNotNone(json_content)
            self.assertTrue(len(json_content) > 0)
            
            # Verify it's valid JSON
            try:
                parsed_json = json.loads(json_content)
                self.assertIsInstance(parsed_json, dict)
            except json.JSONDecodeError:
                self.fail(f"Invalid JSON generated for {template_type}")
    
    def test_statement_json_generation(self):
        """Test that statement JSON is generated correctly"""
        json_content, statement_data = generate_statement_json()
        
        # Basic validation
        self.assertIsNotNone(json_content)
        self.assertTrue(len(json_content) > 0)
        
        # Verify it's valid JSON
        try:
            parsed_json = json.loads(json_content)
            self.assertIsInstance(parsed_json, dict)
        except json.JSONDecodeError:
            self.fail("Invalid JSON generated for statement")
    
    def test_invoice_validation(self):
        """Test that invoice validation works correctly"""
        # Generate test files
        test_files = []
        
        # Generate one of each type
        for template_type in ["aegis", "reagan", "atkinson"]:
            json_content, _ = generate_invoice_json(template_type)
            
            # Save JSON to test file
            json_path = f"test_output/json/test_{template_type}.json"
            with open(json_path, 'w') as f:
                f.write(json_content)
            
            # Create a dummy PDF path (validation doesn't actually use the PDF)
            pdf_path = f"test_output/pdf/test_{template_type}.pdf"
            
            test_files.append((json_path, pdf_path))
        
        # Validate the files
        validation_results = validate_invoices(test_files)
        
        # Check validation results
        self.assertEqual(len(validation_results), len(test_files))
        
        for result in validation_results:
            self.assertTrue(result["valid"], f"Validation failed for {result['file']}: {result['errors']}")

if __name__ == "__main__":
    unittest.main()