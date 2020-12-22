from largebot.config import AIE_DRIVE
from welo365.welo365 import WorkBook
import pandas as pd

intent_path = [
    'Amazon Web Services, Inc',
    'Lex LargeBot (Akshat)',
    'Production Planning',
    'Files for Processing',
    'Processed Files 2.0',
    'EN-US',
    '_Training',
    'DeliveryPrep'
]

drop = 'Drop2'

prep_folder = AIE_DRIVE.get_item_by_path(*intent_path, 'ConversationPrep', drop)

intent_file_name = 'EN_Tr_Ints_Drop2.xlsx'

intent_file = AIE_DRIVE.get_item_by_path(*intent_path, intent_file_name)
wb = WorkBook(intent_file)
ws = wb.get_worksheet('Intent_Slot Creation')
_range = ws.get_range('A1:I3670')
columns, *values = _range.values

df = pd.DataFrame(values, columns=columns)
df['Domain'] = df['Intent ID'].apply(lambda x: 'MediaCable' if x.split()[0] == 'MC' else 'Finance')
df['IntentNumber'] = df['Intent ID'].apply(lambda x: int(x.split()[1]))
df.rename(
    columns={
        'Slot Name': 'SlotName',
        'Slot Prompt': 'SlotPrompt'
    },
    inplace=True
)

bot_template_name = 'bot_template.xlsx'

bot_template_file = AIE_DRIVE.get_item_by_path(*intent_path, bot_template_name)

intent_data = {
    'Finance': {},
    'MediaCable': {}
}

for row in df.itertuples(name='row'):
    domain = row.Domain
    conversation_name = f"{row.Domain}_{row.IntentName}_en-US"
    intent_key = (row.IntentNumber, row.IntentName)
    if intent_key not in intent_data[domain]:
        conversation = [
            conversation_name,
            'SingleIntent',
            f"{row.IntentNumber:03d}",
            '',
            row.IntentDescription
        ]
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
        intent_data[domain].setdefault(
            intent_key, {}).update(
            {
                'conversation': conversation,
                'script_in': script_in,
                'script_out': script_out,
                'scripts': []
            }
        )
    script = [
        conversation_name,
        row.SlotPrompt,
        '',
        row.SlotName,
        'FALSE',
        'FALSE',
        'FALSE',
        'FALSE'
    ]
    intent_data[domain][intent_key]['scripts'].append(script)

for domain in ('MediaCable', 'Finance'):
    intent_keys = list(intent_data[domain].keys())
    intent_names = [intent_name for _, intent_name in intent_keys]
    intent_numbers = [int(intent_number) for intent_number, _ in intent_keys]
    dms = {
        'MediaCable': 'MC',
        'Finance': 'Fi'
    }
    dm = dms.get(domain)
    intent_groups = [(f"bot_convo_prep_{dm}{intent_numbers[i]:03d}-{dm}{intent_numbers[i+4]:03d}.xlsx", intent_keys[i:i+5]) for i in range(0, len(intent_names), 5)]

    for file_name, intents in intent_groups:
        bot_template_file.copy(prep_folder, name=file_name)
        output_file = prep_folder.get_item(file_name)
        conversations = []
        scripts = []
        for intent in intents:
            conversations.append(intent_data[domain][intent]['conversation'])
            intent_scripts = [
                intent_data[domain][intent]['script_in'],
                *intent_data[domain][intent]['scripts'],
                intent_data[domain][intent]['script_out']
            ]
            scripts.extend(intent_scripts)
        wb = WorkBook(output_file)
        convo_ws = wb.get_worksheet('Conversations')
        convo_range = convo_ws.get_range('conversations')
        convo_range.update(
            values=conversations
        )
        script_ws = wb.get_worksheet('Scripts')
        script_range = script_ws.get_range(f"A4:H{3 + len(scripts)}")
        script_range.update(
            values=scripts
        )
