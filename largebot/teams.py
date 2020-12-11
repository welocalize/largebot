import pymsteams
from welo365.account import O365Account
from O365.excel import WorkBook
import pandas as pd
from largebot.largebotter import FileBook

WEBHOOK = 'https://outlook.office.com/webhook/b6df740f-912c-4f8e-aae2-f729af5204e1@d41d420e-6265-4ec2-aeb7-5869659e3fe2/IncomingWebhook/5a3c1efd0aca4a9b8e001bede0e5934e/7c1980c0-388e-40b1-8f38-0fa7ad32141f'
DEV_WEBHOOK = 'https://outlook.office.com/webhook/1db85346-a351-4611-8184-de0fba3b2de6@d41d420e-6265-4ec2-aeb7-5869659e3fe2/IncomingWebhook/b36c6e4a5c884d589713fc6d79ffabe9/7c1980c0-388e-40b1-8f38-0fa7ad32141f'


class TeamsMessage:
    def __init__(self, task: str = 'Utterance', role: str = 'Creator', lang: str = 'EN-US', phase: str = '_Training'):
        self.book = FileBook(lang=lang, phase=phase)

        self.summary = getattr(self.book, f"{task}{role}").summary()

        self.message = pymsteams.connectorcard(WEBHOOK)
        self.message.summary(f"{task} {role} Progress")
        table = f"""\n
        \t{task} {role} Progress
        \t\t\tFinance\t\tMedia_Cable
        Completed\t\t{self.summary['Finance']['Completed']}\t\t\t{self.summary['Media_Cable']['Completed']}
        Not Started\t\t{self.summary['Finance']['Not Started']}\t\t\t{self.summary['Media_Cable']['Not Started']}
        In Progress\t\t{self.summary['Finance']['In Progress']}\t\t\t{self.summary['Media_Cable']['In Progress']}
        """
        self.message.text(table)

    def print(self):
        self.message.printme()

    def send(self):
        self.message.send()