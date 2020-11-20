import pymsteams
from welo365.account import O365Account
from O365.excel import WorkBook
import pandas as pd
import datetime
import numpy as np


def send_teams_update(TASK: str = 'Intent', STEP: str = 'Creator'):
    account = O365Account(site='AIEnablementPractice')

    AIE_PATH = [
        'Amazon Web Services, Inc',
        'Bot Training & Testing Data (LargeBot)',
        'Production Planning',
        'Files for Processing',
        'Intent_Intent IDs Keys'
    ]
    KEY_FOLDER = account.get_folder(*AIE_PATH)

    def get_values(domain):
        filename = f"{domain}_Intent Key.xlsx"
        item = KEY_FOLDER.get_item(filename)
        wb = WorkBook(item, use_session=False, persist=False)
        ws = wb.get_worksheet('Files')
        _range = ws.get_range(f"{domain}Summary")
        return _range.values

    values = []
    for domain in ['Finance', 'Media_Cable']:
        _values = get_values(domain)
        headers = _values[0]
        values.extend(_values[1:])


    df = pd.DataFrame(values, columns=headers)
    df['Domain'] = df['IntentFileName'].apply(lambda x: 'Finance' if x.split('_')[3] == 'Fi' else 'Media_Cable')

    STATUS = pd.crosstab(df.Domain, df[f"{TASK}{STEP}Status"])
    FI_STATS, MC_STATS = STATUS.values.tolist()

    WEBHOOK = 'https://outlook.office.com/webhook/b6df740f-912c-4f8e-aae2-f729af5204e1@d41d420e-6265-4ec2-aeb7-5869659e3fe2/IncomingWebhook/5a3c1efd0aca4a9b8e001bede0e5934e/7c1980c0-388e-40b1-8f38-0fa7ad32141f'

    my_teams_message = pymsteams.connectorcard(WEBHOOK)
    my_teams_message.text(f"{TASK} {STEP} Progress")
    # section.title(f"{datetime.datetime.utcnow().strftime('%H:%M GMT %d-%b')}")
    for domain, stats in [('Finance', FI_STATS), ('Media_Cable', MC_STATS)]:
        completed, in_progress, not_started = stats
        section = pymsteams.cardsection()
        section.title(f"{domain} Totals")
        section.addFact('Completed', completed)
        section.addFact('In Progress', in_progress)
        section.addFact('Not Started', not_started)
        my_teams_message.addSection(section)

    my_teams_message.send()