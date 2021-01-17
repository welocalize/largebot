import PySimpleGUI as sg
from typing import List, Union
from welo365 import WorkBook
import pandas as pd
from largebot.config import ACCOUNT
from largebot.logger import get_logger


logger = get_logger(__name__)

def get_col(i: int):
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    col = letters[(i % 26) - 1]
    if i > 26 and (index := i // 26):
        col = f"{letters[index - 1]}{col}"
    return col


class NewWindow:
    def __init__(self, name, layout):
        self.event = None
        self.values = None
        self.name = name
        self.layout = layout

    def __enter__(self):
        self.window = sg.Window(self.name, self.layout, resizable=True)
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def read(self):
        self.event, self.values = self.window.read()
        logger.info(self.event, self.values)

    def close(self):
        self.window.close()







class ScriptTurn:
    def __init__(
            self,
            index: int,
            agent: str,
            sample_response: Union[str, list],
            count: int,
            slot_to_elicit: Union[bool, str] = False,
            intent_to_elicit: Union[bool, str] = False,
            confirm_intent: bool = False,
            assume_intent: bool = False,
            close: bool = False,
            include_all: bool = True,
            visible: bool = True,
            key: str = None,
            additional_layout: list = None
    ):
        additional_layout = additional_layout or []
        self.index = index
        if key:
            index = f"{index}-{key}"
        self.agent = agent
        self.sample_response = sample_response if isinstance(sample_response, list) else [sample_response]
        self.slot_to_elicit = slot_to_elicit
        self.intent_to_elicit = intent_to_elicit
        self.confirm_intent = confirm_intent
        self.assume_intent = assume_intent
        self.close = close
        key = key or 'turn'
        self.key = f"{self.index}-{key}"
        basic_layout = [
            [
                sg.Text('Agent', enable_events=True),
                sg.InputText(self.agent, key=f"{index}-agent", enable_events=True)
            ],
            [
                sg.InputText(f"{{{self.slot_to_elicit}}}" if self.slot_to_elicit else '', key=f"{index}-customer", visible=bool(self.index != count), enable_events=True),
                sg.Text('Customer', visible=bool(self.index != count), enable_events=True)
            ],
            additional_layout
        ]
        right_col = [
            sg.VerticalSeparator(pad=None),
            sg.Column(
                [
                    [sg.Text('Possible Utterances:')],
                    [sg.Combo(values=self.sample_response, key=f"{index}-customer-utterances", visible=bool(self.index != count), enable_events=True)],
                    [sg.Text('Intent to elicit:', visible=bool(self.index == 1)), sg.InputText(intent_to_elicit or '', visible=bool(self.index == 1), size=(20, None))],
                    [sg.Text('Slot to elicit:', visible=bool(slot_to_elicit)), sg.InputText(slot_to_elicit or '', visible=bool(slot_to_elicit), size=(20, None))],
                    [sg.Text('Slot Type:', visible=bool(slot_to_elicit)), sg.InputText(visible=bool(slot_to_elicit), size=(20, None))]
                ],
                justification='center'
            )
        ] if index != count else []
        self.layout = [
            sg.Frame(
                layout=[
                    [
                        sg.Column(
                            basic_layout,
                            justification='center'
                        ),
                        *right_col
                    ]
                ] if include_all else basic_layout,
                title=f"{key.title()} {self.index}",
                relief=sg.RELIEF_SUNKEN if self.index % 2 == 0 else sg.RELIEF_RAISED,
                visible=visible,
                key=self.key
            )
        ]


class NewScriptTurn(ScriptTurn):
    def __init__(
            self,
            index: int,
            count: int,
            include_all: bool = True
    ):
        index += 1
        additional_layout = [
            sg.Text('New Slot'), sg.InputText(key=f"{index}-new_slot")
        ]
        super().__init__(
            index=index,
            agent='',
            sample_response='',
            count=count,
            include_all=include_all,
            visible=False,
            key='new_turn',
            additional_layout=additional_layout
        )


class Script:
    def __init__(self, turns: List[ScriptTurn], include_all: bool = True):
        self.turns = [
            ScriptTurn(
                index, **script_turn, count=len(turns), include_all=include_all
            )
            for index, script_turn in enumerate(turns, start=1)
        ]
        self.layout = [
            [
                sg.Column(
                    [
                        [sg.Sizer(22, 20)]
                    ],
                    justification='center'
                ),
                sg.Column(
                    [
                        self.turns[0].layout
                    ],
                    justification='center'
                )
            ],
            *[
                [
                    sg.Column(
                        [
                            [
                                sg.Column([[sg.Button('✚', key=f"{i}-add")]], justification='right'),
                                sg.Column(
                                    [
                                        [sg.Button('▲', key=f"{i}-up", visible=bool(i != 2))],
                                        [sg.Button('▼', key=f"{i}-down", visible=bool(i != len(turns) - 1))],
                                    ],
                                    justification='center'
                                ),
                                sg.Column([[sg.Button('✖', key=f"{i}-delete")]], justification='left')
                            ]
                        ],
                        justification='center'
                    ),
                    sg.Column(
                        [
                            turn.layout,
                            NewScriptTurn(i, count=len(turns) + 1, include_all=include_all).layout
                        ],
                        justification='center'
                    )
                ]
                for i, turn in enumerate(self.turns[1:-1], start=2)
            ],
            [
                sg.Column(
                    [
                        self.turns[-1].layout
                    ],
                    justification='center'
                )
            ]
        ]

class Conversation(NewWindow):
    def __init__(
            self,
            conversation,
            name: str,
            scenario_id: str,
            bias: List[str],
            customer_instructions: str,
            description: str,
            script: List[ScriptTurn],
            include_all: bool = True,
            **kwargs
    ):
        self.conversation = conversation
        self.scenario_id = scenario_id
        self.bias = bias
        self.customer_instructions = customer_instructions
        self.description = description
        self.script = Script(script, include_all=include_all)
        self.turns = len(script)
        self.added = []
        self.deleted = []
        layout = [
            [
                sg.Column(
                [[sg.Text(name.split('_')[1], justification='center', size=(30, 1), font=('Helvetica', 20, 'bold'))]],
                justification='center'
                )
            ],
            *self.script.layout,
            [
                sg.Button('Save Changes', key='save_changes'), sg.Exit(), sg.InputText(key='deleted_slots', visible=False), sg.InputText(key='added_slots', visible=False)
            ]
        ]
        super().__init__(name, layout)

    def read(self):
        while True:
            super().read()
            if 'up' in self.event:
                turn_index = int(self.event.split('-')[0])
                up_agent_key = f"{turn_index - 1}-agent"
                up_customer_key = f"{turn_index - 1}-customer"
                up_agent = self.values.get(up_agent_key)
                up_customer = self.values.get(up_customer_key)
                this_agent_key = f"{turn_index}-agent"
                this_customer_key = f"{turn_index}-customer"
                this_agent = self.values.get(this_agent_key)
                this_customer = self.values.get(this_customer_key)
                self.window[up_agent_key].update(this_agent)
                self.window[up_customer_key].update(this_customer)
                self.window[this_agent_key].update(up_agent)
                self.window[this_customer_key].update(up_customer)
            if 'down' in self.event:
                turn_index = int(self.event.split('-')[0])
                down_agent_key = f"{turn_index + 1}-agent"
                down_customer_key = f"{turn_index + 1}-customer"
                down_agent = self.values.get(down_agent_key)
                down_customer = self.values.get(down_customer_key)
                this_agent_key = f"{turn_index}-agent"
                this_customer_key = f"{turn_index}-customer"
                this_agent = self.values.get(this_agent_key)
                this_customer = self.values.get(this_customer_key)
                self.window[down_agent_key].update(this_agent)
                self.window[down_customer_key].update(this_customer)
                self.window[this_agent_key].update(down_agent)
                self.window[this_customer_key].update(down_customer)
            if 'add' in self.event:
                turn_index = int(self.event.split('-')[0])
                self.added.append(str(turn_index))
                self.window['added_slots'].update(','.join(self.added))
                self.window[f"{turn_index + 1}-new_turn"].update(visible=True)
                self.window.VisibilityChanged()
            if 'delete' in self.event:
                turn_index = int(self.event.split('-')[0])
                self.deleted.append(str(turn_index))
                self.window['deleted_slots'].update(','.join(self.deleted))
                for element in ('up', 'down', 'add', 'delete', 'turn'):
                    self.window[f"{turn_index}-{element}"].update(visible=False)
                self.window.VisibilityChanged()
            if self.event in (sg.WIN_CLOSED, 'OK', 'Exit', 'save_changes'):
                break
        values = None
        if self.event == 'save_changes':
            values = self.values
        return self.event, values


class NoConversation:
    name: 'No Conversation'


class IntentChooser(NewWindow):
    def __init__(self, template_link: str, name: str = 'Intent Chooser'):
        self.conversations, self.wb = self.get_conversations(template_link)
        self.conversation = NoConversation()
        self.completed = []
        self.generator = (
            window
            for conversation, window in self.conversations.values()
            if conversation.get('status') == 'Incomplete'
        )
        self._get_next()
        layout = [
            [
                sg.Text(
                    name,
                    justification='center',
                    size=(30, 1),
                    font=('Helvetica', 20, 'bold')
                )
            ],
            [
                sg.Text('Next Conversation: '), sg.Text(f"{self.conversation.name}", key='next_convo_name'), sg.Button('Open', key='open_convo')
            ],
            [
                sg.Text('Get Conversation by Id: '), sg.InputText(key='intent_id'), sg.Button('Get Conversation', key='get_convo')
            ],
            [sg.OK(), sg.Cancel()]
        ]
        '''
        conversation_columns = [
            (
                sg.Button(conversation_name, key=conversation_name),
                sg.Button(conversation.get('status'), key=f"{conversation_name}_status")
            )
            for conversation_name, (conversation, _) in self.conversations.items()
        ]
        batches = [
            conversation_columns[i:i + len(conversation_columns) // 6]
            for i in range(0, len(conversation_columns), len(conversation_columns) // 6)
        ]
        conversation_batches = [
            [
                sg.Column(
                    [
                        *[
                            [conversation_name]
                            for conversation_name, _ in batch
                        ]
                    ]
                ),
                sg.Column(
                    [
                        *[
                            [conversation_status]
                            for _, conversation_status in batch
                        ]
                    ]
                )
            ]
            for batch in batches
        ]
        layout = [
            [
                sg.Column(
                    [
                        [
                            sg.Text(
                                name,
                                justification='center',
                                size=(30, 1),
                                font=('Helvetica', 20, 'bold')
                            )
                        ]
                    ],
                    justification='center'
                )
            ],
            [
                sg.Column(
                    [
                        batch
                    ]
                )
                for batch in conversation_batches
            ],
            [sg.OK(), sg.Cancel()]
        ]
        '''
        super().__init__(name, layout)

    def __exit__(self, type, value, traceback):
        if self.completed:
            logger.info("Getting 'Updates' worksheet")
            ws = self.wb.get_worksheet('Updates')
            _range = ws.get_range(f"A1:{get_col(len(self.completed[0]))}{len(self.completed)}")
            _range.update(values=self.completed)
        super().__exit__(type, value, traceback)

    def _get_next(self):
        self.conversation = next(self.generator)

    @staticmethod
    def get_conversations(template_link: str):
        template = ACCOUNT.get_item_by_url(template_link)
        wb = WorkBook(template)
        scripts = wb.get_worksheet('Scripts')
        scripts_range = scripts.get_used_range()
        columns, *scripts_values = scripts_range.values
        scripts_df = pd.DataFrame(scripts_values, columns=columns)
        scripts_df.replace({'FALSE': False}, inplace=True)
        utterances = wb.get_worksheet('Utterances')
        utterances_range = utterances.get_used_range()
        utterances_values = utterances_range.values
        conversations = {}
        for i, row in enumerate(scripts_df.itertuples(name='row')):
            last_row = False
            if not row.SlotName and row.IntentID in conversations:
                last_row = True
            if row.IntentID not in conversations:
                turn_id = 0
                domain = 'Finance' if 'F' in row.IntentID else 'MediaCable'
                conversations[row.IntentID] = {
                    'conversation': None,
                    'status': 'Incomplete',
                    'name': f"{domain}_{row.IntentName}_en-US",
                    'scenario_id': row.IntentID.split()[1],
                    'bias': ['SingleIntent'],
                    'customer_instructions': 'Pretend you are interacting with a cable company and you want to add a new device to your plan.',
                    'description': row.IntentDescription,
                    'script': []
                }
            row_utterances = [
                utterance
                for utterance in utterances_values[i - 1]
                if utterance
            ]
            conversations[row.IntentID]['script'].append(
                {
                    'agent': row.Agent,
                    'sample_response': row_utterances,
                    'slot_to_elicit': row.SlotName,
                    'intent_to_elicit': row.IntentName if turn_id == 0 else False,
                    'assume_intent': row.AssumeIntent,
                    'confirm_intent': row.ConfirmIntent,
                    'close': last_row
                }
            )
            turn_id += 1
        return {
            conversation_name: (
                conversation, Conversation(**conversation, include_all=False)
            )
            for conversation_name, conversation in conversations.items()
        }, wb

    def read(self):
        while True:
            super().read()
            if self.event == 'open_convo':
                window = self.conversation
                self._get_next()
                self.window['next_convo_name'].update(self.conversation.name)
                with window as conversation_window:
                    conversation_window.read()
            if self.event == 'get_convo':
                intent_id = self.values.get('intent_id')
                logger.info(f"{intent_id=}")
                conversation_window = self.conversations.get(intent_id)[1]
                logger.info(f"{conversation_window=}")
                event, values = conversation_window.read()
                logger.info(f"{event=}, {values=}")
                if values:
                    logger.info('IntentChooser - ConversationWindow - SaveChanges')
                    conversation = []
                    deleted = [int(slot) for slot in values.get('deleted_slots').split(',')]
                    added = [int(slot) for slot in values.get('added_slots').split(',')]
                    for i in range(1, conversation_window.turns + 1):
                        if i in deleted:
                            continue
                        turn = [conversation_window.name]
                        new_turn = [conversation_window.name]
                        for element in ('agent', 'customer'):
                            turn.append(values.get(f"{i}-{element}", ''))
                            if i in added:
                                new_turn.append(values.get(f"{i}-new_turn-{element}", ''))
                        conversation.append(turn)
                        if len(new_turn) > 1:
                            new_turn[2] = values.get(f"{i}-new_slot", '')
                            conversation.append(new_turn)
                    self.completed.append(conversation)
                conversation_window.close()
                logger.info(f"Number of completed conversations: {len(self.completed)}")
            if self.event in (sg.WIN_CLOSED, 'OK', 'Exit', 'Cancel', 'save_changes'):
                break



class TemplateChooser(NewWindow):
    def __init__(self, name: str = 'TemplateSelection'):
        layout = [
            [sg.Text('Template Selection')],
            [sg.Text('Link to Excel Online Template File:'), sg.InputText(key='template_link')],
            [sg.OK(), sg.Cancel()]
        ]
        super().__init__(name=name, layout=layout)

    def read(self):
        while True:
            super().read()
            if self.event in (sg.WIN_CLOSED, 'Exit', 'Cancel'):
                break
            if self.event in ('OK', ):
                return self.values.get('template_link')


if __name__ == '__main__':
    # with TemplateChooser() as window:
        # template_link = window.read()
    template_link = 'https://welocalize.sharepoint.com/:x:/r/sites/msteams_08dd34-AmazonLex-LargeBot/_layouts/15/Doc.aspx?sourcedoc=%7B1364EF59-AB96-4FED-900C-DFB173326E79%7D&file=TestTemplates.xlsx&action=default&mobileredirect=true'
    with IntentChooser(template_link) as window:
        window.read()

'''
convo = {'conversation': None,
 'name': 'MediaCable_AddDevicePlan_en-US',
 'scenario_id': '2020001',
 'bias': ['SingleIntent'],
 'customer_instructions': 'Pretend you are interacting with a cable company and you want to add a new device to your plan.',
 'description': 'User wants to add an additional device to their plan',
 'script': [{'agent': 'Welcome. How can I help you?',
   'sample_response': 'I want to add a device to my plan',
   'slot_to_elicit': False,
   'intent_to_elicit': 'AddDevicePlan',
   'confirm_intent': False,
   'assume_intent': False,
   'close': False},
  {'agent': 'Can I please have your account number?',
   'sample_response': '333-321-455X1',
   'slot_to_elicit': 'AccountNumber',
   'intent_to_elicit': False,
   'confirm_intent': False,
   'assume_intent': False,
   'close': False},
  {'agent': 'What is your name?',
   'sample_response': 'Ramiro',
   'slot_to_elicit': 'CustomerFirstName',
   'intent_to_elicit': False,
   'confirm_intent': False,
   'assume_intent': False,
   'close': False},
  {'agent': 'Can I have your phone number?',
   'sample_response': '786-398-3421',
   'slot_to_elicit': 'PhoneNumber',
   'intent_to_elicit': False,
   'confirm_intent': False,
   'assume_intent': False,
   'close': False},
  {'agent': 'What type of phone would you like?',
   'sample_response': 'Smartphone',
   'slot_to_elicit': 'PhoneType',
   'intent_to_elicit': False,
   'confirm_intent': False,
   'assume_intent': False,
   'close': False},
  {'agent': 'Do you have a preferred device?',
   'sample_response': 'iPhone',
   'slot_to_elicit': 'Device',
   'intent_to_elicit': False,
   'confirm_intent': False,
   'assume_intent': False,
   'close': False},
  {'agent': 'Do you know your model number?',
   'sample_response': '12 256GB',
   'slot_to_elicit': 'ModelNumber',
   'intent_to_elicit': False,
   'confirm_intent': False,
   'assume_intent': False,
   'close': False},
  {'agent': 'Do you have your password?',
   'sample_response': 'los Olivos 0203',
   'slot_to_elicit': 'Password',
   'intent_to_elicit': False,
   'confirm_intent': False,
   'assume_intent': False,
   'close': False},
  {'agent': 'What is your PIN?',
   'sample_response': 9076,
   'slot_to_elicit': 'UserPIN',
   'intent_to_elicit': False,
   'confirm_intent': False,
   'assume_intent': False,
   'close': False},
  {'agent': 'Can you give me your email address?',
   'sample_response': 'ramiro.morales@gmail.com',
   'slot_to_elicit': 'EmailAddress',
   'intent_to_elicit': False,
   'confirm_intent': False,
   'assume_intent': False,
   'close': False},
  {'agent': 'Your new device has been added to your plan',
   'sample_response': False,
   'slot_to_elicit': False,
   'intent_to_elicit': False,
   'confirm_intent': False,
   'assume_intent': False,
   'close': True}]}

with Conversation(**convo) as convo:
    convo.read()
'''