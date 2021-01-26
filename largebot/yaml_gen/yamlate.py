import re
import time
from functools import partial
from typing import Callable, Union, Optional, List

import pandas as pd
from pathlib import Path
from pydantic import BaseModel as ConfigModel, validator, root_validator
from ruamel.yaml import YAML
from ruamel.yaml.representer import RepresenterError
from ruamel.yaml.scalarstring import SingleQuotedScalarString
from rypy import rex
from slot_faker import SlotFaker
from termcolor import cprint

from largebot.logger import get_logger
from welo365 import O365Account
from welo365.drive import File
from welo365.excel import WorkBook, WorkSheet, Range

logger = get_logger(__file__)

account = O365Account()

TESTING_DRIVE = account.get_site('msteams_08dd34-AmazonLex-TestingDataLargeBot').get_default_document_library()

link = 'https://welocalize.sharepoint.com/:x:/s/msteams_08dd34-AmazonLex-esUSLargeBot/EXV5W83kgmpBlcUBuUzDOHUB1O6CiaYNGgJGuunC5bAtzw?e=PaPqPa'
url = 'https://welocalize.sharepoint.com/:x:/r/sites/msteams_08dd34-AmazonLex-esUSLargeBot/_layouts/15/Doc.aspx?sourcedoc=%7BCD5B7975-82E4-416A-95C5-01B94CC33875%7D&file=utterances.xlsx&action=default&mobileredirect=true'
parent_id = '{CD5B7975-82E4-416A-95C5-01B94CC33875}'

item_id = 'EXV5W83kgmpBlcUBuUzDOHUB1O6CiaYNGgJGuunC5bAtzw'

WKDIR = Path(__file__).absolute().parent

FINANCE_CUSTOM = WKDIR / 'Finance_Custom.csv'
MEDIA_CABLE_CUSTOM = WKDIR / 'MediaCable_Custom.csv'

slot_config = {
    'types': WKDIR / 'MASTER_SLOT_TYPES.csv',
    'methods': WKDIR / 'MASTER_SLOT_METHODS.csv',
    'slotterances': WKDIR / 'MASTER_SLOTTERANCES.csv'
}
BASE_FAKER = SlotFaker(**slot_config)
# BASE_FAKER.load_custom(FINANCE_CUSTOM)
# BASE_FAKER.load_custom(MEDIA_CABLE_CUSTOM)

announce = lambda x: cprint(x, 'white', attrs=['blink'])
agent = lambda x: cprint(x, 'grey', 'on_yellow', attrs=['bold'])
customer = lambda x: cprint(x.rjust(50), 'cyan', attrs=['bold'])

FINANCE_XL = Path.home() / 'Downloads' / 'Finance Testing.xlsx'
TESTING_PATH = ['Amazon Lex - Testing Data LargeBot', 'Archive']


def get_first_turns():
    custom1 = 'FirstTurns1.xlsx'
    custom2 = 'FirstTurns2.xlsx'
    first_turns = {}
    for custom in (custom1, custom2):
        xl = TESTING_DRIVE.get_item_by_path(*TESTING_PATH, custom)
        wb = WorkBook(xl)
        ws = wb.get_worksheet('Sample Utterances')
        columns, *values = ws.get_used_range().values
        df = pd.DataFrame(values, columns=columns)
        df = df.where(pd.notnull(df), None)
        df['FirstTurn'] = df['SelectedFirstTurn'].apply(lambda x: bool(x))
        for row in df.itertuples(name='row'):
            if row.FirstTurn:
                first_turns.setdefault(row.IntentID, []).append(row.Utterance.strip())
    return first_turns


def cols_to_keys(key: str):
    return {
               'intent_id': 'IntentID',
               'intent_name': 'IntentName',
               'intent_description': 'IntentDescription',
               'confirm_intent': 'ConfirmIntent',
               'assume_intent': 'AssumeIntent',
               'slot_name': 'SlotName',
               'slot_method': 'Method',
               'slot_type': 'SlotTypeName',
               'slot_prompt': 'Agent',
               'slot_required': 'SlotRequired'
           }.get(key, None) or key


class SlotTypes(dict):
    @property
    def yaml(self):
        return [
            {
                'name': slot_type.name,
                'values': [
                    {
                        'value': value
                    }
                ]
            }
            for slot_type, slot_type_methods in self.items()
            for custom_slot_method in slot_type_methods
            for value in custom_slot_method.values
        ]


SLOT_TYPES = SlotTypes()


class BaseModel(ConfigModel):
    class Config:
        arbitrary_types_allowed = True
        alias_generator = cols_to_keys


class Slot(BaseModel):
    slot_name: str
    slot_type: str
    slot_prompt: str = ''
    slot_required: bool = False
    slot_method: Optional[Union[Callable[..., str], str]]

    class Config:
        allow_extra = False

    @validator('slot_method', pre=True)
    def configure_method(cls, v, values):
        slot_type = values.get('slot_type')
        if (custom_methods := BASE_FAKER._custom_values._get_methods().items()):
            for custom_method in custom_methods.values():
                if custom_method.name == v:
                    return custom_method.method
        if isinstance(v, str):
            if (method := getattr(BASE_FAKER, v, None)):
                SLOT_TYPES.setdefault(slot_type, []).append(
                    {
                        'name': v,
                        'method': method
                    }
                )
                return method
            if (parts := v.split(',')) and (method := getattr(BASE_FAKER, parts[0], None)):
                if len(parts) == 1:
                    return method
                _, *args = parts
                params = {
                    p[0]: p[1]
                    for arg in args
                    if (p := arg.split('='))
                }

                method = partial(method, **params)
                SLOT_TYPES.setdefault(slot_type, []).append(
                    {
                        'name': v,
                        'method': method
                    }
                )

            if (parts := v.split(':')) and (method := getattr(BASE_FAKER, parts[0], None)):
                if len(parts) < 2:
                    SLOT_TYPES.setdefault(slot_type, []).append(
                        {
                            'name': v,
                            'method': method
                        }
                    )
                    return method

                method = partial(BASE_FAKER.parse, text=f"{{{v}}}")
                SLOT_TYPES.setdefault(slot_type, []).append(
                    {
                        'name': v,
                        'method': method
                    }
                )
                return method
        return v

    def __call__(self):
        if callable(self.slot_method):
            return self.slot_method()

    def yaml(self):
        return {
            'name': self.slot_name,
            'type': self.slot_type,
            'prompt': self.slot_prompt,
            'required': self.slot_required
        }


class Turn(BaseModel):
    turn_id: int
    agent: Union[str, bool] = False
    customer_response: Union[str, bool] = False
    slot_value: Union[List[str], str, bool] = False
    slot_to_elicit: Union[str, bool] = False
    intent_to_elicit: Union[str, bool] = False
    confirm_intent: Union[str, bool] = False
    assume_intent: Union[str, bool] = False
    close: Union[str, bool] = False

    class Config:
        allow_extra = False

    @property
    def intent(self):
        return self.intent_to_elicit

    @property
    def sample_response(self):
        return self.customer_response

    @property
    def yaml(self):
        return {
            'agent': self.agent,
            'sample_response': self.sample_response,
            'slot_to_elicit': self.slot_to_elicit,
            'intent_to_elicit': self.intent_to_elicit,
            'confirm_intent': self.confirm_intent,
            'assume_intent': self.assume_intent,
            'close': self.close
        }


class Intent(BaseModel):
    domain: str = None
    intent_id: str = None
    intent_name: str = None
    intent_description: str = None
    scenario_id: str = None
    sample_utterances: List[str] = None
    slots: List[Slot] = None
    script: List[Turn] = None
    parent_intent: str = None
    locale: str = 'en-US'

    class Config:
        allow_extra = True

    @validator('intent_id', pre=True)
    def format_intent_id(cls, v, values):
        if rex.is_format(r'^(MC|Fi)\s[\d]{3}$', v):
            return v
        if (domain := values.get('domain')) and rex.is_format(r'[\d]{3}', v):
            dom = 'MC' if domain[0] == 'M' else 'Fi'
            return f"{dom} {v}"
        return v

    @validator('scenario_id', pre=True)
    def format_scenario_id(cls, v, values):
        return SingleQuotedScalarString(v) if v else SingleQuotedScalarString(values.get('intent_id'), '')

    @validator('sample_utterances', pre=True)
    def default_sample_utterances(cls, v, values):
        return v if v else [values.get('intent_description')]

    @validator('slots', pre=True)
    def prep_slots(cls, v, values):
        if (slot := Slot(**values)):
            return [slot]
        return []

    def append_row(self, **kwargs):
        if (slot := Slot(**kwargs)):
            self.slots.append(slot)
        if (turn := Turn(**kwargs)):
            self.turns.append(turn)

    def definition(self):
        return {
            'name': self.name,
            'sample_utterances': self.sample_utterances,
            'slots': [
                slot_provider.slot.yaml
                for slot_provider in self.slots
            ]
        } if not self.parent_intent else {
            'name': self.name,
            'parent_intent': self.parent_intent
        }

    def template(self):
        if self.parent_intent:
            return
        return {
            'conversation': None,
            'name': f"{self.domain}_{self.name}_{self.locale}",
            'scenario_id': self.scenario_id,
            'bias': ['SingleIntent'],
            'customer_instructions': self.customer_instructions,
            'description': self.description,
            'script': [
                turn.yaml
                for turn in self.script
            ]
        }

    @property
    def slot_types(self):
        return [
            slot_provider.yaml
            for slot_provider in self.slots
        ]

    @property
    def customer_instructions(self):
        return self.description.replace('User wants', 'Pretend you want')


class Utterer(BaseModel):
    FALLBACK_INTENTS: list = [
        Intent(intent_name=intent_name, parent_intent=parent_intent)
        for (intent_name, parent_intent) in (
            ('UnsupportedIntent', 'AMAZON.FallbackIntent'),
            ('OODIntent', 'AMAZON.FallbackIntent'),
            ('FallbackIntent', 'AMAZON.FallbackIntent'),
            ('CancelIntent', 'AMAZON.CancelIntent'),
            ('HelpIntent', 'AMAZON.HelpIntent'),
            ('NoIntent', 'AMAZON.NoIntent'),
            ('PauseIntent', 'AMAZON.PauseIntent'),
            ('RepeatIntent', 'AMAZON.RepeatIntent'),
            ('ResumeIntent', 'AMAZON.ResumeIntent'),
            ('StartOverIntent', 'AMAZON.StartOverIntent'),
            ('StopIntent', 'AMAZON.StopIntent'),
            ('YesIntent', 'AMAZON.YesIntent')
        )
    ]
    intents: List[Intent]
    locale: str = 'en-US'
    domain: str = 'Media_Cable'

    @classmethod
    def read_excel(cls, excel_path: Union[str, Path], sheet_name: str = 'Scripts'):
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        df = df.where(pd.notnull(df), '')
        data = {}
        for row in df.itertuples(name='row'):
            row = {
                key: value
                for key, value in row._as_dict().items()
                if value
            }
            if (intent_name := row.get('IntentName')) and (intent := data.get(intent_name)):
                intent.append_row(**row)

            if row.get('TurnID', '') == 0:
                row['sample_utterances'] = [
                    row.get(f"Customer{i}", '')
                    for i in range(1, 9)
                ]

    def open(self, conversation_id: str, opening: str, opening_slot: tuple = None):
        self.conversations[conversation_id] = {'opening_slot': False}
        slot_name, slot_method, slot_type, _, _ = opening_slot
        if opening_slot:
            self.conversations[conversation_id]['opening_slot'] = True
            utterance_method = getattr(self, f"{slot_name}_opening_utterance", None)
            slot_method = getattr(self, f"{slot_name}_value", None)
            opening = opening.format(utterance_method())
            slot_value = slot_method()
            self.conversations[conversation_id][slot_name] = slot_value
            opening = opening.format(slot_value)
        announce("Starting conversation...")
        announce('...')
        time.sleep(1)
        agent(f"Agent: {self.greeting()}")
        logger.debug('')
        time.sleep(1)
        customer(f"Customer: {opening}")
        logger.debug('')
        time.sleep(1)
        self.get_annotation(conversation_id, opening, slot_name)

    def exchange(self, conversation_id: str, slot_name: str, turn_id: int):
        utterance_method = getattr(self, f"{slot_name}_utterance", None)
        slot_method = getattr(self, f"{slot_name}_value", None)
        slot_prompt_method = getattr(self, f"{slot_name}_prompt", None)
        if utterance_method and slot_method and slot_prompt_method:
            slot_value = self.conversations.get(conversation_id, {}).get(slot_name, None)
            if not slot_value:
                slot_value = slot_method()
                self.conversations.setdefault(conversation_id, {}).update({slot_name: slot_value})
            slot_prompt = slot_prompt_method()
            if turn_id == 0 and self.conversations[conversation_id]['opening_slot']:
                slot_prompt = f"Thank you for providing that information. I would be happy to help with that. {slot_prompt}"
            utterance = utterance_method()
            customer_response = utterance.format(slot_value)
            agent(f"Agent: {slot_prompt}")
            logger.debug('')
            time.sleep(1)
            customer(f"Customer: {customer_response}")
            logger.debug('')
            time.sleep(1)
            self.get_annotation(conversation_id, customer_response, slot_name)

    def get_annotation(self, conversation_id: str, customer_response: str, slot_name: str):
        slot_value = self.conversations[conversation_id].get(slot_name, None)
        if not slot_value:
            return
        matches = re.search(re.escape(slot_value), customer_response)
        if matches:
            offset = matches.span()[0]
            annotation = {
                'is_slot_present': True,
                'slot_name': slot_name,
                'offset': offset,
                'slot_value': slot_value,
                'utterance': customer_response
            }
            announce(f"\t\tannotation:")
            for key, value in annotation.items():
                logger.debug(f"\t\t\t{key}: {value}")
            time.sleep(1)
            logger.debug('')

    def confirm_intent(self, confirm_intent: bool):
        agent("Agent: That's everything we need. Should I finalize your request?")
        logger.debug('')
        time.sleep(1)
        if confirm_intent:
            customer("Customer: Yes, please! Thanks!")
            logger.debug('')
            time.sleep(1)
            agent("Agent: You're all set!")
            logger.debug('')
            announce("Conversation completed.")
            return
        customer("Actually, let's hold off for right now. Thanks anyway for your help!")
        logger.debug('')
        time.sleep(1)
        agent("Agent: No worries. We're here if you change you're mind or have any questions. Have a nice day!")
        logger.debug('')
        announce("Conversation completed.")
        return

    def converse(self, conversation_id: str, slot_names: list, openings: list, confirm_intent: bool = True):
        self.add_slot_names(slot_names=slot_names)
        opening = self.random_element(openings)
        opening_slot = None
        if '{}' in opening:
            opening_slot, *slot_names = slot_names
        self.open(conversation_id, opening, opening_slot=opening_slot)
        for turn_id, slot_name in enumerate(slot_names):
            self.exchange(conversation_id, slot_name[0], turn_id)
        self.confirm_intent(confirm_intent)

    def build_yaml(self, name: str, domain: str, output_path: Path = None):
        definition = {
            'name': name,
            'locale': self.locale,
            'intent_clarification': ["I'd like to add a device plan"],
            'intents': self.intents,
            'slot_types': [
                intent.slot_types
                for intent in self.intents
            ]
        }

        template = {
            'name': name,
            'locale': self.locale,
            'domain': domain,
            'general_agent_instructions': 'In this task, you will be playing the Agent side of a customer service bot. Follow the directions found in the "Simulated Conversation with a Text Bot" guidelines.',
            'general_customer_instructions': 'In this task, you will be playing the Customer side of a customer service bot. Follow the directions found in the "Simulated Conversation with a Text Bot" guidelines.',
            'slot_filled_instructions': 'IMPORTANT - Do not re-ask for information that the Customer gave you when they first made the request. Just skip over that prompt when you get to it.',
            'custom_slot_instructions': "Please use the following information to answer the bot's questions.",
            'personal_information': 'IMPORTANT - Do not give any personal information to the bot! If it asks you for personal information, just make up something that sounds realistic.',
            'agent_did_not_understand': 'Sorry, I did not understand. Goodbye!',
            'conversations': [
                *[
                    intent.template()
                    for intent in self.intents
                    if intent.domain == domain
                ],
                *self.FALLBACK_INTENTS
            ]
        }

        try:
            output_path = output_path or Path.cwd()

            yaml = YAML()
            yaml.width = 200
            yaml.indent(mapping=2, sequence=2, offset=2)

            out_def = output_path / f"{name}_definition.yaml"
            out_temp = output_path / f"{name}_scenarios.yaml"

            for outfile, data in [(out_def, definition), (out_temp, template)]:
                with open(outfile, mode='w', encoding='utf-8') as outf:
                    yaml.dump(data, outf)

        except RepresenterError as e:
            logger.error(f"Error during YAML creation: {e}")

        return definition, template


class DomainScriptTurn(BaseModel):
    turn_id: int
    slot_value: Union[List[str], bool, str] = False
    intent_to_elicit: Union[bool, str] = False
    slot_to_elicit: Union[bool, str] = False
    agent: Union[bool, str] = False
    customer_response: Union[bool, str] = False
    confirm_intent: Union[bool, str] = False
    assume_intent: bool = False


class DomainConversation:
    script_turns: List[DomainScriptTurn] = None


class DomainIntent(BaseModel):
    intent_id: str = None
    intent_name: str = None
    intent_description: str = None
    conversations: List[List[DomainScriptTurn]] = None


def amazon_attr(name: str):
    return '_'.join(
        part.lower()
        for part in re.findall(r'[A-Z][^A-Z.]*', name.replace('AMAZON.', ''))
    )


def clean_conversation(convo):
    clean_convo = convo[:1]
    matches = rex.capture_all(
        r'\{(?P<slot_name>[\w]+)\}',
        convo[0].get('customer_response', '')
    )
    if matches and (first_turn_slots := matches.get('slot_name')):
        first_turn_customer_response = convo[0]['customer_response']
        first_turn_slot_value = []
        for turn in convo[1:]:
            if (
                    (first_turn_slot := turn.get('slot_to_elicit'))
                    and first_turn_slot in first_turn_slots
            ):
                if (slot_value := turn.get('slot_value', '')):
                    first_turn_customer_response = first_turn_customer_response.replace(
                        f"{{{first_turn_slot}}}", f"{slot_value}")
                    first_turn_slot_value.append(slot_value)
                    continue
            clean_convo.append(turn)
        clean_convo[0]['slot_value'] = first_turn_slot_value
        clean_convo[0]['customer_response'] = first_turn_customer_response
    return clean_convo


class DomainScript(BaseModel):
    source: File
    wb: WorkBook = None
    ws: WorkSheet = None
    convo_range: Range = None
    values: List[List[str]] = None
    intents: List[DomainIntent] = None
    conversations: list = None
    templates: dict = None

    @root_validator
    def get_data(cls, values):
        if (source := values.get('source')):
            wb = WorkBook(source)
            ws = wb.get_worksheet('Conversations')
            convo_range = ws.get_used_range()
            cols, *values = convo_range.values
            df = pd.DataFrame(values, columns=cols)
            df = df.where(pd.notnull(df), None)
            df = df.replace(to_replace='FALSE', value=False)
            _v = df.values.tolist()
            v = [
                row
                for row in _v
                if row[0]
            ]
            '''
            v = [
                row
                for row in convo_range.values
                if (intent_id := row[0])
            ]
            scrubbed = []
            for row in v:
                scrub = []
                for cell in row:
                    cell = False if cell in ('FALSE', 'False', 'false') else cell
                    scrub.append(cell)
                scrubbed.append(scrub)
            v = scrubbed
            '''
            intents = {}
            for _, intent_id, intent_name, intent_description, turn_id, *convo_data in v[1:]:
                if intent_id not in intents:
                    intents[intent_id] = {
                        'intent_id': intent_id,
                        'intent_name': intent_name,
                        'intent_description': intent_description,
                        'conversations': {}
                    }
                conversations = [convo_data[i:i + 5] for i in range(0, len(convo_data), 5)]
                for i, conversation in enumerate(conversations):
                    if set(conversation) not in ({False, ''}, {'', False}):
                        intents[intent_id]['conversations'].setdefault(i, {}).setdefault('turns', []).append([turn_id, *conversation])
            for intent_id in intents:
                convo_data = []
                for i in range(8):
                    convo_data.append(
                        intents[intent_id]['conversations'][i]
                    )
                intents[intent_id]['conversations'] = convo_data
            intents = list(intents.values())
            for intent in intents:
                if (conversations := intent.get('conversations')):
                    intent_conversations = []
                    for i, conversation in enumerate(conversations):
                        convo = []
                        conversation['status'] = conversation['turns'][0][2]
                        conversation['turns'] = conversation['turns'][1:]
                        if conversation['status'] == 'Rejected':
                            logger.debug(f"Skipping {intent} conversation {i+1} as 'Rejected'")
                            continue
                        for (turn_id, intent_to_elicit, slot_to_elicit, agent, customer_response, slot_value) in conversation['turns']:
                            if slot_value in ('FALSE', 'False', 'false'):
                                slot_value = False
                            if intent_to_elicit in ('FALSE', 'False', 'false'):
                                intent_to_elicit = False
                            if slot_to_elicit in ('FALSE', 'False', 'false'):
                                slot_to_elicit = False
                            if not intent_to_elicit and not slot_to_elicit:
                                logger.debug(
                                    f"{intent.get('intent_id')} has neither a slot nor a prompt for conversation {i}:{turn_id}"
                                )
                            confirm_intent = False
                            turn = {
                                'turn_id': turn_id,
                                'intent_to_elicit': intent_to_elicit,
                                'slot_to_elicit': slot_to_elicit,
                                'slot_value': slot_value,
                                'agent': agent,
                                'customer_response': customer_response,
                                'confirm_intent': confirm_intent,
                                'assume_intent': False
                            }
                            logger.debug(f"{turn=}")
                            convo.append(turn)
                            clean_convo = clean_conversation(convo)
                        intent_conversations.append(clean_convo)
                intent['conversations'] = intent_conversations
        return {
            'source': source,
            'wb': wb,
            'ws': ws,
            'convo_range': convo_range,
            'values': v,
            'intents': intents,
            'conversations': [
                {
                    'conversation': convo,
                    'description': intent.get('intent_description'),
                    'intent_name': intent.get('intent_name')
                }
                for intent in intents
                for convo in intent.get('conversations')
            ],
            'templates': {}
        }

    def export_template(self, name, locale, domain):
        count = {
            'bias': {}
        }
        AMAZON_Intents = {
            'UnsupportedIntent': 'AMAZON.FallbackIntent',
            'OODIntent': 'AMAZON.FallbackIntent',
            'FallbackIntent': 'AMAZON.FallbackIntent',
            'CancelIntent': 'AMAZON.CancelIntent',
            'HelpIntent': 'AMAZON.HelpIntent',
            'NoIntent': 'AMAZON.NoIntent',
            'PauseIntent': 'AMAZON.PauseIntent',
            'RepeatIntent': 'AMAZON.RepeatIntent',
            'ResumeIntent': 'AMAZON.ResumeIntent',
            'StartOverIntent': 'AMAZON.StartOverIntent',
            'StopIntent': 'AMAZON.StopIntent',
            'YesIntent': 'AMAZON.YesIntent'
        }

        templates = {}
        for conversation in self.conversations:
            intent_name = conversation.get('intent_name')
            conversation['conversation'] = [
                Turn(**turn)
                for turn in conversation.get('conversation')
            ]
            logger.debug(conversation.get('conversation'))
            conversation['domain'] = domain
            conversation['locale'] = locale

            def classify(conversation):
                intents = {
                    intent
                    for turn in conversation.get('conversation')
                    if (intent := turn.intent)
                }
                logger.debug(f"bias {intents=}")
                cname = [conversation.get('domain'), [], conversation.get('locale')]
                _bias = []
                confirm_intent = False
                for intent in intents:
                    if intent.lower() == 'false':
                        continue
                    intent = intent.replace('.', '')
                    if (amazint := AMAZON_Intents.get(intent)):
                        if amazint != f"AMAZON.{intent}":
                            cname[0] = f"{cname[0]}({intent})"
                            logger.debug(f"{cname[0]=}")
                            _bias.append(intent)
                            continue
                    if intent in ('ConfirmedIntent', 'DeniedIntent'):
                        confirm_intent = intent.replace('Intent', '')
                        continue
                    cname[1].append(intent)
                bias_num = 'SingleIntent' if len(cname[1]) == 1 else 'MultiIntent'
                bias = [bias_num, *_bias]
                if confirm_intent:
                    cname[1].append(confirm_intent)
                cname = f"{cname[0]}_{'_'.join(cname[1])}_{cname[2]}"
                return bias, cname

            bias, cname = classify(conversation)

            if cname in templates:
                logger.info(f"{cname} already in templates list; skipping")
                continue

            for bias_type in bias:
                count.get('bias', {}).setdefault(bias_type, []).append(1)

            description = conversation.get('description')
            logger.debug(f"{description=}")
            instructions = description.replace(
                'User', 'You').replace('Customer', 'You').replace(
                'wants', 'want').replace('has', 'have').replace(
                'their', 'your').replace(' is ', ' are ').replace('You\'s', 'Your').strip()
            scenario_id = SingleQuotedScalarString(f"{len(templates) + 1:04d}")
            script = []
            for i, turn in enumerate(conversation.get('conversation'), start=1):
                if turn.intent in ('Confirmed.Intent', 'Denied.Intent'):
                    confirm_intent = turn.intent
                    turn.intent_to_elicit = False
                    turn.confirm_intent = confirm_intent.split('.')[0]
                script_turn = {
                    'agent': turn.agent,
                    'sample_response': turn.sample_response,
                    'intent_to_elicit': turn.intent,
                    'slot_to_elicit': turn.slot_to_elicit,
                    'confirm_intent': turn.confirm_intent,
                    'assume_intent': turn.assume_intent,
                    'close': False
                }
                script.append(script_turn)
            if len(script) < 2:
                continue
            if '__' in cname:
                continue
            templates[cname] = {
                'conversation': None,
                'name': cname,
                'scenario_id': scenario_id,
                'bias': bias,
                'customer_intructions': instructions,
                'description': description,
                'script': [
                    *script,
                    {
                        'agent': 'Closing message (do not respond)',
                        'sample_response': False,
                        'intent_to_elicit': False,
                        'slot_to_elicit': False,
                        'confirm_intent': False,
                        'assume_intent': False,
                        'close': True
                    }
                ]
            }

        print(f"{len(templates)=}")

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
            'conversations': list(templates.values())
        }

        try:
            output_path = Path.cwd()

            yaml = YAML()
            yaml.width = 200
            yaml.indent(mapping=2, sequence=4, offset=2)

            out_temp = output_path / f"{name}_scenarios.yaml"

            with open(out_temp, mode='w', encoding='utf-8') as outf:
                yaml.dump(template, outf)

        except RepresenterError as e:
            logger.error(f"Error during YAML creation: {e}")

        return {
            bias_type: sum(bias_count)
            for bias_type, bias_count in count['bias'].items()
        }
