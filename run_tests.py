#!/usr/bin/env python3
"""
Test runner for FullThumbs application.

This script runs all unit tests for the FullThumbs application.
Use this script to run all tests or specific test modules.

Usage:
    python run_tests.py                           # Run all tests
    python run_tests.py tests.test_time_parsing   # Run specific test module
    python run_tests.py -v                        # Run with verbose output
"""

import sys, os, unittest

def main():
    """Run the test suite."""
    # Add the project root to the path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    # Check if specific test modules are requested
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        # Run specific test modules
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        for module_name in sys.argv[1:]:
            if not module_name.startswith('-'):
                try:
                    module_suite = loader.loadTestsFromName(module_name)
                    suite.addTest(module_suite)
                except (ImportError, AttributeError) as e:
                    print(f"Error loading test module '{module_name}': {e}")
                    return 1
    else:
        # Discover and run all tests in the tests directory
        loader = unittest.TestLoader()
        tests_dir = os.path.join(project_root, 'tests')
        suite = loader.discover(tests_dir, pattern='test_*.py')
    
    # Determine verbosity
    verbosity = 2 if '-v' in sys.argv or '--verbose' in sys.argv else 1
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Return appropriate exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(main())
