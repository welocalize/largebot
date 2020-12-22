from welo365 import O365Account

DEBUG = False

WEBHOOK = 'https://outlook.office.com/webhook/b6df740f-912c-4f8e-aae2-f729af5204e1@d41d420e-6265-4ec2-aeb7-5869659e3fe2/IncomingWebhook/5a3c1efd0aca4a9b8e001bede0e5934e/7c1980c0-388e-40b1-8f38-0fa7ad32141f'
DEV_WEBHOOK = 'https://outlook.office.com/webhook/1db85346-a351-4611-8184-de0fba3b2de6@d41d420e-6265-4ec2-aeb7-5869659e3fe2/IncomingWebhook/b36c6e4a5c884d589713fc6d79ffabe9/7c1980c0-388e-40b1-8f38-0fa7ad32141f'
WEBHOOKS = {
    'Creator': 'https://outlook.office.com/webhook/b6df740f-912c-4f8e-aae2-f729af5204e1@d41d420e-6265-4ec2-aeb7-5869659e3fe2/IncomingWebhook/ee87271452cc4e638fe889c073a526fd/7c1980c0-388e-40b1-8f38-0fa7ad32141f',
    'QC': 'https://outlook.office.com/webhook/b6df740f-912c-4f8e-aae2-f729af5204e1@d41d420e-6265-4ec2-aeb7-5869659e3fe2/IncomingWebhook/0cad1f2097194f34805ef6720e52b6f9/7c1980c0-388e-40b1-8f38-0fa7ad32141f'
}


AIE_SWITCH = 'Dev' if DEBUG else 'Production Planning'
PROJ_SWITCH = 'Dev' if DEBUG else 'Data Creation'

AIE_SITE = 'AIEnablementPractice'
EN_PROJ_SITE = 'msteams_08dd34-AmazonLex-LargeBot'
ES_PROJ_SITE = 'msteams_08dd34-AmazonLex-esUSLargeBot'

EN_PROJ_PATH = [
    'Amazon Lex - LargeBot',
    PROJ_SWITCH
]

ES_PROJ_PATH = [
    'Amazon Lex - esUS LargeBot',
    PROJ_SWITCH
]

AIE_PATH = [
    'Amazon Web Services, Inc',
    'Lex Largebot (Akshat)',
    AIE_SWITCH,
    'Files for Processing'
]

FILE_PATH = [
    *AIE_PATH,
    'Processed Files 2.0'
]

STEPS = (
    ('Intent', 'Creator'),
    ('Intent', 'QC'),
    ('Utterance', 'QC'),
    ('Utterance', 'Creator')
)

ACCOUNT = O365Account()

AIE_DRIVE = ACCOUNT.get_site(AIE_SITE).get_default_document_library()

EN_PROJ_DRIVE = ACCOUNT.get_site(EN_PROJ_SITE).get_default_document_library()
ES_PROJ_DRIVE = ACCOUNT.get_site(ES_PROJ_SITE).get_default_document_library()

PROJ_CONFIG = {
    'EN-US': (EN_PROJ_DRIVE, EN_PROJ_PATH),
    'ES-US': (ES_PROJ_DRIVE, ES_PROJ_PATH)
}
