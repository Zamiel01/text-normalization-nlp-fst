import pynini
from pynini.lib import pynutil

# -----------------------------
# Fonctions utilitaires
# -----------------------------

def apply_fst(text, fst):
    """Applies an FST to a string."""
    try:
        return pynini.shortestpath(
            pynini.accep(text, token_type='utf8') @ fst
        ).string("utf8")
    except Exception as e:
        return f"Error: {e}, for input:'{text}'"

def I_O_FST(input_str: str, output_str: str):
    """Creates a simple input->output FST."""
    return pynini.cross(
        pynini.accep(str(input_str), token_type="utf8"),
        pynini.accep(str(output_str), token_type="utf8")
    ).optimize()

# -----------------------------
# Unités 0-9
# -----------------------------
units_map = {
    "0": "zéro", "1": "un", "2": "deux", "3": "trois", "4": "quatre",
    "5": "cinq", "6": "six", "7": "sept", "8": "huit", "9": "neuf"
}
fst_units = pynini.union(*[I_O_FST(k, v) for k, v in units_map.items()]).optimize()

# -----------------------------
# Adolescents 10-19
# -----------------------------
teens_map = {
    "10": "dix", "11": "onze", "12": "douze", "13": "treize",
    "14": "quatorze", "15": "quinze", "16": "seize",
    "17": "dix-sept", "18": "dix-huit", "19": "dix-neuf"
}
fst_teens = pynini.union(*[I_O_FST(k, v) for k, v in teens_map.items()]).optimize()

# -----------------------------
# Dizaines 20-69
# -----------------------------
tens_map = {
    "2": "vingt", "3": "trente", "4": "quarante",
    "5": "cinquante", "6": "soixante"
}
fst_tens_digits = pynini.union(*[I_O_FST(k, v) for k, v in tens_map.items()]).optimize()
fst_eat_zero = I_O_FST("0", "")

# Exact tens 20,30,...,60
fst_exact_tens = (fst_tens_digits + fst_eat_zero).optimize()

# Compound tens 21-69
fst_compound_tens_list = []
for tens_digit, tens_word in tens_map.items():
    for unit_digit, unit_word in units_map.items():
        if unit_digit == "0":
            continue
        word = f"{tens_word} et {unit_word}" if unit_digit == "1" else f"{tens_word}-{unit_word}"
        fst_compound_tens_list.append(I_O_FST(tens_digit + unit_digit, word))
fst_compound_tens = pynini.union(*fst_compound_tens_list).optimize()

# -----------------------------
# Dizaines 70-79
# -----------------------------
fst_70s_list = []
for i in range(10, 20):
    # Use the dictionary directly instead of apply_fst
    word = "soixante-" + teens_map[str(i)]
    fst_70s_list.append(I_O_FST("7" + str(i % 10), word))
fst_70s = pynini.union(*fst_70s_list).optimize()

# -----------------------------
# Dizaines 80-99
# -----------------------------
fst_80 = I_O_FST("80", "quatre-vingts")
fst_81_99_list = []

# 81-89
for i in range(1, 10):
    fst_81_99_list.append(I_O_FST("8" + str(i), f"quatre-vingt-{units_map[str(i)]}"))
# 90-99
for i in range(10, 20):
    # Use the dictionary directly instead of apply_fst
    fst_81_99_list.append(I_O_FST("9" + str(i % 10), f"quatre-vingt-{teens_map[str(i)]}"))

fst_81_99 = pynini.union(*fst_81_99_list).optimize()
fst_tens_70_99 = pynini.union(fst_70s, fst_80, fst_81_99).optimize()

# -----------------------------
# Centaines 100-999
# -----------------------------
fst_hundreds_list = []
for digit, word in units_map.items():
    if digit == "0":
        continue
    # Exact hundred
    if digit == "1":
        fst_hundreds_list.append(I_O_FST(digit + "00", "cent"))
    else:
        fst_hundreds_list.append(I_O_FST(digit + "00", f"{word} cents"))

    # 101-199, 201-999
    for i in range(1, 100):
        num_str = f"{digit}{i:02d}"
        if i < 10:
            text = f"{word} cent {units_map[str(i)]}"
        elif 10 <= i < 20:
            text = f"{word} cent {teens_map[str(i)]}"
        elif 20 <= i < 70:
            # Build the compound text directly
            tens_digit = str(i // 10)
            unit_digit = str(i % 10)
            if unit_digit == "0":
                tens_text = tens_map[tens_digit]
            elif unit_digit == "1":
                tens_text = f"{tens_map[tens_digit]} et {units_map[unit_digit]}"
            else:
                tens_text = f"{tens_map[tens_digit]}-{units_map[unit_digit]}"
            text = f"{word} cent {tens_text}"
        else:  # 70-99
            if 70 <= i < 80:
                tens_text = "soixante-" + teens_map[str(i - 60)]
            elif i == 80:
                tens_text = "quatre-vingts"
            elif 81 <= i < 90:
                tens_text = f"quatre-vingt-{units_map[str(i - 80)]}"
            else:  # 90-99
                tens_text = f"quatre-vingt-{teens_map[str(i - 80)]}"
            text = f"{word} cent {tens_text}"
        fst_hundreds_list.append(I_O_FST(num_str, text))

# Special case for 100
fst_hundreds_list.append(I_O_FST("100", "cent"))

fst_hundreds_fst = pynini.union(*fst_hundreds_list).optimize()

# -----------------------------
# Mille
# -----------------------------
fst_thousand = I_O_FST("1000", "mille").optimize()

# -----------------------------
# Combine tout
# -----------------------------
number_normalizer_fst = pynini.union(
    fst_units, fst_teens, fst_exact_tens, fst_compound_tens, fst_tens_70_99, fst_hundreds_fst, fst_thousand
).optimize()

