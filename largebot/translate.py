from largebot import AIE_DRIVE, AIE_PATH
from welo365 import WorkBook

en_intent_fol = AIE_DRIVE.get_item_by_path(*AIE_PATH, 'Data Sheet Templates', 'es-US', 'Intent', 'EN')
es_intent_fol = AIE_DRIVE.get_item_by_path(*AIE_PATH, 'Data Sheet Templates', 'es-US', 'Intent', 'ES')
es_intent_template = AIE_DRIVE.get_item_by_path(*AIE_PATH, 'Data Sheet Templates', 'es-US', 'TEMPLATE - es-US_Training Data__Intent_Slot Creation Sheet.xlsx')

def translate_intents(en_values):
    es_values = []
    translation = ''
    divider = ''
    slot_type_name = ''
    for intent_id, intent_name, intent_description, _, _, _, slot_id, slot_name, slot_required, slot_name_built_in, _, slot_prompt, slot_value, slot_value_built_in in en_values:
        es_values.append(
            [
                intent_id, intent_name, translation, intent_description, divider,
                slot_id, slot_name, translation, slot_required, slot_name_built_in, divider,
                slot_prompt, translation, slot_value, translation, slot_type_name, slot_value_built_in
            ]
        )
    return es_values


for en_item in en_intent_fol.get_items():
    es_name = en_item.name.replace('EN', 'ES')
    print(es_name)
    es_intent_template.copy(es_intent_fol, name=es_name)
    es_intent_file = es_intent_fol.get_item(es_name)
    en_wb = WorkBook(en_item)
    en_ws = en_wb.get_worksheet('Intent_Slot Creation')
    en_range = en_ws.get_range('A7:N56')
    en_values = en_range.values
    es_wb = WorkBook(es_intent_file)
    es_ws = es_wb.get_worksheet('Intent_Slot Creation')
    es_range = es_ws.get_range('A7:Q56')
    es_values = translate_intents(en_values)
    es_range.update(values=es_values)