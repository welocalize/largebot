from welo365 import O365Account

DEBUG = False

AIE_SWITCH = 'Dev' if DEBUG else 'Production Planning'
PROJ_SWITCH = 'Dev' if DEBUG else 'Data Creation'

AIE_SITE = 'AIEnablementPractice'
PROJ_SITE = 'msteams_08dd34-AmazonLex-LargeBot'

PROJ_PATH = [
    'Amazon Lex - LargeBot',
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
    # ('Intent', 'Creator'),
    # ('Intent', 'QC'),
    ('Utterance', 'QC'),
    ('Utterance', 'Creator')
)

ACCOUNT = O365Account()

AIE_DRIVE = ACCOUNT.get_site(AIE_SITE).get_default_document_library()

PROJ_DRIVE = ACCOUNT.get_site(PROJ_SITE).get_default_document_library()