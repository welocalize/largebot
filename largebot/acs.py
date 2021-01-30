import re
import time
from typing import List
from urllib.parse import urlparse, parse_qsl

import pymsteams
import requests
import random
from pathlib import Path
from pydantic import BaseModel
from termcolor import cprint
import asyncio
from aiohttp import ClientSession
from largebot.logger import get_logger

logger = get_logger(__file__)


announce = lambda x: cprint(x, 'white', attrs=['blink'])
agent = lambda x: cprint(x, 'white', 'on_magenta', attrs=['dark', 'bold'])
customer = lambda x: cprint(x.rjust(50), 'red', 'on_yellow', attrs=['bold', 'dark'])

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

    def __init__(self, token: str):
        self.token = token

    @classmethod
    def get(cls, username: str, password: str):
        url = f"{BASE_URL}/token/create"
        token = requests.post(
            url, json={
                'agent': {
                    'login': username,
                    'password': password
                }
            }
        ).json().get('token')
        return cls(token)

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
        r = requests.post(
            url,
            json={
                **token
            }
        )
        print(f"{r.json()=}")
        customer_url = r.json().get('customerURL')
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


class AsyncAuthor:
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
    async def get_agent(cls, template_id: str, token: Token):
        url = f"{BASE_URL}/conversation"
        async with ClientSession() as session:
            async with session.post(
                url,
                json={
                    'template_id': template_id,
                    **token
                }
            ) as resp:
                r = await resp.json()
                agent_url = r.get('agentURL')
                return cls(**get_query_dict(agent_url))

    @classmethod
    async def get_customer(cls, token: Token):
        url = f"{BASE_URL}/conversation/queue/joinbest"
        async with ClientSession() as session:
            async with session.post(
                url,
                json={
                    **token
                }
            ) as resp:
                r = await resp.json()
                customer_url = r.get('customerURL')
                return cls(**get_query_dict(customer_url))

    async def update_present_state(self):
        url = f"{self.url}/{self.conversation_id}"
        async with ClientSession() as session:
            async with session.post(
                url,
                json={
                    'author': {
                        **self
                    },
                    'present': True
                }
            ) as resp:
                r = await resp.json()
                return r.get('successful')


class ConfigModel(BaseModel):
    class Config:
        arbitrary_types_allowed = True


class Slot(ConfigModel):
    required: bool
    type: str = None
    name: str = None


class Intent(ConfigModel):
    name: str
    slots: List[Slot]

    def __str__(self):
        return self.name


class Template(ConfigModel):
    token: Token = None
    domain: str = None
    author_agent_id: str = None
    collection_reference: dict = None
    author_org_id: str = None
    done_collecting: bool = None
    collections_target: int = None
    bias: str = None
    intent: list = None
    bot_agent_config: dict = None
    created_timestamp: int = None
    definition_references: dict = None
    slots: list = None
    customer_instructions_visibile_to_agent: bool
    agent_organizations: list = None
    updated_timestamp: int = None
    turn_configurations: list = None
    intent_to_slot_mapping: dict = None
    name: str = None
    language: str
    agent_instructions: str
    mturk_hit_config: dict = None
    author: str = None
    scenario_id: float = None
    state: str = None
    version: int = None
    version_history: list = None
    customer_instructions: str
    inline_annotation_enabled: bool
    collections_completed: int = None
    template_id: str = None
    intents: List[Intent] = None
    customer_organizations: list = None

    @classmethod
    def get_template(cls, template_id: str, token: Token):
        url = f"{BASE_URL}/template/{template_id}"
        attributes = requests.get(url).json()
        return cls(**attributes, token=token)

    @property
    def agent_prompts(self):
        return [
            turn.get('agent_prompt')
            for turn in self.turn_configurations
        ]

    def delete(self):
        url = f"{BASE_URL}/template/{self.template_id}"
        payload = {**self.token}
        r = requests.delete(url, json=payload)
        return r.json().get('successful')

    def update_collections_target(self, target: int = None):
        target = target or 1
        current_target = self.collections_target or 0
        current_target += target
        url = f"{BASE_URL}/template"
        payload = {
            'template_id': self.template_id,
            'name': self.name,
            'domain': self.domain,
            'bias': self.bias,
            'intent': self.intent,
            'slots': self.slots,
            'collection_reference': self.collection_reference,
            'language': self.language,
            'collections_target': current_target,
            'agent_organizations': self.agent_organizations,
            'customer_organizations': self.customer_organizations,
            'mturk_hit_config': self.mturk_hit_config,
            'bot_agent_config': self.bot_agent_config,
            'customer_instructions_visibile_to_agent': self.customer_instructions_visibile_to_agent,
            'inline_annotation_enabled': self.inline_annotation_enabled,
            'agent_instructions': self.agent_instructions,
            'customer_instructions': self.customer_instructions,
            **self.token
        }
        r = requests.post(url, json=payload)
        return r.json()

    async def async_update_collections_target(self, target: int):
        collections_target = self.collections_target or 0
        collections_target += target
        url = f"{BASE_URL}/template"
        payload = {
            'template_id': self.template_id,
            'name': self.name,
            'domain': self.domain,
            'bias': self.bias,
            'intent': self.intent,
            'slots': self.slots,
            'collection_reference': self.collection_reference,
            'language': self.language,
            'collections_target': current_target,
            'agent_organizations': self.agent_organizations,
            'customer_organizations': self.customer_organizations,
            'mturk_hit_config': self.mturk_hit_config,
            'bot_agent_config': self.bot_agent_config,
            'customer_instructions_visibile_to_agent': self.customer_instructions_visibile_to_agent,
            'inline_annotation_enabled': self.inline_annotation_enabled,
            'agent_instructions': self.agent_instructions,
            'customer_instructions': self.customer_instructions,
            **self.token
        }
        async with ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                return await resp.json()


class Templates:
    def __init__(self, state: str = 'PARTIAL_TEMPLATE', token: str = None):
        self.token = Token(token) if token else Token.get(admin_username, admin_password)

        def get_templates(chunk_key: dict = None):
            url = f"{BASE_URL}/template/editor/templates"
            payload = {
                'filters': {
                    'sort_ascending': False,
                    'sort_field': 'updated_timestamp',
                    'state': state
                },
                **self.token
            }
            if chunk_key:
                chunk_key['updated_timestamp'] = int(chunk_key['updated_timestamp'])
                payload['chunk_key'] = chunk_key
            r = requests.post(url, json=payload)
            resp_templates = r.json().get('templates')
            templates = [
                Template(token=self.token, **template)
                for template in resp_templates
            ] if resp_templates else None
            if templates and (chunk_key := r.json().get('chunk_key', None)):
                more_templates = get_templates(chunk_key=chunk_key)
                if more_templates:
                    templates += more_templates
            return templates

        self.templates = get_templates()

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
def get_tokens():
    pair = random.randint(1, 50)
    password = 'welo7890'
    agent = f"wl_bot_enUS_{pair}"
    cust = f"wl_user_enUS_{pair}"
    return Token.get(agent, password), Token.get(cust, password)


class ScriptGenerator:
    def __init__(self, turns: list):
        self.turns = turns

    def __iter__(self):
        return iter(self.turns)

    def __next__(self):
        try:
            return next(iter(self))
        except StopIteration as e:
            logger.error(f"No turns remain: {e}")
            return None



class Conversation:
    url: str = f"{BASE_URL}/conversation"

    def __init__(self, template_id: str, dry_run: bool = False):
        self.dry_run = dry_run
        self.template_id = template_id
        self.agent_token, self.customer_token = get_tokens()
        self.template = Template.get_template(template_id, token=self.agent_token)
        self.intents = self.template.intents
        self.statements = []
        self.successful = True
        if not self.dry_run:
            self.agent = Author.get_agent(self.template_id, self.agent_token)
            self.agent.update_present_state()
            self.customer = Author.get_customer(self.customer_token)
            self.conversation_id = self.agent.conversation_id

    @property
    def intent_name(self):
        return f"{self.intents[0]!s}" if self.intents else None

    def agent_response(self, content: str):
        agent(f"Agent: {content}")
        if not self.dry_run:
            url = f"{self.url}/{self.conversation_id}"
            self.agent.update_present_state()
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
        customer(f"Customer: {content}")
        if not self.dry_run:
            url = f"{self.url}/{self.conversation_id}"
            self.customer.update_present_state()
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

    '''
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
        self.successful = r.json().get('successful')
    '''

    def create_annotation(self, turn_id: int, customer_response: dict = None):
        intent_to_elicit = customer_response.get('intent', None)
        slots_to_elicit = customer_response.get('slots', None)
        if not intent_to_elicit and not slots_to_elicit:
            return
        payload = {
            'payload': {
                'type': 'annotation',
                'value': [
                    {
                        'intent_name': intent_to_elicit or self.intent_name
                    }
                ],
                'activeContexts': [],
                'agentTurnActiveContexts': []
            }
        }
        dialog_intent_name = 'ContentOnlyIntent'
        if intent_to_elicit:
            payload['payload']['value'][0]['is_intent_present'] = True
            dialog_intent_name = intent_to_elicit
        if dialog_intent_name != self.intent_name:
            payload['payload']['value'][0]['dialog_intent_name'] = dialog_intent_name
        if slots_to_elicit:
            for slot_name, slot_value in slots_to_elicit:
                print(slot_name, slot_value)
                matches = re.search(re.escape(slot_value), customer_response.get('content'), re.IGNORECASE)
                if matches:
                    offset = matches.span()[0]
                    payload['payload']['value'][0].setdefault('slots', []).append(
                        {
                            'is_slot_present': True,
                            'slot_name': slot_name,
                            'offset': offset,
                            'slot_value': slot_value,
                            'utterance': customer_response.get('content')
                        }
                    )
        if self.dry_run:
            announce(f"{payload=}")
            return
        url = f"{self.url}/{self.conversation_id}/annotation/{turn_id}"
        payload['author'] = {**self.agent}
        self.agent.update_present_state()
        r = requests.post(url, json=payload)
        self.successful = r.json().get('successful')

    def update_statements(self):
        url = f"{self.url}/{self.conversation_id}"
        r = requests.get(url, headers={**self.agent_token})
        self.statements = r.json().get('statements')

    def exchange(self, agent_prompt: str, customer_response: str):
        self.agent_response(content=agent_prompt)
        time.sleep(round(random.random(), 1))
        self.customer_response(content=customer_response)
        time.sleep(round(random.random(), 1))

    def close(self, agent_rating: str = 'Good', notes: str = ''):
        payload = {
            'result': {
                'agent_rating': agent_rating,
                'notes': notes
            }
        }
        if self.dry_run:
            announce(f"{payload=}")
            return payload
        url = f"{self.url}/{self.conversation_id}"
        payload['author'] = {**self.agent}
        r = requests.delete(url, json=payload)
        return r.json().get('successful')

    def converse(self, customer_responses: list):
        collected_slots = []
        agent_script = self.template.turn_configurations[:-1]
        agent = ScriptGenerator(agent_script)
        customer = ScriptGenerator(customer_responses)
        for turn_id in range(1, len(customer_responses)*2+1, 2):
            agent_response = next(agent)
            if agent_response.get('slot_to_elicit') in collected_slots:
                agent_response = next(agent)
            if not agent_response:
                if (agent_response := customer_response.get('agent', [])) and len(agent_response) == 1:
                    agent_response = agent_response[0]
                    if not agent_response:
                        return self.close(
                            agent_rating='Poor',
                            notes='Missing agent response'
                        )
            customer_response = next(customer)
            self.exchange(agent_response.get('agent_prompt'), customer_response.get('content'))
            time.sleep(round(random.random(), 1))
            self.create_annotation(turn_id, customer_response)
            if slots := customer_response.get('slots'):
                for slot_name, _ in slots:
                    collected_slots.append(slot_name)

        self.agent_response(self.template.agent_prompts[-1])
        return self.close()


class AsyncConversation:
    url: str = f"{BASE_URL}/conversation"
    agent_username: str = agent_username
    agent_password: str = agent_password
    customer_username: str = customer_username
    customer_password: str = customer_password

    def __init__(self, template_id: str):
        self.template_id = template_id
        self.agent_token = Token.get(self.agent_username, self.agent_password)
        self.customer_token = Token.get(self.customer_username, self.customer_password)
        self.get_users()
        self.conversation_id = self.agent.conversation_id
        self.template = Template.get_template(template_id, token=self.agent_token)
        self.intents = self.template.intents
        self.statements = []
        self.successful = True

    async def async_get_users(self):
        self.agent = await AsyncAuthor.get_agent(self.template_id, self.agent_token)
        await self.agent.update_present_state()
        self.customer = await AsyncAuthor.get_customer(self.customer_token)

    def get_users(self):
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(async_get_users())
        except Exception as e:
            print(e)

    @property
    def intent_name(self):
        return f"{self.intents[0]!s}" if self.intents else None

    async def agent_response(self, content: str):
        await self.agent.update_present_state()
        agent(f"Agent: {content}")
        url = f"{self.url}/{self.conversation_id}"
        async with ClientSession() as session:
            async with session.post(
                url,
                json={
                    'author': {
                        **self.agent
                    },
                    'content': content
                }
            ) as resp:
                await resp
                await self.update_statements()

    async def customer_response(self, content: str):
        await self.customer.update_present_state()
        customer(f"Customer: {content}")
        url = f"{self.url}/{self.conversation_id}"
        async with ClientSession() as session:
            async with session.post(
                url,
                json={
                    'author': {
                        **self.customer
                    },
                    'content': content
                }
            ) as resp:
                await resp
                await self.update_statements()

    async def create_annotation(self, turn_id: int, customer_response: dict = None):
        await self.agent.async_update_present_state()
        intent_to_elicit = customer_response.get('intent', None)
        slots_to_elicit = customer_response.get('slots', None)
        if not intent_to_elicit and not slots_to_elicit:
            return
        url = f"{self.url}/{self.conversation_id}/annotation/{turn_id}"
        payload = {
            'author': {
                **self.agent
            },
            'payload': {
                'type': 'annotation',
                'value': [
                    {
                        'intent_name': intent_to_elicit or self.intent_name
                    }
                ],
                'activeContexts': [],
                'agentTurnActiveContexts': []
            }
        }
        if intent_to_elicit:
            payload['payload']['value'][0]['is_intent_present'] = True
        if slots_to_elicit:
            for slot_name, slot_value in slots_to_elicit:
                print(slot_name, slot_value)
                matches = re.search(re.escape(slot_value), customer_response.get('content'), re.IGNORECASE)
                if matches:
                    offset = matches.span()[0]
                    payload['payload']['value'][0].setdefault('slots', []).append(
                        {
                            'is_slot_present': True,
                            'slot_name': slot_name,
                            'offset': offset,
                            'slot_value': slot_value,
                            'utterance': customer_response.get('content')
                        }
                    )
        async with ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                r = await resp.json()
                self.successful = r.json().get('successful')

    async def update_statements(self):
        url = f"{self.url}/{self.conversation_id}"
        async with ClientSession() as session:
            async with session.get(
                    url,
                    headers={
                        **self.agent_token
                    }
            ) as resp:
                r = await resp.json()
                self.statements = r.get('statements')

    async def exchange(self, agent_prompt: str, customer_response: str):
        self.agent_response(content=agent_prompt)
        await asyncio.sleep(round(random.random(), 1))
        self.customer_response(content=customer_response)
        await asyncio.sleep(round(random.random(), 1))

    async def close(self, agent_rating: str = 'Good', notes: str = ''):
        if self.successful:
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
            async with ClientSession() as session:
                async with session.delete(url, json=payload) as resp:
                    r = await resp.json()
                    self.successful = r.get('successful')

    async def converse(self, customer_responses: list):
        tasks = []
        collected_slots = []
        agent = ScriptGenerator(self.template.turn_configurations[:-1])
        customer = ScriptGenerator(customer_responses)
        for turn_id in range(1, len(customer_responses)*2+1, 2):
            agent_response = next(agent)
            if agent_response.get('slot_to_elicit') in collected_slots:
                agent_response = next(agent)
            customer_response = next(customer)
            tasks.append(await self.exchange(agent_response.get('agent_prompt'), customer_response.get('content')))
            tasks.append(await asyncio.sleep(round(random.random(), 1)))
            tasks.append(await self.create_annotation(turn_id, customer_response))
            if slots := customer_response.get('slots'):
                for slot_name, _ in slots:
                    collected_slots.append(slot_name)

        self.agent_response(self.template.agent_prompts[-1])
        await asyncio.gather(tasks)
        await self.close()
        return self