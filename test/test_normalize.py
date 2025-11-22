#!/usr/bin/env python3
"""
Test script for text normalization system.
Tests cardinal numbers from 0 to 1000 in both English and French.
Uses FAR archive for FST loading.
"""

import sys
import os
import argparse
from typing import List, Tuple
import pynini
from pathlib import Path

# Default FAR archive path
DEFAULT_FAR_PATH = "../Far/my_normalized_language.far"

# Global FST variables
english_fst = None
french_fst = None


def load_fsts_from_far(far_path: str = DEFAULT_FAR_PATH):
    """
    Load the English and French FSTs from the FAR archive.
    
    Args:
        far_path: Path to the FAR archive file
    
    Returns:
        Tuple of (english_fst, french_fst) or exits on error
    """
    global english_fst, french_fst
    
    if not Path(far_path).exists():
        print(f"Error: FAR archive not found at '{far_path}'", file=sys.stderr)
        print(f"Please run: python build_fst.py --output {far_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Open the FAR archive for reading
        far = pynini.Far(far_path, mode='r')
        
        # Load the FSTs
        english_fst = far['english']
        french_fst = far['french']
        
        print(f"✓ FSTs loaded successfully from '{far_path}'", file=sys.stderr)
        return english_fst, french_fst
        
    except KeyError as e:
        print(f"Error: FST key not found in archive: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error loading FAR archive: {e}", file=sys.stderr)
        sys.exit(1)


def apply_fst(text, fst):
    """Applies an FST to a string and returns the result."""
    try:
        result = pynini.shortestpath(
            pynini.accep(text, token_type='utf8') @ fst
        ).string("utf8")
        return result
    except:
        # If FST fails, return original text
        return text


def normalize_number(num_str, language='english'):
    """
    Normalize a single number string to words.
    Only handles numbers from 0 to 1000.
    Returns "OUT_OF_BOUND" for numbers outside this range.
    """
    # Clean the number string - remove commas, spaces
    clean_num = num_str.strip().replace(',', '').replace(' ', '')
    
    # Handle negative numbers - out of bound
    if clean_num.startswith('-'):
        return "OUT_OF_BOUND"
    
    # Check if it's a valid number
    if not clean_num.isdigit():
        return "OUT_OF_BOUND"
    
    # Convert to integer to check bounds
    try:
        num_value = int(clean_num)
    except ValueError:
        return "OUT_OF_BOUND"
    
    # Check if within bounds (0-1000)
    if num_value < 0 or num_value > 1000:
        return "OUT_OF_BOUND"
    
    # Use the appropriate FST
    fst = french_fst if language == 'french' else english_fst
    
    # Apply FST to convert number to words
    result = apply_fst(str(num_value), fst)
    
    # If FST failed to convert, return OUT_OF_BOUND
    if result == str(num_value):
        return "OUT_OF_BOUND"
    
    return result


def load_test_file(filepath: str) -> List[Tuple[str, str]]:
    """
    Load test cases from a file.
    Expected format: each line contains "input<SEPARATOR>expected_output"
    Supports separators: ~ (tilde), tab, or comma
    
    Returns:
        List of (input, expected_output) tuples
    """
    test_cases = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Try different separators: tilde, tab, then comma
                if '~' in line:
                    parts = line.split('~', 1)
                elif '\t' in line:
                    parts = line.split('\t', 1)
                elif ',' in line:
                    parts = line.split(',', 1)
                else:
                    print(f"Warning: Line {line_num} has invalid format (no separator found): {line}", file=sys.stderr)
                    continue
                
                if len(parts) != 2:
                    print(f"Warning: Line {line_num} has invalid format: {line}", file=sys.stderr)
                    continue
                
                input_text = parts[0].strip()
                expected_output = parts[1].strip()
                test_cases.append((input_text, expected_output))
    
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file {filepath}: {e}", file=sys.stderr)
        sys.exit(1)
    
    return test_cases


def test_number_only(number: str, expected: str, language: str) -> Tuple[bool, str]:
    """
    Test a single number (without sentence context).
    
    Returns:
        (success, actual_output)
    """
    actual = normalize_number(number, language)
    
    # Check if expected output indicates out of bound
    # If number is out of range (0-1000), expect OUT_OF_BOUND
    clean_num = number.replace(',', '').replace(' ', '').replace('-', '')
    if clean_num.isdigit():
        num_value = int(clean_num)
        if num_value < 0 or num_value > 1000 or number.startswith('-'):
            # Out of bounds - should return OUT_OF_BOUND
            success = (actual == "OUT_OF_BOUND")
            return success, actual
    
    success = (actual == expected)
    return success, actual


def test_sentence(sentence: str, expected: str, language: str) -> Tuple[bool, str]:
    """
    Test a complete sentence.
    Note: This test script focuses on number-only tests.
    For full sentence testing, use normalize.py
    
    Returns:
        (success, actual_output)
    """
    # For this test script, we'll treat it as a number test
    return test_number_only(sentence, expected, language)


def run_tests(test_cases: List[Tuple[str, str]], language: str, mode: str = 'auto') -> dict:
    """
    Run all test cases and return results.
    
    Args:
        test_cases: List of (input, expected) tuples
        language: 'english' or 'french'
        mode: 'auto' (detect), 'number' (numbers only), or 'sentence' (full sentences)
    
    Returns:
        Dictionary with test statistics
    """
    total = len(test_cases)
    passed = 0
    failed = 0
    errors = []
    
    print(f"\n{'='*70}")
    print(f"Running {total} tests for {language.upper()}")
    print(f"Mode: {mode}")
    print(f"{'='*70}\n")
    
    for i, (input_text, expected) in enumerate(test_cases, 1):
        # Determine test mode
        if mode == 'auto':
            # If input is just digits, test as number; otherwise as sentence
            clean_input = input_text.replace(',', '').replace(' ', '').replace('-', '')
            is_number_only = clean_input.isdigit() or (input_text.startswith('-') and clean_input[1:].isdigit())
        elif mode == 'number':
            is_number_only = True
        else:  # sentence
            is_number_only = False
        
        # Run the test
        if is_number_only:
            success, actual = test_number_only(input_text, expected, language)
        else:
            success, actual = test_sentence(input_text, expected, language)
        
        if success:
            passed += 1
            if args.verbose:
                print(f"✓ Test {i}/{total}: PASS")
                print(f"  Input:    {input_text}")
                print(f"  Expected: {expected}")
                print(f"  Actual:   {actual}")
                print()
        else:
            failed += 1
            errors.append((input_text, expected, actual))
            print(f"✗ Test {i}/{total}: FAIL")
            print(f"  Input:    {input_text}")
            print(f"  Expected: {expected}")
            print(f"  Actual:   {actual}")
            print()
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Total:  {total}")
    print(f"Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total*100:.1f}%)")
    print(f"{'='*70}\n")
    
    return {
        'total': total,
        'passed': passed,
        'failed': failed,
        'errors': errors,
        'pass_rate': passed/total if total > 0 else 0
    }


def generate_unit_tests(language: str, output_file: str = None):
    """
    Generate unit test cases for numbers 0-1000.
    """
    print(f"Generating unit tests for {language}...")
    
    fst = french_fst if language == 'french' else english_fst
    
    test_cases = []
    errors = []
    
    for num in range(0, 1001):
        num_str = str(num)
        try:
            result = apply_fst(num_str, fst)
            if result and result != num_str:  # Successfully converted
                test_cases.append(f"{num_str}\t{result}")
            else:
                errors.append(num_str)
        except Exception as e:
            errors.append(num_str)
            print(f"Error processing {num_str}: {e}")
    
    # Output results
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            for line in test_cases:
                f.write(line + '\n')
        print(f"Generated {len(test_cases)} test cases in {output_file}")
    else:
        for line in test_cases[:10]:  # Show first 10
            print(line)
        if len(test_cases) > 10:
            print(f"... and {len(test_cases) - 10} more")
    
    if errors:
        print(f"\nWarning: {len(errors)} numbers could not be converted: {errors[:10]}")


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(
        description='Test text normalization system with unit tests (uses FAR archive)'
    )
    parser.add_argument(
        'testfile',
        nargs='?',
        help='Path to test file (TSV or CSV format: input<TAB>expected)'
    )
    parser.add_argument(
        '-l', '--language',
        choices=['english', 'french'],
        default='english',
        help='Language for tests (default: english)'
    )
    parser.add_argument(
        '-m', '--mode',
        choices=['auto', 'number', 'sentence'],
        default='auto',
        help='Test mode: auto (detect), number (numbers only), or sentence (full sentences)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show all test results (including passes)'
    )
    parser.add_argument(
        '-g', '--generate',
        action='store_true',
        help='Generate unit test file for numbers 0-1000'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file for generated tests (use with -g)'
    )
    parser.add_argument(
        '--far',
        default=DEFAULT_FAR_PATH,
        help=f'Path to FAR archive (default: {DEFAULT_FAR_PATH})'
    )
    
    global args
    args = parser.parse_args()
    
    # Load FSTs from FAR archive
    load_fsts_from_far(args.far)
    
    # Generate tests if requested
    if args.generate:
        output_file = args.output or f"unit_tests_{args.language}.txt"
        generate_unit_tests(args.language, output_file)
        return
    
    # Load and run tests
    if not args.testfile:
        print("Error: Test file required (or use -g to generate tests)", file=sys.stderr)
        print("\nUsage examples:")
        print("  python test_normalize.py test_english.txt -l english")
        print("  python test_normalize.py test_french.txt -l french -v")
        print("  python test_normalize.py -g -l english -o my_tests.txt")
        print("  python test_normalize.py test_english.txt --far custom/path.far")
        parser.print_help()
        sys.exit(1)
    
    # Load test cases
    print(f"Loading test cases from: {args.testfile}")
    test_cases = load_test_file(args.testfile)
    print(f"Loaded {len(test_cases)} test cases")
    
    # Run tests
    results = run_tests(test_cases, args.language, args.mode)
    
    # Exit with error code if any tests failed
    sys.exit(0 if results['failed'] == 0 else 1)


if __name__ == '__main__':
    main()