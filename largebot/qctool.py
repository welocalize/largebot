from __future__ import annotations

import re

import pandas as pd
from fuzzywuzzy import fuzz, process
from num2words import num2words
from welo365 import WorkBook

PUNC_WITH_SLOTS = '!"#$%&()*+,./:;<=>?@[\\]^_`|~'
PUNC_WITHOUT_SLOTS = '!"#$%&()*+,./:;<=>?@[\\]^_`{|}~'

BRACKETS_TABLE = str.maketrans(
    {
        '[': '{',
        ']': '}'
    }
)

SPOKEN_SLOTS = str.maketrans(dict.fromkeys(PUNC_WITH_SLOTS))
SPOKEN_NO_SLOTS = str.maketrans(dict.fromkeys(PUNC_WITHOUT_SLOTS))


def intake(utterance: str):
    return utterance.strip().translate(BRACKETS_TABLE)


def slot_prep(utterance: str, *slot_types: str):
    slots = [
        slot
        for slot in slot_types
        if slot not in ['', 'Null']
    ]
    if not slots:
        return re.sub(r'\{|\}', '', utterance)
    utterance = re.sub(r'\(([A-Z][a-z]+(\w+)?)\)', r'{\1}', utterance)
    utterance = re.sub(r'^(.*?)(([{}])?(\w+))([{}])(.*)$', r'\1{\4}\6', utterance)
    utterance = re.sub(r'^(.*)([{}])(\w+)([{}])?(.*)$', r'\1{\3}\5', utterance)
    utterance = re.sub(r'([\{\}])?Null([\{\}])?', '', utterance)
    return utterance


def check_slots(utterance: str, *slot_types: str, flags: list = None):
    flags = flags or []
    expected = [
        slot
        for slot in slot_types
        if slot not in ['', 'Null']
    ]
    if not expected:
        return utterance, flags
    actual = re.findall(r'\{\w+\}', utterance)
    if len(expected) != len(actual):
        flags.append('SLOT_ERROR')
        return utterance, flags
    for actual_slot, expected_slot in zip(actual, expected):
        utterance = utterance.replace(actual_slot, f"{{{expected_slot}}}")
    return utterance, flags


def check_spoken(utterance: str, flags: list = None):
    flags = flags or []
    if re.match(r'(\d+)', utterance):
        flags.append('DIGITS_ERROR')
        utterance = re.sub(r'(\d+)', lambda x: num2words(int(x.group(0))), utterance)
    return utterance.translate(SPOKEN_SLOTS), flags


def check_fuzzies(utterance: str, choices: list[str], flags: list = None, matches_dict: dict = None):
    flags = flags or []
    matches_dict = matches_dict or {}
    if (matches := list(
            process.extractWithoutOrder(
                utterance, choices, scorer=fuzz.token_sort_ratio, score_cutoff=90
            )
    )
    ):
        i = len(set(matches_dict.values())) + 1
        fuzzy_match_error = f"FUZZY_MATCH_ERROR{i:02d}"
        flags = [fuzzy_match_error, *flags]
        matches_dict[utterance] = fuzzy_match_error
        for match, _ in matches:
            matches_dict[match] = fuzzy_match_error
    return flags, matches_dict


def global_prep(utterance: str, spoken: bool, *slot_types: str):
    utterance = utterance.strip().translate(BRACKETS_TABLE)
    utterance = re.sub(r'\s+', ' ', utterance)
    utterance = slot_prep(utterance, *slot_types)
    utterance, flags = check_slots(utterance, *slot_types)
    if spoken:
        utterance, flags = check_spoken(utterance, flags)
    return utterance, flags


def qc_check(infile):
    wb = WorkBook(infile)
    ws = wb.get_worksheet('Sample Utterances')
    _range = ws.get_range('A1:G304')
    columns, _, _, _, *values = _range.values
    df = pd.DataFrame(values, columns=columns)
    slot_types = list(zip(df['SlotName'].tolist(), df['SlotName (Optional)'].tolist()))
    utterances = df['Sample Utterance'].tolist()
    modalities = [
        bool(modality == 'Spoken')
        for modality in df['Modality'].tolist()
    ]
    new_utterances = []
    flags = []

    for utterance, modality, slots in zip(utterances, modalities, slot_types):
        new_utterance, _flags = global_prep(utterance, modality, *slots)
        new_utterances.append(new_utterance)
        flags.append(_flags)

    matches_dict = {}
    new_flags = []
    for i, (new_utterance, flag) in enumerate(zip(new_utterances, flags)):
        if (fuzzy_match_error := matches_dict.get(new_utterance, None)):
            new_flags.append([fuzzy_match_error, *flag])
            continue
        choices = new_utterances[:i] + new_utterances[i + 1:]
        flag, matches_dict = check_fuzzies(new_utterance, choices, flag, matches_dict)
        new_flags.append(flag)

    df['ErrorFlags'] = [', '.join(flag) for flag in new_flags]
    df['NewUtterance'] = new_utterances
    df = df.where(pd.notnull(df), '')
    df.sort_values(
        by=['ErrorFlags', 'Modality'],
        ascending=[False, True],
        inplace=True
    )

    delete_range = ws.get_range('A2:G4')
    delete_range.delete()

    update_range = ws.get_range('A1:I301')
    update_range.update(
        values=[
            df.columns.tolist(),
            *df.values.tolist()
        ]
    )
    old_utterances = update_range.get_column(6)
    old_utterances.column_hidden = True
    old_utterances.update(
        values=old_utterances.values
    )

    error_flags = update_range.get_column(7)
    error_flags_format = error_flags.get_format()
    error_flags_format.auto_fit_columns()
