# FullThumbs Tests

This directory contains unit tests for the FullThumbs application.

## Running Tests

### Run All Tests
```bash
# From project root
python run_tests.py

# Or with verbose output
python run_tests.py -v
```

### Run Individual Test Files
```bash
# From project root
python tests/test_time_parsing.py
python tests/test_argument_validation.py

# Or using module notation
python -m unittest tests.test_time_parsing -v
python -m unittest tests.test_argument_validation -v
```

### Run Specific Test Classes or Methods
```bash
# Run specific test class
python -m unittest tests.test_time_parsing.TestTimeIntervalParsing -v

# Run specific test method
python -m unittest tests.test_time_parsing.TestTimeIntervalParsing.test_multiple_units_supported -v
```

## Adding New Tests

When adding new functionality:
1. Add corresponding tests to appropriate test file
2. Use descriptive test method names
3. Include docstrings explaining what is being tested
4. Test both success and failure cases
5. Run all tests to ensure no regressions
