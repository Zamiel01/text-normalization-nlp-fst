import re
import sys
import pynini
from pynini.lib import pynutil
from pathlib import Path

# Path to the FAR archive
FAR_PATH = "../Far/my_normalized_language.far"

# Global variables to store loaded FSTs
english_fst = None
french_fst = None


def load_fsts_from_far(far_path=FAR_PATH):
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
    
    Args:
        num_str: String representation of the number (may contain commas, spaces, etc.)
        language: 'english' or 'french'
    
    Returns:
        Normalized word representation or "OUT_OF_BOUND"
    """
    # Clean the number string - remove commas, spaces
    clean_num = num_str.strip().replace(',', '').replace(' ', '')
    
    # Handle negative numbers - out of bound
    if clean_num.startswith('-'):
        return "OUT_OF_BOUND"
    
    # Check if it's a valid number
    if not clean_num.isdigit():
        # Could be something like "978-0" or other format
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
    
    Args:
        text: Input text containing numbers
        language: 'english' or 'french'
    
    Returns:
        Text with numbers replaced by their written forms or "OUT_OF_BOUND"
    """
    # Find all numbers in the text
    # Match: digits, optionally with commas or spaces
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
    
    Args:
        text: Input text to normalize (can be a number or sentence)
        language: Optional language specification ('english' or 'french')
                 If None, language will be auto-detected
    
    Returns:
        Normalized text with numbers written out (0-1000) or "OUT_OF_BOUND"
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


def main():
    """
    Command-line interface for text normalization.
    Reads from stdin or file, writes to stdout.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Normalize numbers (0-1000) in text to their written forms'
    )
    parser.add_argument(
        '-l', '--language',
        choices=['english', 'french'],
        help='Specify language (auto-detected if not provided)'
    )
    parser.add_argument(
        '-f', '--file',
        help='Input file (reads from stdin if not provided)'
    )
    parser.add_argument(
        '--far',
        default=FAR_PATH,
        help=f'Path to FAR archive (default: {FAR_PATH})'
    )
    parser.add_argument(
        'text',
        nargs='?',
        help='Text to normalize (alternative to stdin/file)'
    )
    
    args = parser.parse_args()
    
    # Load FSTs from FAR archive
    load_fsts_from_far(args.far)
    
    # Determine input source
    if args.text:
        text = args.text
    elif args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = sys.stdin.read()
    
    # Normalize and output
    result = normalize(text, args.language)
    print(result)


if __name__ == '__main__':
    # Load FSTs at module initialization
    if not english_fst or not french_fst:
        load_fsts_from_far()
    
    # If called directly, run CLI or tests
    if len(sys.argv) > 1:
        main()
    else:
        # Run test cases
        print("=== English Tests (0-1000) ===")
        test_cases_en = [
            "I have 3 dogs and 21 cats",
            "There are 100 people in the room",
            "I own 0 cars but 5 bicycles",
            "She bought 17 apples and 42 oranges",
            "The temperature is 32 degrees",
            "We have 99 problems",
            "1000",
            "0",
            "500",
            "5000",  # Out of bound
            "13,000",  # Out of bound
            "-5",  # Out of bound
        ]
        
        for test in test_cases_en:
            result = normalize(test, 'english')
            print(f"Input:  {test}")
            print(f"Output: {result}")
            print()
        
        print("=== French Tests (0-1000) ===")
        test_cases_fr = [
            "J'ai 3 chiens et 21 chats",
            "Il y a 100 personnes dans la salle",
            "Elle a acheté 17 pommes et 42 oranges",
            "Nous avons 99 problèmes",
            "Il a 0 voitures mais 5 vélos",
            "1000",
            "5000",  # Out of bound
        ]
        
        for test in test_cases_fr:
            result = normalize(test, 'french')
            print(f"Input:  {test}")
            print(f"Output: {result}")
            print()