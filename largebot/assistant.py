from largebot import AIE_DRIVE
from welo365.welo365 import WorkBook

french = 'fr-FR'
source_path = ['Workday', 'Assistant', 'FRENCH RYAN ONLY', french]
dictionary_source = AIE_DRIVE.get_item_by_path(*source_path, f"en_dictionary_{french}.xlsx")
dictionary_wb = WorkBook(dictionary_source)
dictionary_ws = dictionary_wb.get_worksheet('in')
dictionary_range_no_trans = dictionary_ws.get_range('A4634:C5380')
dictionary_range_trans = dictionary_ws.get_range('A2:C4633')
dictionary_trans_values = dictionary_range_trans.values
dictionary_no_trans_values = dictionary_range_no_trans.values
dictionary_template = AIE_DRIVE.get_item_by_path('Workday', 'Production Planning', 'Data Templates', 'Working Doc - Dictionary_Template.xlsx')
intent_source = AIE_DRIVE.get_item_by_path(*source_path, f"master_gt_ids_20-10-21_{french}.xlsx")
intent_wb = WorkBook(intent_source)
intent_ws = intent_wb.get_worksheet('in')
intent_range_no_trans = intent_ws.get_range('A17976:C20760')
intent_range_trans = intent_ws.get_range('A2:C17975')
intent_trans_values = intent_range_trans.values
intent_no_trans_values = intent_range_no_trans.values
intent_template = AIE_DRIVE.get_item_by_path('Workday', 'Production Planning', 'Data Templates', 'Working Doc - Intents_Template.xlsx')
ner_source = AIE_DRIVE.get_item_by_path(*source_path, f"master_ner_ids_20-10-21_{french}.xlsx")
ner_wb = WorkBook(ner_source)
ner_ws = ner_wb.get_worksheet('in')
ner_range_no_trans = ner_ws.get_range('A9311:C9469')
ner_range_trans = ner_ws.get_range('A2:C9310')
ner_trans_values = ner_range_trans.values
ner_no_trans_values = ner_range_no_trans.values
ner_template = AIE_DRIVE.get_item_by_path('Workday', 'Production Planning', 'Data Templates', 'Working Doc - NER_Template.xlsx')

template_path = ['Workday', 'Production Planning', 'Data Templates']
template_fol = AIE_DRIVE.get_item_by_path(*template_path)
template_fol.create_child_folder(french)
french_fol = template_fol.get_item(french)

values_dict = {
    'Dictionary':
        {
            'PartialTrans': dictionary_trans_values,
            'NoTrans': dictionary_no_trans_values
        },
    'Intents':
        {
            'PartialTrans': intent_trans_values,
            'NoTrans': intent_no_trans_values
        },
    'NER':
        {
            'PartialTrans': ner_trans_values,
            'NoTrans': ner_no_trans_values
        }
}


for name, template in [('Dictionary', dictionary_template), ('Intents', intent_template), ('NER', ner_template)]:
    print(name)
    french_fol.create_child_folder(name)
    source_fol = french_fol.get_item(name)
    for trans_type in ('PartialTrans', 'NoTrans'):
        template_values = values_dict.get(name).get(trans_type)
        batches = [template_values[i:i+200] for i in range(0, len(template_values), 200)]
        for i, batch in enumerate(batches, start=1):
            batch_name = f"{french}_{name}_{trans_type}_{i:02d}.xlsx"
            print(batch_name)
            template.copy(source_fol, name=batch_name)
            batch_file = source_fol.get_item(batch_name)
            batch_wb = WorkBook(batch_file)
            batch_ws = batch_wb.get_worksheet(name)
            batch_range = batch_ws.get_range(f"A3:C{len(batch) + 2}")
            batch_range.update(values=batch)



'''
langs = ['it-IT', 'ko-KR', 'ja-JP', 'de-DE', 'nl-NL', 'pt-BR', 'zh-CN', 'zh-TW', 'es-ES']
template_path = ['Workday', 'Production Planning', 'Data Templates']

for lang in langs[1:]:
    print(lang)
    for source in ('Dictionary', 'Intents', 'NER'):
        print(source)
        source_folder = AIE_DRIVE.get_item_by_path(*template_path, 'it-IT', source)
        lang_folder = AIE_DRIVE.get_item_by_path(*template_path, lang)
        lang_folder.create_child_folder(source)
        target_folder = lang_folder.get_item(source)
        for item in source_folder.get_items():
            print(item.name)
            item.copy(target_folder, name=item.name.replace('it-IT', lang))


for lang in langs:
    print(lang)
    for name, template, values in [('Dictionary', dictionary_template, dictionary_values), ('Intents', intent_template, intent_values), ('NER', ner_template, ner_values)]:
        print(name)
        lang_fol = AIE_DRIVE.get_item_by_path(*template_path, lang)
        lang_fol.create_child_folder(name)
        template_folder = lang_fol.get_item(name)
        batches = [values[i:i+200] for i in range(0, len(values), 200)]
        for i, batch in enumerate(batches, start=1):
            batch_name = f"{lang}_{name}_{i:02d}.xlsx"
            print(batch_name)
            template.copy(template_folder, name=batch_name)
            batch_file = template_folder.get_item(batch_name)
            batch_wb = WorkBook(batch_file)
            batch_ws = batch_wb.get_worksheet(name)
            batch_range = batch_ws.get_range(f"A3:B{len(batch) + 2}")
            batch_range.update(values=batch)
'''