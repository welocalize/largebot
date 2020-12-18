from largebot.config import AIE_DRIVE
from welo365 import WorkBook
import pandas as pd

intent_path = [
    'Amazon Web Services, Inc',
    'Lex LargeBot (Akshat)',
    'Production Planning',
    'Files for Processing',
    'Processed Files 2.0',
    'EN-US',
    '_Training',
    'Media_Cable',
    'DeliveryPrep'
]

prep_folder = AIE_DRIVE.get_item_by_path(*intent_path, 'ConversationPrep')

intent_file_name = 'FINAL_EN_Tr_Ints_MC_Drop1.xlsx'

intent_file = AIE_DRIVE.get_item_by_path(*intent_path, intent_file_name)
wb = WorkBook(intent_file)
ws = wb.get_worksheet('Intent_Slot Creation')
_range = ws.get_range('A1:I723')
columns, *values = _range.values

df = pd.DataFrame(values, columns=columns)

bot_template_name = 'bot_template.xlsx'

bot_template_file = AIE_DRIVE.get_item_by_path(*intent_path, bot_template_name)

intent_data = {}

i = 1
for row in df.itertuples(name='row'):
    conversation_name = f"MediaCable_{row.IntentName}_en-US"
    if row.IntentName not in intent_data:
        conversation = [
            conversation_name,
            'SingleIntent',
            f"{i:03d}",
            '',
            row.IntentDescription
        ]
        i += 1
        script_in = [
            conversation_name,
            '',
            '',
            'FALSE',
            row.IntentName,
            'FALSE',
            'FALSE',
            'FALSE'
        ]
        script_out = [
            conversation_name,
            '',
            'FALSE',
            'FALSE',
            'FALSE',
            'FALSE',
            'FALSE',
            'TRUE'
        ]
        intent_data.setdefault(
            row.IntentName, {}).update(
            {
                'conversation': conversation,
                'script_in': script_in,
                'script_out': script_out,
                'scripts': []
            }
        )
    script = [
        conversation_name,
        row._7,
        '',
        row.IntentName,
        'FALSE',
        'FALSE',
        'FALSE',
        'FALSE'
    ]
    intent_data[row.IntentName]['scripts'].append(script)

intent_names = list(intent_data.keys())
intent_groups = [(f"bot_prep_MC{i+1:03d}-{i+5:03d}.xlsx", intent_names[i:i+5]) for i in range(0, len(intent_names), 5)]

for file_name, intents in intent_groups:
    bot_template_file.copy(prep_folder, name=file_name)
    output_file = prep_folder.get_item(file_name)
    conversations = []
    scripts = []
    for intent in intents:
        conversations.append(intent_data[intent]['conversation'])
        intent_scripts = [
            intent_data[intent]['script_in'],
            *intent_data[intent]['scripts'],
            intent_data[intent]['script_out']
        ]
        scripts.extend(intent_scripts)
    wb = WorkBook(output_file)
    convo_ws = wb.get_worksheet('Conversations')
    convo_range = convo_ws.get_range('conversations')
    convo_range.update(
        values=conversations
    )
    script_ws = wb.get_worksheets('Scripts')
    script_range = script_ws.get_range(f"A4:H{3 + len(scripts)}")
    script_range.update(
        values=scripts
    )
