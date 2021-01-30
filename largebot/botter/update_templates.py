import requests
from pathlib import Path
from largebot.acs import Token
from ruamel.yaml import YAML
import re
from welo365 import O365Account
import massedit

from largebot.yaml_gen.yamlate import DomainScript

me = O365Account()
links = {
    'MediaCable': 'https://welocalize.sharepoint.com/:x:/r/sites/msteams_08dd34-AmazonLex-TestingDataLargeBot/_layouts/15/Doc.aspx?sourcedoc=%7B9E6CCE46-60B9-4D49-9D05-C2DAD3464F14%7D&file=MediaCable%20Testing%20NEW.xlsx&action=default&mobileredirect=true',
    'Finance': 'https://welocalize.sharepoint.com/:x:/r/sites/msteams_08dd34-AmazonLex-TestingDataLargeBot/_layouts/15/Doc.aspx?sourcedoc=%7BCC07F723-3EA3-4F2D-8B5F-CA32B9A5E03F%7D&file=Finance%20Testing%201.27.21%20NEW.xlsx&action=default&mobileredirect=true'
}
domain = 'Finance'
xl = me.search(links.get(domain))

test = DomainScript(source=xl)
bias = test.export_template(f"LargeBot_{domain}_Update", 'en-US', domain)
templates = []
for template in test.templates.values():
    temp = template.copy()
    del temp['alternate_scripts']
    templates.append(temp)

admin_username = 'wl_admin_enUS_1'
admin_password = 'welo@1729'

token = Token.get(admin_username, admin_password)

SCENARIOS = Path.cwd() / 'scenarios'
SCENARIOS.mkdir(exist_ok=True)
name = f"LargeBot_{domain}_scenarios_batch"
locale = 'en-US'
batches = [templates[i:i + 50] for i in range(0, len(templates), 50)]
for i, batch in enumerate(batches, start=1):
    batch_name = f"{name}{i:02d}"
    print(batch_name)
    template = {
        'name': batch_name,
        'locale': locale,
        'domain': domain,
        'general_agent_instructions': 'In this task, you will be playing the Agent side of a customer service bot. Follow the directions found in the "Simulated Conversation with a Text Bot" guidelines.',
        'general_customer_instructions': 'In this task, you will be playing the Customer side of a customer service bot. Follow the directions found in the "Simulated Conversation with a Text Bot" guidelines.',
        'slot_filled_instructions': 'IMPORTANT - Do not re-ask for information that the Customer gave you when they first made the request. Just skip over that prompt when you get to it.',
        'custom_slot_instructions': "Please use the following information to answer the bot's questions.",
        'personal_information': 'IMPORTANT - Do not give any personal information to the bot! If it asks you for personal information, just make up something that sounds realistic.',
        'agent_did_not_understand': 'Sorry, I did not understand. Goodbye!',
        'conversations': batch
    }
    outfile = SCENARIOS / f"{batch_name}.yaml"
    yaml = YAML()
    yaml.width = 200
    yaml.indent(mapping=2, sequence=4, offset=2)
    with open(outfile, mode='w', encoding='utf-8') as outf:
        yaml.dump(template, outf)
    with open(outfile, 'r') as f:
        data = f.read()
        data = re.sub(r'\'False\'', 'false', data)
    with open(outfile, 'w') as f:
        f.write(data)

# token = 'f222853c-0023-450f-8031-0b5a92a63369'
update_url = 'https://api.acs.projectdublin.com/v1/scenario/update'
validate_url = 'https://api.acs.projectdublin.com/v1/scenario/validate'
errors = []


def update(bot, scenarios):
    with open(bot, 'r') as botFile, open(scenarios, 'r') as scenarioFile:
        files = {
            'botFile': botFile,
            'scenarioFile': scenarioFile
        }
        payload = {**token}
        r = requests.post(update_url, data=payload, files=files)
        return r.json().get('valid')


def validate(bot, scenarios):
    with open(bot, 'r') as botFile, open(scenarios, 'r') as scenarioFile:
        files = {
            'botFile': botFile,
            'scenarioFile': scenarioFile
        }
        payload = {**token}
        r = requests.post(validate_url, data=payload, files=files)
        return r.json()


def upload_batchs():
    batches = list(SCENARIOS.iterdir())
    batches.sort()
    if '.DS' in batches[0].name:
        batches = batches[1:]
    bot = Path.cwd().parent / 'yaml_gen' / f"LargeBot_{domain}_definition.yaml"
    failed = []
    for batch in batches:
        print(batch.name)
        if (r := validate(bot, batch)):
            if not r.get('valid'):
                failed.append(batch.name)
                print(f"{batch.name} failed validation")
                for error in r.get('errors'):
                    errors.append(error)
                    print(f"\t{error}")
                continue
        if not update(bot, batch):
            continue
        print(f"{batch.name} uploaded successfully.")
