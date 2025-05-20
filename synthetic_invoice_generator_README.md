# Synthetic Invoice Generator for Lucky Lad Energy

A Python-based tool to generate realistic oil & gas invoices for training and testing purposes.

## Overview

This generator creates synthetic invoices that mimic the structure and appearance of real invoices from vendors like Reagan Power, Aegis Chemical, and Atkinson Propane. It's designed to produce training data for document AI systems and testing data for invoice processing applications.

## Features

- **Multiple Invoice Templates**: Supports Reagan Power, Aegis Chemical, and Atkinson Propane invoice formats
- **Realistic Data Generation**: Uses Faker with custom oil & gas industry providers
- **PDF Generation**: Creates professional-looking PDF invoices using ReportLab
- **Image Degradation**: Applies realistic degradation effects to mimic scanned documents
- **Data Validation**: Ensures generated invoices have correct calculations and valid data
- **JSON Export**: Exports invoice data in JSON format for Document AI training

## Requirements

- Python 3.10+
- Dependencies:
  - `Faker` (data generation)
  - `Jinja2` (templates)
  - `ReportLab` (PDF rendering)
  - `Pillow`/`numpy` (image degradation)
  - `Pydantic` (validation)
  - `pdf2image` (PDF to image conversion, requires poppler)

## Installation

1. Clone the repository
2. Install required packages:
   ```
   pip install -r synthetic_invoice_requirements.txt
   ```
3. Install poppler (required for pdf2image):
   - Windows: Download from [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/)
   - macOS: `brew install poppler`
   - Linux: `apt-get install poppler-utils`

## Usage

### Basic Usage

Generate 10 synthetic invoices with default settings:

```bash
python synthetic_invoice_generator.py
```

### Command Line Options

- `--count`: Number of invoices to generate (default: 10)
- `--no-degradation`: Skip image degradation
- `--validate`: Validate generated invoices

Example:

```bash
python synthetic_invoice_generator.py --count 20 --validate
```

### Using as a Library

```python
from synthetic_invoice_generator import generate_synthetic_invoices

# Generate 5 invoices with degradation
generated_files = generate_synthetic_invoices(count=5, include_degradation=True)

# Process the generated files
for json_path, pdf_path in generated_files:
    print(f"Generated: {json_path} and {pdf_path}")
```

## Output

Generated files are saved to:
- JSON files: `synthetic_invoices/json/`
- PDF files: `synthetic_invoices/pdf/`

## Testing

Run the test suite to verify the generator is working correctly:

```bash
python test_synthetic_invoices.py
```

## Customization

### Adding New Templates

1. Define a new Jinja2 template string in the `# ===== Template Definitions =====` section
2. Add a new case in the `generate_invoice_data()` function
3. Add a new case in the `create_invoice_pdf()` function
4. Update the `generate_invoice_json()` function to use the new template

### Customizing Data Generation

Modify the `OilGasProvider` class to add or change the data generation patterns.

## Integration with Lucky Lad Invoice Processor

This synthetic invoice generator complements the Lucky Lad Invoice Processor by providing training and testing data. The generated invoices can be used to:

1. Train Document AI models
2. Test extraction accuracy
3. Validate processing logic
4. Benchmark system performance

## License

[Specify your license here]