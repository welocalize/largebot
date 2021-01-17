from welo365 import WorkBook
from largebot import AIE_DRIVE, FILE_PATH
import pandas as pd
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import SingleQuotedScalarString
from pathlib import Path

postponexl = AIE_DRIVE.get_item_by_path(*FILE_PATH, 'EN-US', 'Testing', 'POSTPONE', 'BOT TEMPLATE AND DEF.xlsx')
wb = WorkBook(postponexl)
ws = wb.get_worksheet('Scripts')
_range = ws.get_range('A3:K93')
columns, *values = _range.values

df = pd.DataFrame(values, columns=columns)

df.replace(to_replace='FALSE', value=False, inplace=True)
df.replace(to_replace='TRUE', value=True, inplace=True)
df = df.applymap(
    lambda x: x.strip() if isinstance(x, str) else x
)

intents = {}
slot_types = {}
conversations = {}
for row in df.itertuples(name='row'):
    if row.IntentName not in intents:
        intents[row.IntentName] = {
            'name': row.IntentName,
            'sample_utterances': [row.SampleResponse],
            'slots': []
        }
    if row.SlotName:
        intents[row.IntentName]['slots'].append(
            {
                'name': row.SlotName,
                'type': row.SlotType,
                'prompt': row.Agent,
                'required': row.SlotRequired
            }
        )
    if row.SlotType and 'AMAZON' not in row.SlotType:
        if row.SlotType not in slot_types:
            slot_types.setdefault(row.SlotType, {}).update(
                {
                    'name': row.SlotType,
                    'values': []
                }
            )
        slot_types[row.SlotType]['values'].append(
            {
                'value': row.SlotValue
            }
        )
    if row.ConversationName not in conversations:
        conversations[row.ConversationName] = {
            'conversation': None,
            'name': row.ConversationName,
            'scenario_id': SingleQuotedScalarString(f"202012{row.ScenarioID}"),
            'bias': ['SingleIntent'],
            'customer_instructions': row.CustomerInstructions,
            'description': row.Description,
            'script': []
        }
    conversations[row.ConversationName]['script'].append(
        {
            'agent': row.Agent,
            'sample_response': row.SampleResponse,
            'slot_to_elicit': row.SlotName,
            'intent_to_elicit': row.IntentName,
            'confirm_intent': False,
            'assume_intent': False,
            'close': not bool(row.SampleResponse)
        }
    )


intents = list(intents.values())
slot_types = list(slot_types.values())
conversations = list(conversations.values())


default_intents = [
    {'name': 'UnsupportedIntent', 'parent_intent': 'AMAZON.FallbackIntent'},
    {'name': 'OODIntent', 'parent_intent': 'AMAZON.FallbackIntent'},
    {'name': 'FallbackIntent', 'parent_intent': 'AMAZON.FallbackIntent'},
    {'name': 'CancelIntent', 'parent_intent': 'AMAZON.CancelIntent'},
    {'name': 'HelpIntent', 'parent_intent': 'AMAZON.HelpIntent'},
    {'name': 'NoIntent', 'parent_intent': 'AMAZON.NoIntent'},
    {'name': 'PauseIntent', 'parent_intent': 'AMAZON.PauseIntent'},
    {'name': 'RepeatIntent', 'parent_intent': 'AMAZON.RepeatIntent'},
    {'name': 'ResumeIntent', 'parent_intent': 'AMAZON.ResumeIntent'},
    {'name': 'StartOverIntent', 'parent_intent': 'AMAZON.StartOverIntent'},
    {'name': 'StopIntent', 'parent_intent': 'AMAZON.StopIntent'},
    {'name': 'YesIntent', 'parent_intent': 'AMAZON.YesIntent'}
]

intents.extend(default_intents)

def get_bot_definition(name: str, locale: str = 'en-US'):
    definition = {
        'name': name,
        'locale': locale,
        'intent_clarification': ["I'd like to add a device plan"],
        'intents': intents,
        'slot_types': slot_types
    }

    outfile = Path.cwd() / f"{name}.yaml"

    yaml = YAML()
    yaml.width = 200
    yaml.indent(mapping=2, sequence=4, offset=2)

    with open(outfile, mode='w', encoding='utf-8') as out_file:
        yaml.dump(definition, out_file)


def get_template(name: str, domain: str = 'MediaInternetTelecom', locale: str = 'en-US'):
    template = {
        'name': name,
        'locale': locale,
        'domain': domain,
        'general_agent_instructions': 'In this task, you will be playing the Agent side of a customer service bot. Follow the directions found in the "Simulated Conversation with a Text Bot" guidelines.',
        'general_customer_instructions': 'In this task, you will be playing the Customer side of a customer service bot. Follow the directions found in the "Simulated Conversation with a Text Bot" guidelines.',
        'slot_filled_instructions': 'IMPORTANT - Do not re-ask for information that the Customer gave you when they first made the request. Just skip over that prompt when you get to it.',
        'custom_slot_instructions': "Please use the following information to answer the bot's questions.",
        'personal_information': 'IMPORTANT - Do not give any personal information to the bot! If it asks you for personal information, just make up something that sounds realistic.',
        'agent_did_not_understand': 'Sorry, I did not understand. Goodbye!',
        'conversations': conversations
    }

    outfile = Path.cwd() / f"{name}.yaml"

    yaml = YAML()
    yaml.width = 200
    yaml.indent(mapping=2, sequence=4, offset=2)

    with open(outfile, mode='w', encoding='utf-8') as out_file:
        yaml.dump(template, out_file)