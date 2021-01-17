from largebot.config import ACCOUNT
from largebot import AIE_DRIVE, FILE_PATH, PROJ_CONFIG
from welo365 import WorkBook
import pandas as pd

PROJ_DRIVE, PROJ_PATH = PROJ_CONFIG.get('EN-US')

#en_utts = ACCOUNT.get_item_by_url(
#    # 'https://welocalize.sharepoint.com/:x:/r/sites/msteams_08dd34-AmazonLex-LargeBot/_layouts/15/Doc.aspx?sourcedoc=%7BF5A2D6CA-D4F1-40F1-90C1-85E0FBE4FF3A%7D&file=FINAL_EN_Tr_Utts_MC_Drop11.xlsx&action=default&mobileredirect=true'
#    'https://welocalize.sharepoint.com/:x:/r/sites/msteams_08dd34-AmazonLex-LargeBot/_layouts/15/Doc.aspx?sourcedoc=%7B66D65B6F-8DC4-4222-9BBB-08A3EFE77169%7D&file=12302020_EN-US_Training-Data_Drop2_Utts.xlsx&action=default&mobileredirect=true'
#    )
en_utts = PROJ_DRIVE.get_item_by_path(
    *PROJ_PATH,
    'EN-US',
    '_Training',
    'Delivery Prep',
    '50% Drop',
    'Drop2 for ES_us slots populated.xlsx'
)

es_temp = AIE_DRIVE.get_item_by_path(
    *FILE_PATH[:-1],
    'Data Sheet Templates',
    'es-US',
    'TEMPLATE - es-US_Training Data__Utterance Creation Sheet.xlsx'
)

en_wb = WorkBook(en_utts)
wss = list(en_wb.get_worksheets())
print(f"{wss=}")
for en_ws, dom, last_row in zip(wss, ['MC', 'Fi'], [24001, 6001]):
    if dom == 'MC':
        continue
    print(f"{en_ws.name=}")
    print(f"{dom=}, {last_row=}")
    _range = en_ws.get_range(f"A1:J{last_row}")
    columns, *values = _range.values
    en_df = pd.DataFrame(values, columns=columns)
    en_df['IntentNameTranslation'] = None
    en_df.drop(columns=['Sample Utterance'], inplace=True)
    en_df.drop(columns=['ErrorFlags', 'Fuzzy Flags'], inplace=True)
    en_df['ID'] = en_df['ID'].apply(lambda x: f"{dom} {x}")
    en_df['SampleUtteranceTranslation'] = None
    en_df = en_df.reindex(
        columns=[
            'ID', 'IntentName', 'IntentNameTranslation', 'IntentDescription',
            'Modality', 'SlotName', 'SlotName (Optional)', 'NewUtterance', 'SampleUtteranceTranslation'
        ]
    ).where(pd.notnull(en_df), '')
    es_values = [
        row
        for row in en_df.values.tolist()
        if row
    ]
    batches = [es_values[i:i + 300] for i in range(0, len(es_values), 300)]
    es_utt_fol = AIE_DRIVE.get_item_by_path(*FILE_PATH[:-1], 'Data Sheet Templates', 'es-US', 'Utterance')
    for batch in batches:
        print(f"{batch=}")
        print(f"{batch[0]=}")
        print(f"{len(batch[0])=}")
        batch_num = None
        if (intent_id := batch[0][0]):
            batch_num = int(intent_id.split()[1]) // 5 + 1
        if not batch_num:
            continue
        batch_name = f"ES_Tr_Utts_{dom}_{batch_num:03d}.xlsx"
        print(batch_name)
        xl = es_utt_fol.get_item(batch_name)
        if not xl:
            es_temp.copy(es_utt_fol, name=batch_name)
            xl = es_utt_fol.get_item(batch_name)
        wb = WorkBook(xl)
        ws = wb.get_worksheet('Sample Utterances')
        _range = ws.get_range('A5:I304')
        _range.update(values=batch)
