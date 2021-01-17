from __future__ import annotations

import re
import time

import pandas as pd
from faker import Generator
from faker.providers import BaseProvider
from largebot.config import ACCOUNT
from pathlib import Path
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import SingleQuotedScalarString
from ruamel.yaml.representer import RepresenterError
from slot_faker import SlotFaker
from termcolor import cprint
from welo365 import WorkBook
from largebot.logger import get_logger


logger = get_logger(__name__)


MASTER = Path(__file__).parent.absolute() / 'master.csv'
df = pd.read_csv(MASTER)
df = df.where(pd.notnull(df), '')
names = df.columns.tolist()
AMAZON_UTTERANCES = {
    name: [
        phrase
        for phrase in df[name].tolist()
        if phrase
    ]
    for name in names
}


def clean_master(master: Path):
    df = pd.read_csv(master)
    columns = df.columns.tolist()
    df = df.where(pd.notnull(df), '')

    for column in columns:
        phrases = [
            phrase.strip()
            for phrase in df[column].tolist()
            if phrase
        ]
        for i in range(50 - len(phrases)):
            phrases.append('')
        df[column] = phrases

    df.to_csv('master.csv', index=False)


def amazon_attr(name: str):
    return '_'.join(
        part.lower()
        for part in re.findall(r'[A-Z][^A-Z.]*', name.replace('AMAZON', 'Amazon'))
    )


def get_conversational_name(name: str):
    return ' '.join(name.split('_'))


fake = SlotFaker()

builtins = {
    'NUMBER': 'AMAZON.Number',
    'FIRSTNAME': 'AMAZON.FirstName',
    'LASTNAME': 'AMAZON.LastName',
    'PHONENUMBER': 'AMAZON.PhoneNumber',
    'ALPHANUMERIC': 'AMAZON.AlphaNumeric',
    'EMAILADDRESS': 'AMAZON.EmailAddress',
    'POSTALADDRESS': 'AMAZON.PostalAddress',
    'DATEINTERVAL': 'AMAZON.DateInterval',
    'TIME': 'AMAZON.Time',
    'DATE': 'AMAZON.Date',
    'CURRENCY': 'AMAZON.Currency',
    'DURATION': 'AMAZON.Duration',
    'STATE': 'AMAZON.State',
    'COUNTRY': 'AMAZON.Country',
    'CITY': 'AMAZON.City',
    'AIRPORT': 'AMAZON.Airport',
    'DAYOFWEEK': 'AMAZON.DayOfWeek',
    'PERCENTAGE': 'AMAZON.Percentage',
    'SPEED': 'AMAZON.Speed',
    'STREETNAME': 'AMAZON.StreetName',
    'WEIGHT': 'AMAZON.Weight'
}

AMAZON_PROVIDERS = {
    # 'AMAZON.Number': fake.number,
    'AMAZON.FirstName': fake.first_name,
    'AMAZON.LastName': fake.last_name,
    'AMAZON.PhoneNumber': fake.phone_number,
    # 'AMAZON.AlphaNumeric': fake.alpha,
    'AMAZON.EmailAddress': fake.email,
    'AMAZON.PostalAddress': fake.address,
    'AMAZON.DateInterval': fake.date,
    'AMAZON.Time': fake.time,
    'AMAZON.Date': fake.date,
    'AMAZON.Currency': fake.currency,
    # 'AMAZON.Duration': fake.duration,
    'AMAZON.State': fake.state,
    'AMAZON.Country': fake.country,
    'AMAZON.City': fake.city,
    # 'AMAZON.Airport': fake.airport,
    'AMAZON.DayOfWeek': fake.day_of_week,
    'AMAZON.Percentage': fake.percentage,
    'AMAZON.Speed': fake.speed,
    'AMAZON.StreetName': fake.street_name,
    'AMAZON.Weight': fake.weight
}

slot_names = [
    ('UserFirstName', 'amazon_first_name', 'AMAZON.FirstName', 'May I have your first name please?', []),
    ('UserLastName', 'amazon_last_name', 'AMAZON.LastName', 'May I have your last name please?', []),
    ('UserBankAccountNumber', 'bank_account_number', 'AMAZON.AlphaNumeric', 'What is your bank account number?', []),
    ('UserSocialSecurityNumber',
     'ssn', 'AMAZON.Number', 'To confirm you are the account holder, can I have your social security number?', []
     ),
    ('NewAccountUsername',
     'user_name', 'AMAZON.AlphaNumeric',
     'What do you want to be your username? You will use this to login to your new account.', []
     ),
    ('NewAccountPassword', 'password', 'AMAZON.AlphaNumeric',
     'What do you want to set as the password for your account?', []),
]


class Slot:
    def __init__(self, slot_name: str, slot_type: str, slot_prompt: str, required: bool = True):
        self.name = slot_name
        self.type = slot_type
        self.prompt = slot_prompt
        self.required = required

    @property
    def yaml(self):
        return {
            'name': self.name,
            'type': self.type,
            'prompt': self.prompt,
            'required': self.required
        }


class SlotProvider(BaseProvider):
    def __init__(
            self,
            slot: Slot,
            utterance_method=None,
            utterance_list: list = None,
            value_method=None,
            value_list: list = None,
            opening_utterances: list = None,
            builtin: bool = False,
            **config
    ):
        generator = Generator()
        super().__init__(generator)
        self.slot = slot
        conversational_name = value_method or slot.type or slot.name
        self.conversational_name = get_conversational_name(conversational_name)
        self.utterances = utterance_list or ['{}']
        self.opening_utterances = opening_utterances or []
        self.values = []
        if utterance_method:
            self._utterance = utterance_method
        object.__setattr__(self, f"{slot.name}_utterance", self._utterance)
        object.__setattr__(self, f"{slot.name}_utterances", self._utterances)
        object.__setattr__(self, f"{slot.name}_opening_utterance", self._opening_utterance)
        object.__setattr__(self, f"{slot.name}_prompt", self.prompt)
        if value_method:
            object.__setattr__(self, f"{slot.name}_value", value_method)
        if value_list:
            self.values = tuple(value_list)
            object.__setattr__(self, f"{slot.name}_value", self.random_element(self.values))

    @property
    def name(self):
        return self.slot.name

    @property
    def type(self):
        return self.slot.type

    @property
    def prompt(self):
        return self.slot.prompt

    @property
    def required(self):
        return self.slot.required

    def _utterance(self):
        return self.random_element(self.utterances)

    def _opening_utterance(self):
        if self.opening_utterances:
            return self.random_element(self.opening_utterances)
        return f"my {self.conversational_name} is {{}}"

    def _utterances(self):
        return self.utterances

    def prompt(self):
        return self.slot.prompt

    @property
    def yaml(self):
        if self.values:
            return {
                'name': self.type,
                'values': [
                    {'value': value}
                    for value in self.values
                ]
            }


class BuiltinSlotProvider(BaseProvider):
    def __init__(self, slot_type: str, **config):
        generator = Generator()
        super().__init__(generator)
        super().__init__(
            generator=generator
        )
        self.slot_name = amazon_attr(slot_type)
        self.utterances = AMAZON_UTTERANCES.get(slot_type)
        value_method = AMAZON_PROVIDERS.get(slot_type)
        self.builtin = True
        object.__setattr__(self, f"{self.slot_name}_utterance", self._utterance)
        object.__setattr__(self, f"{self.slot_name}_utterances", self._utterances)
        object.__setattr__(self, f"{self.slot_name}_opening_utterance", self._opening_utterance)
        if value_method:
            object.__setattr__(self, f"{self.slot_name}_value", value_method)

    def _utterance(self):
        return self.random_element(self.utterances)

    def _opening_utterance(self):
        if self.opening_utterances:
            return self.random_element(self.opening_utterances)
        return f"my {self.conversational_name} is {{}}"

    def _utterances(self):
        return self.utterances


PROVIDERS = [
    BuiltinSlotProvider(
        slot_type=amazon_slot_name,
    )
    for amazon_slot_name in AMAZON_PROVIDERS
]

announce = lambda x: cprint(x, 'white', attrs=['blink'])
agent = lambda x: cprint(x, 'grey', 'on_yellow', attrs=['bold'])
customer = lambda x: cprint(x.rjust(50), 'cyan', attrs=['bold'])


class Turn:
    def __init__(
            self,
            agent: str = False,
            sample_response: str = False,
            slot_to_elicit: str = False,
            intent_to_elicit: str = False,
            confirm_intent: bool = False,
            assume_intent: bool = False,
            close: bool = False
    ):
        self.agent = agent
        self.sample_response = sample_response
        self.slot_to_elicit = slot_to_elicit
        self.intent_to_elicit = intent_to_elicit
        self.confirm_intent = confirm_intent
        self.assume_intent = assume_intent
        self.close = close

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


class Conversation:
    pass


class Intent:
    def __init__(
            self,
            intent_name: str,
            domain: str = None,
            intent_description: str = None,
            scenario_id: str = None,
            sample_utterances: list[str] = None,
            opening_utterances: list[str] = None,
            slots: list[SlotProvider] = None,
            script: list[Turn] = None,
            parent_intent: str = None,
            locale: str = 'en-US'
    ):
        self.name = intent_name
        self.domain = domain
        self.locale = locale
        self.description = intent_description
        self.scenario_id = SingleQuotedScalarString(scenario_id)
        self.sample_utterances = sample_utterances
        self.opening_utterances = opening_utterances
        self.slots = slots
        self.script = script
        self.parent_intent = parent_intent

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


builtin_intents = (
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


class Utterer(SlotFaker):
    FALLBACK_INTENTS: list = [
        Intent(intent_name=intent_name, parent_intent=parent_intent)
        for (intent_name, parent_intent) in builtin_intents
    ]

    def __init__(self, intents: list = None, locale: str = 'en-US'):
        super().__init__()
        for provider in PROVIDERS:
            self.add_provider(provider)
        self.locale = locale
        self.conversations = {}
        self.intents = intents or []

    def add_slot_names(self, slot_names: list):
        for slot_name, slot_method, slot_type, slot_prompt, utterances in slot_names:
            slot_method_name = slot_method
            if 'amazon' in slot_method.lower():
                slot_method_name = f"{slot_method_name}_value"
            if not utterances:
                utterances = AMAZON_UTTERANCES.get(slot_type)
            self.add_provider(
                SlotProvider(
                    slot_name=slot_name,
                    slot_type=slot_type,
                    slot_prompt=slot_prompt,
                    utterances=utterances,
                    slot_method=getattr(self, f"{slot_method_name}")
                )
            )

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
        print('')
        time.sleep(1)
        customer(f"Customer: {opening}")
        print('')
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
            print('')
            time.sleep(1)
            customer(f"Customer: {customer_response}")
            print('')
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
                print(f"\t\t\t{key}: {value}")
            time.sleep(1)
            print('')

    def confirm_intent(self, confirm_intent: bool):
        agent("Agent: That's everything we need. Should I finalize your request?")
        print('')
        time.sleep(1)
        if confirm_intent:
            customer("Customer: Yes, please! Thanks!")
            print('')
            time.sleep(1)
            agent("Agent: You're all set!")
            print('')
            announce("Conversation completed.")
            return
        customer("Actually, let's hold off for right now. Thanks anyway for your help!")
        print('')
        time.sleep(1)
        agent("Agent: No worries. We're here if you change you're mind or have any questions. Have a nice day!")
        print('')
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


openings = [
    'I want to set up online banking',
    'I would like to set up online banking',
    'I\'m trying to set up online banking',
    'hello! im hoping to set up online banking',
    'Hi there! If possible, I want to set up an online banking profile. For starters, {}'
]

site = ACCOUNT.get_site('msteams_08dd34-AmazonLex-TestingDataLargeBot')
drive = site.get_default_document_library()
test = drive.get_item_by_path('Amazon Lex - Testing Data LargeBot', 'Archive', 'MediaCable Testing NEW.xlsx')
wb = WorkBook(test)
scws = wb.get_worksheet('Scripts')
scripts_range = scws.get_used_range()
sc_columns, *sc_values = scripts_range.values
df = pd.DataFrame(sc_values, columns=sc_columns)
mews = wb.get_worksheet('ValueMethods')
meths_range = mews.get_used_range()
meth_columns, *meth_values = meths_range.values



data = {}





for row in df.itertuples(name='row'):
    if row.IntentName not in data:
        data[row.IntentName] = {
            'intent_name': row.IntentName,
            'intent_description': row.IntentDescription,
            'domain': 'Media_Cable' if 'M' in row.IntentID else 'Finance',
            'scenario_id': SingleQuotedScalarString(f"202012{row.IntentID}".replace(' ', '')),
            'opening_utterances': [
                utterance
                for utterance in [
                    row.Customer1, row.Customer2, row.Customer3, row.Customer4,
                    row.Customer5, row.Customer6, row.Customer7, row.Customer8
                ]
                if utterance
            ],
            'script': [
                Turn(
                    **{
                        'agent': False,
                        'sample_response': False,
                        'slot_to_elicit': False,
                        'intent_to_elicit': row.IntentName,
                        'confirm_intent': False,
                        'assume_intent': False,
                        'close': False
                    }
                )
            ],
            'slots': []
        }
        continue
    data[row.IntentName]['script'].append(
        Turn(
            **{
                'agent': row.Agent,
                'sample_response': '',
                'slot_to_elicit': row.SlotName,
                'intent_to_elicit': False,
                'confirm_intent': False,
                'assume_intent': False,
                'close': False
            }
        )
    )
    if row.SlotName:
        data[row.IntentName]['slots'].append(
            SlotProvider(
                Slot(
                    **{
                        'slot_name': row.SlotName,
                        'slot_type': row.SlotTypeName,
                        'slot_prompt': row.Agent,
                        'required': row.SlotRequired
                    }
                ),
                utterance_method=row.Method
            )
        )

intents = []

for intent_name, intent_config in data.items():
    intents.append(
        Intent(**intent_config)
    )

'''
    if __name__ == '__main__':
        conversation_id = '12345'
        amazon = Utterer()
        amazon.converse(conversation_id, slot_names=slot_names, openings=openings[-1:], confirm_intent=random.getrandbits(1))
'''
