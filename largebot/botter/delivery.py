from largebot.yaml_gen.yamlate import DomainScript
from largebot.acs import Templates, Conversation, AsyncConversation, Token
from welo365 import O365Account, WorkBook
from rypy import rex
from largebot.logger import get_logger
import re
import asyncio
from functools import partial
import logging
import os
from queue import Queue
from threading import Thread
from time import time




logger = get_logger(__file__)



class CustomerResponses:
    def __init__(self, turns: list):
        self.responses = []
        self.turns = turns
        slot_bank = turns[0].get('slot_bank', {})
        logger.info(f"{slot_bank=}")
        self.slots = slot_bank
        slots_covered = []
        for turn in turns:
            content = turn.get('sample_response')
            slots = []
            slot_name = turn.get('slot_to_elicit')
            intent = turn.get('intent_to_elicit') or turn.get('confirm_intent')
            intent = str(intent) if intent else intent
            if intent in ('ConfirmedIntent', 'DeniedIntent'):
                intent = intent.replace('Intent', '')
            if slot_name and slot_name in slots_covered:
                continue
            slot_value = turn.get('slot_value')
            slot_value = str(slot_value) if slot_value else slot_value
            if slot_name and slot_value:
                slots.append((slot_name, slot_value))
            slot_names = rex.capture_all(r'\{(?P<slot_name>[\w\d_\.]+)\}', content).get('slot_name')
            if slot_names:
                format_map = {}
                for slot_name in slot_names:
                    slot_value = self.slots.get(slot_name) or f"{{{slot_name}}}"
                    slot_value = str(slot_value) if slot_value else slot_value
                    slots.append((slot_name, slot_value))
                    slots_covered.append(slot_name)
                    if slot_value:
                        format_map[slot_name] = slot_value
                content = content.format_map(format_map)
            self.responses.append(
                {
                    'content': content,
                    'slots': slots,
                    'intent': intent,
                    'agent': [
                        self.slots.get(slot_name).get('agent')
                        for slot_name, _ in slots
                    ]
                }
            )

    def is_valid(self):
        for response in self.responses:
            if (slots := response.get('slots')) and (content := response.get('content')):
                if re.search(r'[{}]', content):
                    return False
                for slot_name, slot_value in slots:
                    if slot_value and not re.search(
                            re.escape(slot_value),
                            content,
                            flags=re.DOTALL | re.IGNORECASE
                    ):
                        return False
        return True

    def __iter__(self):
        return iter(self.responses)

    def __len__(self):
        return len(self.responses)




def get_templates():
    TEMPLATES = Templates().templates
    if (IN_COLLECTION := Templates(state='IN_COLLECTION_TEMPLATE').templates):
        TEMPLATES.extend(IN_COLLECTION)
    if (COMPLETED := Templates(state='COMPLETED_TEMPLATE').templates):
        TEMPLATES.extend(COMPLETED)

    TEMPLATES = [
        T
        for T in TEMPLATES
        if ('Denied' not in T.name and 'Confirmed' not in T.name)
    ]

    TEMPLATES.sort(key=lambda x: x.name.split('_')[-2])

    return {
        template.name: template
        for template in TEMPLATES
    }

def get_intents(templates):
    me = O365Account()
    mc_xl = me.search(
        'https://welocalize.sharepoint.com/:x:/r/sites/msteams_08dd34-AmazonLex-TestingDataLargeBot/_layouts/15/Doc.aspx?sourcedoc=%7B9E6CCE46-60B9-4D49-9D05-C2DAD3464F14%7D&file=MediaCable%20Testing%20NEW.xlsx&action=default&mobileredirect=true')
    mc_script = DomainScript(source=mc_xl)
    _ = mc_script.export_template('DNU', 'en-US', 'MediaCable')
    return {
        convo_name: [
            customer_responses
            for template in templates
            if (
                    (customer_responses := CustomerResponses(template))
                    and customer_responses.is_valid()
            )

        ]
        for intent in mc_script.intents
        for convo_name, templates in intent.items()
        if 'MediaCable' in convo_name.split('_')[0]
    }

def get_upload_functions(templates, intents, dry_run: bool = True):
    convos = []
    for template_name, template in templates.items():
        if (scripts := intents.get(template_name, [])):
            logger.info(f"Getting conversation for {template_name}")
            collections_target = template.collections_target or 0
            new_target = len(scripts) - collections_target
            template.update_collections_target(new_target)
            conversation = Conversation(template.template_id, dry_run=dry_run)
            for i, script in enumerate(scripts, start=1):
                convo = partial(conversation.converse, customer_responses=script.responses)
                convos.append((f"template_name{i}", convo))
    return convos


def have_conversation(convo_name, convo):
    logger.info(f"Having conversation: {convo_name}")
    convo()




class RyanBot(Thread):

    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            # Get the work from the queue and expand the tuple
            convo_name, convo = self.queue.get()
            try:
                have_conversation(convo_name, convo)
            finally:
                self.queue.task_done()


def main(dry_run: bool = True):
    ts = time()

    logger.info("Getting templates")
    templates = get_templates()
    logger.info("Getting intents")
    intents = get_intents(templates)
    logger.info("Getting conversations")
    convos = get_upload_functions(templates, intents, dry_run=dry_run)

    # Create a queue to communicate with the worker threads
    queue = Queue()
    # Create 8 worker threads
    for x in range(8):
        worker = RyanBot(queue)
        # Setting daemon to True will let the main thread exit even though the workers are blocking
        worker.daemon = True
        worker.start()
    # Put the tasks into the queue as a tuple
    for convo in convos:
        logger.info('Queueing {}'.format(convo[0]))
        queue.put(convo)
    # Causes the main thread to wait for the queue to finish processing all the tasks
    queue.join()
    logger.info('Took %s', time() - ts)

if __name__ == '__main__':
    main()


