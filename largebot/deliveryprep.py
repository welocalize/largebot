from largebot.config import AIE_DRIVE, FILE_PATH, PROJ_CONFIG
from largebot.logger import get_logger
from largebot.qctool import batch_update
from welo365 import WorkBook
import pandas as pd
import re
from rapidfuzz import fuzz
import csv

logger = get_logger(__name__)

USE_CACHE = False

lang = 'ES-US'
phase = '_Training'
drop = '10%'

PROJ_DRIVE, PROJ_PATH = PROJ_CONFIG.get(lang)

# delivery_prep_path = [*FILE_PATH, lang, phase, 'Delivery Prep',  drop]
# delivery_prep_folder = AIE_DRIVE.get_item_by_path(*delivery_prep_path)
# master_intent_list = PROJ_DRIVE.get_item_by_path(*PROJ_PATH, lang, phase, 'Creator', 'MasterIntentList.xlsx')
# master_intent_wb = WorkBook(master_intent_list)
# master_intent_ws = master_intent_wb.get_worksheet('MasterIntentList')
# master_intent_range = master_intent_ws.get_range('A2:D1006')
# domain_switch = {
#     'Finance': 'Fi',
#     'Media_Cable': 'MC'
# }
# master_intents = {
#     f"{domain_switch.get(domain)} {intent_id}": (intent_name.strip(), intent_description.strip())
#     for domain, intent_id, intent_name, intent_description in master_intent_range.values
# }

SPOKEN_PUNC = dict.fromkeys('!"#$%&()*+,./:;<=>?@[\\]^_`|~')
WRITTEN_PUNC = {'[': '}', ']': '}'}

PUNC_TABLES = {
    'Spoken': str.maketrans(SPOKEN_PUNC),
    'Written': str.maketrans(WRITTEN_PUNC)
}

# slotmods = PROJ_DRIVE.get_item_by_path(*PROJ_PATH, 'EN-US', '_Training', 'Delivery Prep', 'Slot Mods for Automation.xlsx')

def get_fuzzy_list(utterances: list, intent_ids: list):
    results = [[utterance, [], 0] for utterance in utterances]
    for i, (utterance, intent_id) in enumerate(zip(utterances, intent_ids)):
        logger.info(f"Processing utterance {i + 1} of {len(utterances)}.")
        for j, choice in enumerate(utterances[i + 1:]):
            if fuzz.ratio(utterance, choice, score_cutoff=90):
                results[i][2] += 1
                results[j + i + 1][2] += 1
                results[i][1].append(f"Row {j + i + 3}: [{intent_ids[j + i + 1]}] {choice}")
                results[j + i + 1][1].append(f"Row {i + 2}: [{intent_ids[i]}] {utterance}")
    return [fuzzy_matches for _, fuzzy_matches, _ in results]

def get_intents():
    intent_template = delivery_prep_folder.get_item('intent_template.xlsx')
    intents_in_path = [*delivery_prep_path, 'Intent', drop]
    intents_in_folder = AIE_DRIVE.get_item_by_path(*intents_in_path)
    out_file_name = f"EN_Tr_Ints_{drop}.xlsx"
    out_file = delivery_prep_folder.get_item(out_file_name)
    if not out_file:
        intent_template.copy(delivery_prep_folder, name=out_file_name)
        out_file = delivery_prep_folder.get_item(out_file_name)
    intent_values = []
    drop_cols = [3, 4, 5, 6, 10]
    intent_files = list(intents_in_folder.get_items())

    for domain in ('MC', 'Fi'):
        domain_files = [file for file in intent_files if domain in file.name]
        for in_file in domain_files:
            print(in_file.name)
            wb = WorkBook(in_file)
            ws = wb.get_worksheet('Intent_Slot Creation')
            _range = ws.get_range('A1:N56')
            columns, *values = _range.values
            intent_values.extend(
                [
                    [
                        intent_id,
                        *master_intents.get(intent_id),
                        *value[3:]
                    ]
                    for value in values
                    if (
                        (intent_id := f"{domain} {value[0]}")
                        and (slot_prompt := value[11])
                        and 'Example' not in intent_id
                    )
                ]
            )


    df = pd.DataFrame(intent_values, columns=columns)
    df.drop(df.columns[drop_cols], axis=1, inplace=True)
    out_values = df.values.tolist()
    out_wb = WorkBook(out_file)
    out_ws = out_wb.get_worksheet('Intent_Slot Creation')
    out_range = out_ws.get_range(f"A2:I{len(out_values) + 1}")
    out_range.update(
        values=out_values
    )


def get_utterances(get_df: bool = False):
    utterance_template = delivery_prep_folder.get_item('utterance_template.xlsx')
    utterances_in_path = [*delivery_prep_path, 'Utterance', drop]
    utterances_in_folder = AIE_DRIVE.get_item_by_path(*utterances_in_path)
    out_file_name = f"EN_Tr_Utts_{drop}.xlsx"
    out_file = delivery_prep_folder.get_item(out_file_name)
    if not out_file:
        utterance_template.copy(delivery_prep_folder, name=out_file_name)
        out_file = delivery_prep_folder.get_item(out_file_name)
    utterance_values = []
    utterance_files = list(utterances_in_folder.get_items())

    if not USE_CACHE:
        with open('cache.csv', 'a') as f:
            c = csv.writer(f)
            for domain in ('MC', 'Fi'):
                domain_files = [file for file in utterance_files if domain in file.name]
                for in_file in domain_files:
                    logger.info(in_file.name)
                    wb = WorkBook(in_file)
                    ws = wb.get_worksheet('Sample Utterances')
                    _range = ws.get_range('A1:I301')
                    columns, *values = _range.values
                    # values.sort(key=lambda x: x[0])
                    utterance_values.extend(
                        [
                            [
                                intent_id,
                                *master_intents.get(intent_id),
                                *value[3:9],
                            ]
                            for value in values
                            if (
                                (intent_id := f"{domain} {value[0]}")
                                and 'Example' not in intent_id
                            )
                        ]
                    )
            c.writerows([columns, *utterance_values])
            df = pd.DataFrame(utterance_values, columns=columns[:9])
    else:
        df = pd.read_csv('cache.csv')

    slotmod_wb = WorkBook(slotmods)
    slotmod_ws = slotmod_wb.get_worksheet('Slot Modification List')
    _range = slotmod_ws.get_used_range()
    _, *values = _range.values
    modf = pd.DataFrame(values, columns=['IntentId', 'OldSlotName', 'NewSlotName', 'ChangeType'])
    namechanges = {}
    for row in modf.itertuples(name='row'):
        if row.ChangeType == 'NameChange':
            namechanges[row.IntentId] = {row.OldSlotName: row.NewSlotName}


    df.rename(
        columns={
            'ID': 'IntentID',
            'SlotName': 'SlotNameOne',
            'SlotName (Optional)': 'SlotNameTwo',
            'Sample Utterance': 'Utterance'
        },
        inplace=True
    )
    df = df.where(pd.notnull(df), None)

    def trim_utterance(utterance: str, modality: str):
        return utterance.strip().translate(PUNC_TABLES.get(modality)) if utterance else utterance

    def slot_name_changes(intent_id: str, slot_name: str):
        new_slot_name = namechanges.get(intent_id, {}).get(slot_name, None) or slot_name
        return new_slot_name

    def has_slot_errors(utterance: str, slot1: str = None, slot2: str = None):
        if not utterance:
            return
        slots = [slot for slot in (slot1, slot2) if slot and slot not in (None, 'Null', '')]
        actual = re.findall(r'\{(\w+)\}', utterance)
        if not slots and actual:
            logger.debug(f"UnexpectedSlotError: {slots=}, {actual=}")
            return 'UnexpectedSlotError'
        if actual:
            if len(actual) != len(set(actual)):
                logger.debug(f"DuplicatedSlotNameError: {slots=}, {actual=}")
                return 'DuplicatedSlotNameError'
        if slots != actual:
            if len(slots) == len(actual):
                logger.debug(f"SlotNameError: {slots=}, {actual=}")
                return 'SlotNameError'
            logger.debug(f"SlotNumberError: {slots=}, {actual=}")
            return 'SlotNumberError'

    df['SampleUtterance'] = df.apply(
        lambda x: x['NewUtterance'] if x['NewUtterance'] else x['Utterance'],
        axis=1
    )

    df['SampleUtterance'] = df.apply(
        lambda x: trim_utterance(x['SampleUtterance'], x['Modality']),
        axis=1
    )

    df['SlotNameOne'] = df.apply(
        lambda x: slot_name_changes(x['IntentID'], x['SlotNameOne']),
        axis=1
    )

    df['SlotNameTwo'] = df.apply(
        lambda x: slot_name_changes(x['IntentID'], x['SlotNameTwo']),
        axis=1
    )

    df['NeedsQC'] = df['NewUtterance'].apply(
        lambda x: 'FALSE' if x else 'TRUE'
    )

    df['SlotErrors'] = df.apply(
        lambda x: has_slot_errors(x['SampleUtterance'], x['SlotNameOne'], x['SlotNameTwo']),
        axis=1
    )

    utterances = df.SampleUtterance.tolist()
    intent_ids = df.IntentID.tolist()
    results = [[utterance, [], 0] for utterance, intent_id in utterances]
    for i, (utterance, intent_id) in enumerate(zip(utterances, intent_ids)):
        logger.info(f"Processing utterance {i+1} of {len(utterances)}.")
        for j, choice in enumerate(utterances[i + 1:]):
            if fuzz.ratio(utterance, choice, score_cutoff=90):
                results[i][2] += 1
                results[j + i + 1][2] += 1
                results[i][1].append(f"Row {j + i + 3}: [{intent_ids[j + i + 1]}] {choice}")
                results[j + i + 1][1].append(f"Row {i + 2}: [{intent_ids[i]}] {utterance}")

    df['FuzzyMatches'] = [
        fuzzy_matches
        for _, fuzzy_matches, _ in results
    ]

    df.drop(columns=['Utterance', 'ErrorFlags', 'NewUtterance'], inplace=True)

    if get_df:
        return df

    out_values = df.values.tolist()
    out_wb = WorkBook(out_file)
    out_ws = out_wb.get_worksheet('Sample Utterances')
    out_range = out_ws.get_range(f"A2:J{len(out_values) + 1}")
    batch_update(
        out_ws,
        out_range,
        out_values,
        divs=10
    )