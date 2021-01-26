import re
import time
from typing import List
from urllib.parse import urlparse, parse_qsl

import pymsteams
import requests
from pathlib import Path
from pydantic import BaseModel

BASE_URL = 'https://api.acs.projectdublin.com/v1'

admin_username = 'wl_admin_enUS_1'
admin_password = 'welo@1729'

customer_username = 'wl_user_enUS_47'
customer_password = 'welo7890'

agent_username = 'wl_bot_enUS_13'
agent_password = 'welo7890'

TESTING_WEBHOOK = 'https://outlook.office.com/webhook/b6df740f-912c-4f8e-aae2-f729af5204e1@d41d420e-6265-4ec2-aeb7-5869659e3fe2/IncomingWebhook/df46565468d04cd18b6c8165bd19730b/7c1980c0-388e-40b1-8f38-0fa7ad32141f'

definition = Path.home() / 'PyCharmProjects' / 'largebot' / 'out' / 'bot_definition_drop1.yaml'
template = Path.home() / 'PyCharmProjects' / 'largebot' / 'out' / 'bot_template_drop1.yaml'
defsample = Path.home() / 'PyCharmProjects' / 'largebot' / 'out' / 'CCT_TestData_BotDef.yaml'
tempsample = Path.home() / 'PyCharmProjects' / 'largebot' / 'out' / 'CCT_TestData_BotTemplate.yaml'
def_out = Path.home() / 'PyCharmProjects' / 'largebot' / 'out' / 'bot_definition_drop1a.yaml'
temp_out = Path.home() / 'PyCharmProjects' / 'largebot' / 'out' / 'bot_template_drop1a.yaml'


def get_token(username: str, password: str):
    url = f"{BASE_URL}/token/create"
    payload = {
        'agent': {
            'login': username,
            'password': password
        }
    }
    r = requests.post(url, json=payload)
    return r.json().get('token')


def validate_templates(bot_template, bot_definition):
    url = f"{BASE_URL}/scenario/validate"
    with open(bot_template, 'rb') as template:
        bot_file = template.read()
    with open(bot_definition, 'rb') as definition:
        scenario_file = definition.read()
    files = {
        'botFile': bot_file,
        'scenarioFile': scenario_file
    }
    data = {
        'token': get_token(admin_username, admin_password)
    }
    r = requests.post(url, files=files, data=data)
    return r


def get_query_dict(url: str):
    return dict(parse_qsl(urlparse(url).query))


class Token:
    url: str = f"{BASE_URL}/token/create"

    def __init__(self, username: str, password: str):
        self.token = requests.post(
            self.url, json={
                'agent': {
                    'login': username,
                    'password': password
                }
            }
        ).json().get('token')

    def keys(self):
        return ['token']

    def __getitem__(self, key):
        return self.__dict__[key]


def get_templates(token: Token):
    url = f"{BASE_URL}/agent/templates"
    r = requests.post(url, json={**token})
    return r.json().get('templates')


class Author:
    url: str = f"{BASE_URL}/conversation/present"

    def __init__(self, conversation_id: str, author_id: str, author_key: str):
        self.conversation_id = conversation_id
        self.author_id = author_id
        self.author_key = author_key

    def keys(self):
        return ['author_id', 'author_key']

    def __getitem__(self, key):
        return self.__dict__[key]

    @classmethod
    def get_agent(cls, template_id: str, token: Token):
        url = f"{BASE_URL}/conversation"
        agent_url = requests.post(
            url,
            json={
                'template_id': template_id,
                **token
            }
        ).json().get('agentURL')
        return cls(**get_query_dict(agent_url))

    @classmethod
    def get_customer(cls, token: Token):
        url = f"{BASE_URL}/conversation/queue/joinbest"
        customer_url = requests.post(
            url,
            json={
                **token
            }
        ).json().get('customerURL')
        return cls(**get_query_dict(customer_url))

    def update_present_state(self):
        url = f"{self.url}/{self.conversation_id}"
        r = requests.put(
            url,
            json={
                'author': {
                    **self
                },
                'present': True
            }
        )
        return r.json().get('successful')


class ConfigModel(BaseModel):
    class Config:
        arbitrary_types_allowed = True


class Slot(ConfigModel):
    required: bool
    type: str
    name: str


class Intent(ConfigModel):
    name: str
    slots: List[Slot]


class Template(ConfigModel):
    domain: str
    author_agent_id: str
    collection_reference: dict = None
    author_org_id: str
    done_collecting: bool
    collections_target: int = None
    bias: str
    intent: list
    bot_agent_config: dict = None
    created_timestamp: int
    definition_references: dict
    slots: list
    customer_instructions_visibile_to_agent: bool
    agent_organizations: list
    updated_timestamp: int
    turn_configurations: list
    intent_to_slot_mapping: dict = None
    name: str
    language: str
    agent_instructions: str
    mturk_hit_config: dict = None
    author: str
    scenario_id: float
    state: str
    version: int
    version_history: list
    customer_instructions: str
    inline_annotation_enabled: bool
    collections_completed: int
    template_id: str
    intents: List[Intent]
    customer_organizations: list

    @classmethod
    def get_template(cls, template_id: str):
        url = f"{BASE_URL}/template/{template_id}"
        attributes = requests.get(self.url).json()
        return cls(**attributes)

    @property
    def agent_prompts(self):
        return [
            turn.get('agent_prompt')
            for turn in self.turn_configurations
        ]


class Templates:
    def __init__(self):
        self.token = Token(admin_username, admin_password)
        url = f"{BASE_URL}/template/editor/templates"
        payload = {
            'chunk_key': None,
            'filters': {
                'sort_ascending': False,
                'sort_field': 'updated_timestamp'
            },
            **self.token
        }
        self.templates = [
            Template(**template)
            for template in requests.post(url, json=payload).json().get('templates')
        ]

    def __iter__(self):
        return iter(self.templates)

    def __getitem__(self, key):
        return self.templates[key]

    def send_teams_update(self):
        updates = [
            (template.name, template.collections_completed)
            for template in self.templates
        ]
        num_completed = len([update for update in updates if update[1] > 7])
        percent_completed = f"{(num_completed / len(updates) * 100):0.2f} %"
        text = f"""\n
        ---------- Conversation Progress Update ----------
        ---------- {num_completed} / {len(updates)} {percent_completed} ----------
        """
        for intent_name, completed in updates:
            text = f"""{text}
            {intent_name}:\t{completed} / 8 Conversations Completed
            """

        message = pymsteams.connectorcard(TESTING_WEBHOOK)
        message.summary('Conversation Progress Update')
        message.text(text)
        message.send()

def get_cust_instructions(slot_types: dict):
    customer_instructions = f"""    
    <div class="instructions" id="customer-instructions">
        In this task, you will be playing the Customer side of a customer service bot. Follow the directions found in the "Simulated Conversation with a Text Bot" guidelines.
        <br>
        IMPORTANT - Do not give any personal information to the bot! If it asks you for personal information, just make up something that sounds realistic.
        <br>
        ----------------
        Pretend you are interacting with this tool and want information about a certain kind of intent.
    </div>
    <br>
    
            <div>
            Please use the following information to answer the bot's questions.
            <br>"""
    for slot_type, values_list in slot_types.items():
        customer_instructions = f"""{customer_instructions}<br>
<b>{slot_type}</b> <br>"""
    customer_instructions = f"""{customer_instructions}<br>
            </div>
        

"""
    return customer_instructions

agent_instructions = """
        <div class="instructions" id="agent-instructions">
            In this task, you will be playing the Agent side of a customer service bot. Follow the directions found in the "Simulated Conversation with a Text Bot" guidelines.
            <br>
            IMPORTANT - Do not re-ask for information that the Customer gave you when they first made the request. Just skip over that prompt when you get to it.
        </div>
"""

class Conversation:
    url: str = f"{BASE_URL}/conversation"
    agent_username: str = agent_username
    agent_password: str = agent_password
    customer_username: str = customer_username
    customer_password: str = customer_password

    def __init__(self, template_id: str):
        self.template_id = template_id
        self.agent_token = Token(self.agent_username, self.agent_password)
        self.customer_token = Token(self.customer_username, self.customer_password)
        self.agent = Author.get_agent(self.template_id, self.agent_token)
        self.agent.update_present_state()
        self.customer = Author.get_customer(self.customer_token)
        self.conversation_id = self.agent.conversation_id
        self.template = Template(template_id)
        self.intent_name = self.template.intent_name
        self.statements = []

    def agent_response(self, content: str):
        self.agent.update_present_state()
        print(f"Agent: {content}")
        url = f"{self.url}/{self.conversation_id}"
        requests.post(
            url,
            json={
                'author': {
                    **self.agent
                },
                'content': content
            }
        )
        self.update_statements()

    def customer_response(self, content: str):
        self.customer.update_present_state()
        print(f"Customer: {content}")
        url = f"{self.url}/{self.conversation_id}"
        requests.post(
            url,
            json={
                'author': {
                    **self.customer
                },
                'content': content
            }
        )
        self.update_statements()

    def confirm_intent(self):
        self.agent.update_present_state()
        url = f"{self.url}/{self.conversation_id}/annotation/1"
        payload = {
            'author': {
                **self.agent
            },
            'payload': {
                'type': 'annotation',
                'value': [
                    {
                        'is_intent_present': True,
                        'intent_name': self.intent_name
                    }
                ],
                'activeContexts': [],
                'agentTurnActiveContexts': []
            }
        }
        r = requests.post(url, json=payload)
        return r.json().get('successful')

    def create_annotation(self, turn_id: int, offset: int, content: str, slot_name: str, slot_value: str):
        self.agent.update_present_state()
        url = f"{self.url}/{self.conversation_id}/annotation/{turn_id}"
        payload = {
            'author': {
                **self.agent
            },
            'payload': {
                'type': 'annotation',
                'value': [
                    {
                        'intent_name': self.intent_name,
                        'dialog_intent_name': 'ContentOnlyIntent',
                        'slots': [
                            {
                                'is_slot_present': True,
                                'slot_name': slot_name,
                                'offset': offset,
                                'slot_value': slot_value,
                                'utterance': content
                            }
                        ]
                    }
                ],
                'activeContexts': [],
                'agentTurnActiveContexts': []
            }
        }
        r = requests.post(url, json=payload)
        return r.json().get('successful')

    def update_statements(self):
        url = f"{self.url}/{self.conversation_id}"
        r = requests.get(url, headers={**self.agent_token})
        self.statements = r.json().get('statements')

    def exchange(self, agent_prompt: str, customer_response: str):
        self.agent_response(content=agent_prompt)
        time.sleep(3)
        self.customer_response(content=customer_response)
        time.sleep(3)

    def close(self, agent_rating: str = 'Good', notes: str = ''):
        url = f"{self.url}/{self.conversation_id}"
        payload = {
            'author': {
                **self.agent
            },
            'result': {
                'agent_rating': agent_rating,
                'notes': notes
            }
        }
        r = requests.delete(url, json=payload)
        return r.json().get('successful')

    def converse(self, customer_responses: list):
        agent_open = self.template.agent_prompts[0]
        customer_open = customer_responses[0][0]
        agent_close = self.template.agent_prompts[-1]
        self.exchange(agent_open, customer_open)
        self.confirm_intent()

        for i, agent_prompt in enumerate(self.template.agent_prompts[1:-1], start=1):
            print(f"{customer_responses[i][1]}: {customer_responses[i][2]}")
            self.exchange(agent_prompt, customer_responses[i][0])
            time.sleep(3)
            turn_id = i
            matches = re.search(re.escape(customer_responses[i][2]), customer_responses[i][0])
            print(f"{matches=}")
            if matches:
                offset = matches.span()[0]
                self.create_annotation(turn_id, offset, *customer_responses[i])

        self.agent_response(agent_close)
        self.close()
