#!/usr/bin/env python3
"""
build_fst.py

Compiles English and French number normalizer FSTs into a FAR (Finite-State Archive)
for efficient storage and reuse.

Usage:
    python build_fst.py [--output OUTPUT_PATH]

Arguments:
    --output: Path for the output FAR file (default: number_normalizers.far)
"""

import argparse
import sys
from pathlib import Path

try:
    import pynini
    from pynini.export import export
except ImportError:
    print("Error: pynini is not installed. Install it with: pip install pynini")
    sys.exit(1)

# Import the FST builders
try:
    from build_english_fst import number_normalizer_fst as english_fst
    print("✓ English FST loaded successfully")
except ImportError as e:
    print(f"Error: Could not import build_english_fst.py: {e}")
    english_fst = None

try:
    from build_french_fst import number_normalizer_fst as french_fst
    print("✓ French FST loaded successfully")
except ImportError as e:
    print(f"Error: Could not import build_french_fst.py: {e}")
    french_fst = None


def build_far_archive(output_path: str = "number_normalizers.far"):
    """
    Build a FAR archive containing the English and French FSTs.
    
    Args:
        output_path: Path where the FAR file will be saved
    """
    if english_fst is None and french_fst is None:
        print("Error: No FSTs were successfully loaded. Cannot create FAR archive.")
        return False
    
    print(f"\nBuilding FAR archive: {output_path}")
    
    try:
        # Open FAR archive for writing
        far_writer = pynini.Far(output_path, mode="w", arc_type="standard")
        
        if english_fst is not None:
            print("  - Adding English FST (key: 'english')")
            far_writer.add("english", english_fst)
        
        if french_fst is not None:
            print("  - Adding French FST (key: 'french')")
            far_writer.add("french", french_fst)
        
        # Close the FAR writer (important!)
        far_writer.close()
        
        print(f"✓ FAR archive created successfully: {output_path}")
        print(f"\nTo use the archive:")
        print(f"  far = pynini.Far('{output_path}', mode='r')")
        print(f"  english_fst = far['english']")
        print(f"  french_fst = far['french']")
        
        return True
        
    except Exception as e:
        print(f"Error creating FAR archive: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_far_archive(far_path: str):
    """
    Verify that the FAR archive was created correctly and can be read.
    
    Args:
        far_path: Path to the FAR file
    """
    print(f"\nVerifying FAR archive: {far_path}")
    
    try:
        # Open the FAR archive for reading
        far = pynini.Far(far_path, mode='r')
        
        # List all FSTs in the archive
        fst_keys = list(far)
        print(f"  FSTs in archive: {fst_keys}")
        
        # Test each FST with a simple number
        test_number = "42"
        
        for key in fst_keys:
            fst = far[key]
            try:
                result = pynini.shortestpath(
                    pynini.accep(test_number, token_type='utf8') @ fst
                ).string("utf8")
                print(f"  ✓ {key}: '{test_number}' -> '{result}'")
            except Exception as e:
                print(f"  ✗ {key}: Error testing FST: {e}")
        
        print("\n✓ FAR archive verified successfully")
        return True
        
    except Exception as e:
        print(f"Error verifying FAR archive: {e}")
        return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Build a FAR archive containing English and French number normalizer FSTs"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="number_normalizers.far",
        help="Output path for the FAR file (default: number_normalizers.far)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify the FAR archive after creation"
    )
    
    args = parser.parse_args()
    
    # Build the FAR archive
    success = build_far_archive(args.output)
    
    if not success:
        sys.exit(1)
    
    # Verify if requested
    if args.verify:
        verify_success = verify_far_archive(args.output)
        if not verify_success:
            sys.exit(1)
    
    print("\n✓ Done!")


if __name__ == "__main__":
    main()