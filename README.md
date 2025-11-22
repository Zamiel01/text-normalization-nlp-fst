**Text Normalization (English & French) — FST-based**

This repository provides simple, finite-state transducer (FST) based text normalization for English and French cardinal numbers (0–1000). It includes scripts to build number-normalizer FSTs, package them into a FAR archive, normalize text via a CLI, and run tests / WER evaluations.

**Quick Summary**:
- **Purpose**: Convert numeric tokens (0–1000) into their written forms in English or French.
- **FSTs**: Implemented in `src/build_english_fst.py` and `src/build_french_fst.py`.
- **FAR archive**: Create a reusable archive (FAR) using `src/far-file-generator.py`.
- **CLI normalizer**: `src/normalize-text.py` reads text (stdin, file, or argument) and outputs normalized text.

**Requirements**:
- **Python**: 3.8+ recommended.
- **Packages**: See `requirements.txt` (includes `pynini`, `jiwer`, `RapidFuzz`, etc.).
- **Note**: `pynini` often requires OpenFST and special wheels on some platforms. If `pip install pynini` fails, follow Pynini/OpenFST installation instructions for your OS.

**Install (Windows PowerShell examples)**:
```powershell
python -m pip install -r requirements.txt
# If pynini wheel is not available, follow the Pynini installation docs
```

**Build FAR archive**
Create a FAR archive that packages the English and French number normalizers. The repository contains a script that builds and verifies a FAR file.

Examples:
```powershell
# Build FAR into the Far/ folder
python src/far-file-generator.py --output Far/my_normalized_language.far --verify

# Or use the default output name
python src/far-file-generator.py -o number_normalizers.far --verify
```

The script will import `src/build_english_fst.py` and `src/build_french_fst.py`, add the FSTs under keys `english` and `french`, and save the FAR archive.

**Normalize text (CLI)**
`src/normalize-text.py` is the main CLI to normalize numbers in text. It loads FSTs from a FAR archive and replaces numeric tokens (0–1000) with their word forms.

Usage examples:
```powershell
# Normalize a short inline text (auto-detect language)
python src/normalize-text.py "I have 3 dogs and 21 cats"

# Force language to French
python src/normalize-text.py -l french "J'ai 3 chiens et 21 chats"

# Read from a file and write normalized output to stdout
python src/normalize-text.py -f test/en_sentences.txt --far Far/my_normalized_language.far

# Read from stdin (PowerShell):
Get-Content test/en_sentences.txt | python src/normalize-text.py --far Far/my_normalized_language.far
```

CLI flags (summary):
- **`-l, --language`**: `english` or `french` (auto-detected if not provided).
- **`-f, --file`**: path to input file (reads from stdin if not provided).
- **`--far`**: path to FAR archive (default points at `Far/my_normalized_language.far` in repo).
- **positional `text`**: provide text as single argument instead of stdin/file.

Notes on behavior:
- The normalizer focuses on cardinal numbers between 0 and 1000. Numbers outside this range return the literal `OUT_OF_BOUND`.
- If a FAR archive is missing or does not contain `english` / `french` keys, the scripts will print an error and exit; run the FAR build step first.

**Testing**
The repository includes testing utilities under `test/`.

- Run unit-style tests with a test file:
```powershell
python test/test_normalize.py unit-test/test-case-cardinal-en.txt -l english -v --far Far/my_normalized_language.far
```

- Generate full unit tests (numbers 0–1000) for a language:
```powershell
python test/test_normalize.py -g -l english -o unit_tests_english.txt --far Far/my_normalized_language.far
```

- Evaluate Word Error Rate (WER) using `jiwer`:
```powershell
python test/wer_test.py unit-test/test-case-cardinal-en.txt -l english -v -o wer_results.txt --far Far/my_normalized_language.far
```

**Troubleshooting**
- Error about missing FAR archive: ensure you built the FAR and provided the correct path to `--far`.
- `ImportError: pynini` or install failures: `pynini` may require platform-specific steps. Check the Pynini docs for pre-built wheels or compile instructions.
- If conversions yield raw digits (e.g., `"42" -> "42"`), verify that the FST keys inside the FAR are `english` and `french` and that the FAR builder completed successfully.

**Project structure (important files)**
- `src/build_english_fst.py` — English number FST (0–1000).
- `src/build_french_fst.py` — French number FST (0–1000).
- `src/far-file-generator.py` — Builds a FAR archive from the FSTs (adds keys `english` and `french`).
- `src/normalize-text.py` — CLI normalizer that loads FSTs from the FAR and normalizes text.
- `test/test_normalize.py` — Test runner & unit-generator.
- `test/wer_test.py` — WER / evaluation script using `jiwer`.

**Next steps & contributions**
- Expand numeric coverage (decimals, ordinals, larger ranges).
- Add robust language detection or allow per-line language annotations.
- Add packaging and CI tests that build the FAR and run the test suite automatically.

