import pandas as pd
from pathlib import Path

ints_xl = Path.home() / 'Downloads' / 'EN_Tr_Ints_Drop2.xlsx'
df = pd.read_excel(ints_xl)

df['Custom'] = df['Custom'].apply(lambda x: True if x == 'Custom' else False)
df['Customer'] = df.apply(
    lambda x: x['SlotValue'] if x['Custom'] is True else '',
    axis=1
)
df['SlotType'] = df.apply(
    lambda x: f"AMAZON.{x['SlotValue'].title()}" if x['Custom'] is False else '',
    axis=1
)

conversations = {}

for row in df.itertuples(name='row'):
    if row.IntentName not in conversations:
        conversations.setdefault(row.IntentName, {}).update(
            {
                'name': row.IntentName,
                'description': row.IntentDescription,
                'turns': []
            }
        )
    conversations[row.IntentName]['turns'].append(
        {
            'agent': row.SlotPrompt,
            'slot_to_elicit': row.SlotName,
            'sample_response': row.Customer,
            'slot_type': row.SlotType
        }
    )
