# number_normalizer_0_1000.py

import pynini
from pynini.lib import pynutil

# -----------------------------
# Helper Functions
# -----------------------------

def apply_fst(text, fst):
    """
    Applies a finite-state transducer (FST) to a string.

    Args:
        text (str): The number as a string, e.g., "42"
        fst (pynini.Fst): The FST to apply

    Returns:
        str: The transduced output, e.g., "forty two", or an error message
    """
    try:
        return pynini.shortestpath(
            pynini.accep(text, token_type='utf8') @ fst
        ).string("utf8")
    except Exception as e:
        return f"Error: {e}, for input:'{text}'"

def I_O_FST(input_str: str, output_str: str):
    """
    Creates a simple input->output FST mapping.

    Args:
        input_str (str): The input string
        output_str (str): The output string

    Returns:
        pynini.Fst: Optimized FST for the mapping
    """
    input_str = str(input_str)
    output_str = str(output_str)
    return pynini.cross(
        pynini.accep(input_str, token_type="utf8"),
        pynini.accep(output_str, token_type="utf8")
    ).optimize()

# -----------------------------
# Units 0-9
# -----------------------------

# Map each digit to its word
units_map = {
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine"
}

# Create FSTs for each unit and combine them
fst_units_list = [I_O_FST(k, v) for k, v in units_map.items()]
fst_units = pynini.union(*fst_units_list).optimize()

# -----------------------------
# Teens 10-19
# -----------------------------

teens_map = {
    "10": "ten", "11": "eleven", "12": "twelve", "13": "thirteen",
    "14": "fourteen", "15": "fifteen", "16": "sixteen",
    "17": "seventeen", "18": "eighteen", "19": "nineteen"
}

fst_teens_list = [I_O_FST(k, v) for k, v in teens_map.items()]
fst_teens = pynini.union(*fst_teens_list).optimize()

# -----------------------------
# Tens 20-90
# -----------------------------

# Map first digit of tens to word
tens_digit_map = {
    "2": "twenty", "3": "thirty", "4": "forty", "5": "fifty",
    "6": "sixty", "7": "seventy", "8": "eighty", "9": "ninety"
}

fst_tens_digit_list = [I_O_FST(k, v) for k, v in tens_digit_map.items()]
fst_tens_digits = pynini.union(*fst_tens_digit_list).optimize()

# FST to "eat" a zero (for exact tens like 20,30)
fst_eat_zero = I_O_FST("0", "")

# Exact tens like 20, 30, 40
fst_exact_tens = (fst_tens_digits + fst_eat_zero).optimize()

# -----------------------------
# Compound tens 21-99
# -----------------------------

# Units for second digit (excluding zero)
compound_units_map = {k: v for k, v in units_map.items() if k != "0"}
fst_compound_units_digits = pynini.union(
    *[I_O_FST(k, v) for k, v in compound_units_map.items()]
).optimize()

# FST to insert a space between tens and units
fst_insert_space = I_O_FST("", " ")

# Combine tens + space + units for numbers like 21, 34, 99
fst_compound_tens = (fst_tens_digits + fst_insert_space + fst_compound_units_digits).optimize()

# -----------------------------
# Hundreds 100-999
# -----------------------------

fst_hundreds = []

# Loop over hundreds digit
for digit, word in compound_units_map.items():
    # Example: "100" -> "one hundred"
    fst_hundreds.append(I_O_FST(digit + "00", word + " hundred"))

    # Loop over tens and units to build "101-199", "201-299", etc.
    for i in range(1, 100):
        num_str = f"{digit}{i:02d}"

        if i < 10:
            # Numbers like 101-109: "one hundred one", etc.
            fst_hundreds.append(I_O_FST(num_str, word + " hundred " + apply_fst(str(i), fst_units)))
        elif 10 <= i < 20:
            # Numbers like 110-119: "one hundred eleven", etc.
            fst_hundreds.append(I_O_FST(num_str, word + " hundred " + apply_fst(str(i), fst_teens)))
        else:
            # Numbers like 120-199
            tens_digit = str(i // 10)
            unit_digit = str(i % 10)
            if unit_digit == "0":
                # Exact tens: 120, 130
                fst_hundreds.append(I_O_FST(num_str, word + " hundred " + apply_fst(tens_digit + "0", fst_exact_tens)))
            else:
                # Compound tens: 121, 134, etc.
                fst_hundreds.append(I_O_FST(num_str, word + " hundred " + apply_fst(tens_digit + unit_digit, fst_compound_tens)))

# Combine all hundreds into a single FST
fst_hundreds_fst = pynini.union(*fst_hundreds).optimize()

# -----------------------------
# One thousand
# -----------------------------
fst_thousand = I_O_FST("1000", "one thousand")

# -----------------------------
# Combine everything into one FST for 0-1000
# -----------------------------
number_normalizer_fst = pynini.union(
    fst_units, fst_teens, fst_exact_tens, fst_compound_tens, fst_hundreds_fst, fst_thousand
).optimize()

