from largebot.config import AIE_DRIVE, FILE_PATH, PROJ_DRIVE, PROJ_PATH
from largebot.logger import get_logger
from largebot.qctool import  batch_update
from welo365 import WorkBook
import pandas as pd
import re

logger = get_logger(__name__)


lang = 'EN-US'
phase = '_Training'
drop = 'Drop2'
delivery_prep_path = [*FILE_PATH, lang, phase, 'DeliveryPrep']
delivery_prep_folder = AIE_DRIVE.get_item_by_path(*delivery_prep_path)
master_intent_list = PROJ_DRIVE.get_item_by_path(*PROJ_PATH, lang, phase, 'Creator', 'MasterIntentList.xlsx')
master_intent_wb = WorkBook(master_intent_list)
master_intent_ws = master_intent_wb.get_worksheet('MasterIntentList')
master_intent_range = master_intent_ws.get_range('A2:D1001')
domain_switch = {
    'Finance': 'Fi',
    'Media_Cable': 'MC'
}
master_intents = {
    f"{domain_switch.get(domain)} {intent_id}": (intent_name.strip(), intent_description.strip())
    for domain, intent_id, intent_name, intent_description in master_intent_range.values
}

SPOKEN_PUNC = dict.fromkeys('!"#$%&()*+,./:;<=>?@[\\]^_`|~')
WRITTEN_PUNC = {'[': '}', ']': '}'}

PUNC_TABLES = {
    'Spoken': str.maketrans(SPOKEN_PUNC),
    'Written': str.maketrans(WRITTEN_PUNC)
}

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


def get_utterances():
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

    for domain in ('MC', 'Fi'):
        domain_files = [file for file in utterance_files if domain in file.name]
        for in_file in domain_files:
            logger.info(in_file.name)
            wb = WorkBook(in_file)
            logger.info("Getting WorkBook")
            ws = wb.get_worksheet('Sample Utterances')
            logger.info("Getting WorkSheet")
            _range = ws.get_range('A1:I301')
            logger.info("Getting Range")
            columns, *values = _range.values
            logger.info("Adding values")
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

    in_values = []
    for i, (_, _, _, _, _, _, utterance, _, new_utterance) in enumerate(utterance_values):
        sample_utterance = new_utterance or utterance
        in_values.append([*utterance_values[i][0:6], sample_utterance])

    df = pd.DataFrame(utterance_values, columns=columns[:9])
    print(df.columns)
    df.rename(
        columns={
            'ID': 'Intent ID',
            'SlotName': 'SlotNameOne',
            'SlotName (Optional)': 'SlotNameTwo',
            'Sample Utterance': 'Utterance'
        },
        inplace=True
    )
    print(df.columns)
    df = df.where(pd.notnull(df), None)

    def trim_utterance(utterance: str, modality: str):
        return utterance.strip().translate(PUNC_TABLES.get(modality))

    def has_slot_errors(utterance: str, slot1: str = None, slot2: str = None):
        slots = [slot for slot in (slot1, slot2) if slot and slot not in (None, 'Null', '')]
        actual = re.findall(r'\{(\w+)\}', utterance)
        if not slots and actual:
            logger.info(f"UnexpectedSlotError: {slots=}, {actual=}")
            return 'UnexpectedSlotError'
        if actual:
            if len(actual) != len(set(actual)):
                logger.info(f"DuplicatedSlotNameError: {slots=}, {actual=}")
                return 'DuplicatedSlotNameError'
        if slots != actual:
            if len(slots) == len(actual):
                logger.info(f"SlotNameError: {slots=}, {actual=}")
                return 'SlotNameError'
            logger.info(f"SlotNumberError: {slots=}, {actual=}")
            return 'SlotNumberError'

    df['SampleUtterance'] = df.apply(
        lambda x: x['NewUtterance'] if x['NewUtterance'] is not None else x['Utterance'],
        axis=1
    )

    df['SampleUtterance'] = df.apply(
        lambda x: trim_utterance(x['SampleUtterance'], x['Modality']),
        axis=1
    )

    df['SlotErrors'] = df.apply(
        lambda x: has_slot_errors(x['SampleUtterance'], x['SlotNameOne'], x['SlotNameTwo']),
        axis=1
    )

    df['NeedsQC'] = df['NewUtterance'].apply(
        lambda x: 'FALSE' if x is not None else 'TRUE'
    )

    df.drop(columns=['Utterance', 'ErrorFlags', 'NewUtterance'], inplace=True)

    out_values = df.values.tolist()
    out_wb = WorkBook(out_file)
    out_ws = out_wb.get_worksheet('Sample Utterances')
    out_range = out_ws.get_range(f"A2:I{len(out_values) + 1}")
    batch_update(
        out_ws,
        out_range,
        out_values,
        divs=10
    )