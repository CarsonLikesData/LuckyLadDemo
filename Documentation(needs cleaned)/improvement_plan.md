# Unit Price Validation Improvement Plan

## Code Changes Needed
```python
# Updated validator in synthetic_invoice_generator.py:218-228
@validator("unit_price")
def validate_unit_price(cls, v: Union[str, float, int]) -> float:
    """Validates and normalizes unit_price values. Handles:
    - String/numeric inputs
    - Comma separation
    - Negative values
    - Detailed error reporting"""
    # Implementation details...
```

## Required Test Cases
```python
# New tests in test_synthetic_invoices.py
class TestUnitPriceValidation(unittest.TestCase):
    def test_valid_formats(self): ...
    def test_invalid_formats(self): ...
    def test_negative_values(self): ...
```

## Implementation Steps
1. Create validation tests first (test-driven approach)
2. Update validator with enhanced logic
3. Ensure error message consistency
4. Update documentation