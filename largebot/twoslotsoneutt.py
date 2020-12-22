from largebot import AIE_DRIVE
from welo365.welo365 import WorkBook
import pandas as pd
import re

DROP_PATH = [
    'Amazon Web Services, Inc',
    'Lex LargeBot (Akshat)',
    'Deliveries',
    '10% Drop'
]

deliverINT_file = AIE_DRIVE.get_item_by_path(*DROP_PATH, '12142020_EN-US_Training-Data_Drop1_IntS.xlsx')

deliverUTT_file = AIE_DRIVE.get_item_by_path(*DROP_PATH, '12142020_EN-US_Training-Data_Drop1_Utts.xlsx')

def get_worksheet(infile, sheet_name):
    wb = WorkBook(infile)
    return wb.get_worksheet(sheet_name)

def get_df(worksheet):
    columns, *values = worksheet.get_used_range().values
    return pd.DataFrame(values, columns=columns)

deliverINT = get_worksheet(deliverINT_file, 'Intent_Slot Creation')
dfINT = get_df(deliverINT)
deliverUTT = get_worksheet(deliverUTT_file, 'Utterances')
dfUTT = get_df(deliverUTT)

pattern = r'(\{(?P<slot>\w+)\})'

