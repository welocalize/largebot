from largebot.config import AIE_DRIVE, FILE_PATH, PROJ_DRIVE, PROJ_PATH
from welo365 import WorkBook
import pandas as pd

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
intent_template = delivery_prep_folder.get_item('intent_template.xlsx')
intents_in_path = [*delivery_prep_path, 'Intent', drop]
intents_in_folder = AIE_DRIVE.get_item_by_path(*intents_in_path)
out_file_name = f"EN_Tr_Ints_{drop}.xlsx"
out_file = delivery_prep_folder.get_item(out_file_name)
if not out_file:
    intent_template.copy(delivery_prep_folder, name=out_file_name)
    out_file = delivery_prep_folder.get_item(out_file_name)

def get_intents():
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


