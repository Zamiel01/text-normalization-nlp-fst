#!/usr/bin/env python3
"""
WER (Word Error Rate) test script for text normalization system.
Uses jiwer library to calculate WER between expected and actual outputs.
Uses FAR archive for FST loading.
"""

import sys
import os
import argparse
import re
from typing import List, Tuple, Dict
from pathlib import Path
import pynini

try:
    from jiwer import wer, cer, mer, wil
except ImportError:
    print("Error: jiwer library not found", file=sys.stderr)
    print("Install it with: pip install jiwer", file=sys.stderr)
    sys.exit(1)

# Default FAR archive path (relative to project root, not test folder)
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


def detect_language(text):
    """
    Simple language detection based on common words.
    Returns 'french' or 'english'.
    """
    text_lower = text.lower()
    
    # French indicators
    french_words = ['je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles', 
                    'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du',
                    'et', 'ou', 'mais', 'donc', 'car', 'avec', 'dans',
                    'ai', 'as', 'avons', 'avez', 'ont', 'chiens', 'chats',
                    'suis', 'est', 'sont', 'était', 'été']
    
    # English indicators
    english_words = ['i', 'you', 'he', 'she', 'we', 'they', 'the', 'a', 'an',
                     'and', 'or', 'but', 'with', 'in', 'on', 'at', 'to',
                     'have', 'has', 'had', 'am', 'is', 'are', 'was', 'were',
                     'dogs', 'cats', 'my', 'your', 'his', 'her', 'our', 'their']
    
    # Tokenize text
    words = re.findall(r'\b[a-zàâäéèêëïîôùûüÿæœç]+\b', text_lower)
    
    french_score = sum(1 for word in words if word in french_words)
    english_score = sum(1 for word in words if word in english_words)
    
    # Default to English if no clear indicator
    return 'french' if french_score > english_score else 'english'


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


def normalize_numbers(text, language='english'):
    """
    Normalize all numbers in the text to their written form.
    Only handles numbers from 0 to 1000.
    """
    # Find all numbers in the text
    number_pattern = r'\b\d[\d,\s]*\d\b|\b\d\b'
    
    def replace_number(match):
        num_str = match.group(0)
        normalized = normalize_number(num_str, language)
        return normalized
    
    # Replace all numbers with their normalized forms
    normalized_text = re.sub(number_pattern, replace_number, text)
    
    return normalized_text


def normalize(text, language=None):
    """
    Main normalization function.
    """
    if not text or not text.strip():
        return text
    
    # Auto-detect language if not specified
    if language is None:
        language = detect_language(text)
    
    # Check if the entire input is just a number
    clean_text = text.strip().replace(',', '').replace(' ', '')
    if clean_text.replace('-', '').isdigit() or (clean_text.startswith('-') and clean_text[1:].isdigit()):
        # It's just a number, normalize it directly
        return normalize_number(text, language)
    
    # It's a sentence, normalize numbers within it
    return normalize_numbers(text, language)


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
                    print(f"Warning: Line {line_num} has invalid format (no separator found): {line}", 
                          file=sys.stderr)
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


def calculate_wer_metrics(test_cases: List[Tuple[str, str]], language: str, 
                          verbose: bool = False) -> Dict:
    """
    Calculate WER and related metrics for test cases.
    
    Args:
        test_cases: List of (input, expected) tuples
        language: 'english' or 'french'
        verbose: Show detailed results for each test case
    
    Returns:
        Dictionary with WER metrics
    """
    references = []
    hypotheses = []
    errors = []
    
    print(f"\n{'='*70}")
    print(f"Processing {len(test_cases)} test cases for {language.upper()}")
    print(f"{'='*70}\n")
    
    for i, (input_text, expected) in enumerate(test_cases, 1):
        try:
            # Normalize the input text
            actual = normalize(input_text, language)
            
            references.append(expected)
            hypotheses.append(actual)
            
            if verbose:
                match_status = "✓ MATCH" if actual == expected else "✗ DIFF"
                print(f"Test {i}/{len(test_cases)}: {match_status}")
                print(f"  Input:    {input_text}")
                print(f"  Expected: {expected}")
                print(f"  Actual:   {actual}")
                if actual != expected:
                    print(f"  → Mismatch detected")
                print()
                
        except Exception as e:
            print(f"✗ Error processing test {i}: {input_text}")
            print(f"  Error: {e}\n")
            errors.append((input_text, expected, str(e)))
            # Add empty strings to maintain alignment
            references.append(expected)
            hypotheses.append("")
    
    # Calculate metrics
    try:
        wer_score = wer(references, hypotheses)
        cer_score = cer(references, hypotheses)
        mer_score = mer(references, hypotheses)
        wil_score = wil(references, hypotheses)
    except Exception as e:
        print(f"Error calculating metrics: {e}", file=sys.stderr)
        return None
    
    # Calculate exact match accuracy
    exact_matches = sum(1 for ref, hyp in zip(references, hypotheses) if ref == hyp)
    accuracy = exact_matches / len(test_cases) if test_cases else 0
    
    return {
        'wer': wer_score,
        'cer': cer_score,
        'mer': mer_score,
        'wil': wil_score,
        'accuracy': accuracy,
        'exact_matches': exact_matches,
        'total': len(test_cases),
        'errors': errors,
        'references': references,
        'hypotheses': hypotheses
    }


def print_wer_report(metrics: Dict, show_errors: bool = True):
    """
    Print a detailed WER report.
    
    Args:
        metrics: Dictionary containing WER metrics
        show_errors: Whether to show individual errors
    """
    print(f"\n{'='*70}")
    print(f"WER METRICS REPORT")
    print(f"{'='*70}\n")
    
    print(f"Total Test Cases: {metrics['total']}")
    print(f"Exact Matches:    {metrics['exact_matches']} ({metrics['accuracy']*100:.2f}%)")
    print(f"\n{'─'*70}\n")
    
    print("Error Rates:")
    print(f"  WER (Word Error Rate):           {metrics['wer']*100:.2f}%")
    print(f"  CER (Character Error Rate):      {metrics['cer']*100:.2f}%")
    print(f"  MER (Match Error Rate):          {metrics['mer']*100:.2f}%")
    print(f"  WIL (Word Information Lost):     {metrics['wil']*100:.2f}%")
    
    print(f"\n{'─'*70}\n")
    
    # Interpretation
    print("Interpretation:")
    if metrics['wer'] < 0.05:
        print("  ✓ Excellent performance (WER < 5%)")
    elif metrics['wer'] < 0.10:
        print("  ✓ Good performance (WER < 10%)")
    elif metrics['wer'] < 0.20:
        print("  ⚠ Fair performance (WER < 20%)")
    else:
        print("  ✗ Poor performance (WER ≥ 20%)")
    
    print(f"\n{'='*70}\n")
    
    # Show processing errors if any
    if metrics['errors'] and show_errors:
        print(f"Processing Errors: {len(metrics['errors'])}")
        print(f"{'─'*70}\n")
        for input_text, expected, error_msg in metrics['errors'][:10]:
            print(f"  Input:    {input_text}")
            print(f"  Expected: {expected}")
            print(f"  Error:    {error_msg}")
            print()
        if len(metrics['errors']) > 10:
            print(f"  ... and {len(metrics['errors']) - 10} more errors\n")


def export_results(metrics: Dict, output_file: str, language: str):
    """
    Export detailed results to a file.
    
    Args:
        metrics: Dictionary containing WER metrics
        output_file: Path to output file
        language: Language being tested
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"WER Test Results - {language.upper()}\n")
            f.write(f"{'='*70}\n\n")
            
            f.write(f"Total Test Cases: {metrics['total']}\n")
            f.write(f"Exact Matches:    {metrics['exact_matches']} ({metrics['accuracy']*100:.2f}%)\n\n")
            
            f.write(f"WER (Word Error Rate):       {metrics['wer']*100:.2f}%\n")
            f.write(f"CER (Character Error Rate):  {metrics['cer']*100:.2f}%\n")
            f.write(f"MER (Match Error Rate):      {metrics['mer']*100:.2f}%\n")
            f.write(f"WIL (Word Information Lost): {metrics['wil']*100:.2f}%\n\n")
            
            f.write(f"{'='*70}\n\n")
            
            # Write mismatches
            f.write("Detailed Results:\n")
            f.write(f"{'─'*70}\n\n")
            
            for i, (ref, hyp) in enumerate(zip(metrics['references'], metrics['hypotheses']), 1):
                if ref != hyp:
                    f.write(f"Test {i} - MISMATCH:\n")
                    f.write(f"  Expected: {ref}\n")
                    f.write(f"  Actual:   {hyp}\n\n")
        
        print(f"Results exported to: {output_file}")
        
    except Exception as e:
        print(f"Error exporting results: {e}", file=sys.stderr)


def main():
    """Main WER test runner."""
    parser = argparse.ArgumentParser(
        description='Calculate WER (Word Error Rate) for text normalization system (uses FAR archive)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python wer_test.py test_english.txt -l english
  python wer_test.py test_french.txt -l french -v
  python wer_test.py test_english.txt -l english -o results.txt
  python wer_test.py test_french.txt -l french -v -e
  python wer_test.py test_english.txt -l english --far ../Far/custom.far
        """
    )
    
    parser.add_argument(
        'testfile',
        help='Path to test file (format: input<TAB/~/>expected)'
    )
    parser.add_argument(
        '-l', '--language',
        choices=['english', 'french'],
        default='english',
        help='Language for tests (default: english)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed results for each test case'
    )
    parser.add_argument(
        '-o', '--output',
        help='Export results to file'
    )
    parser.add_argument(
        '-e', '--hide-errors',
        action='store_true',
        help='Hide processing errors in report'
    )
    parser.add_argument(
        '--far',
        default=DEFAULT_FAR_PATH,
        help=f'Path to FAR archive (default: {DEFAULT_FAR_PATH})'
    )
    
    args = parser.parse_args()
    
    # Load FSTs from FAR archive
    load_fsts_from_far(args.far)
    
    # Load test cases
    print(f"Loading test cases from: {args.testfile}")
    test_cases = load_test_file(args.testfile)
    
    if not test_cases:
        print("Error: No valid test cases found in file", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loaded {len(test_cases)} test cases")
    
    # Calculate WER metrics
    metrics = calculate_wer_metrics(test_cases, args.language, args.verbose)
    
    if metrics is None:
        print("Error: Failed to calculate metrics", file=sys.stderr)
        sys.exit(1)
    
    # Print report
    print_wer_report(metrics, show_errors=not args.hide_errors)
    
    # Export if requested
    if args.output:
        export_results(metrics, args.output, args.language)
    
    # Exit with error code if WER is above threshold (20%)
    sys.exit(0 if metrics['wer'] < 0.20 else 1)


if __name__ == '__main__':
    main()