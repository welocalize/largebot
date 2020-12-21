from largebot.config import AIE_DRIVE

path = 'ServiceNow/Project%203&4_Dorit/kb_html'.split('/')
folder = AIE_DRIVE.get_item_by_path(*path)
items = [item.name for item in folder.get_items()]
path = 'ServiceNow/Project%203&4_Dorit/TEMPLATE - SVN Queries.xlsx'.split('/')
template = AIE_DRIVE.get_item_by_path(*path)
items = [item.split('.')[0] for item in items]
from itertools import repeat

batch_prep = [(f"{i:03d}", item) for i, item in enumerate(items, start=1)]
batches = [batch_prep[i:i+10] for i in range(0, len(batch_prep), 10)]
path = 'ServiceNow/Project%203&4_Dorit/Prep'.split('/')
prep_folder = AIE_DRIVE.get_item_by_path(*path)
from welo365 import WorkBook

for i, batch in enumerate(batches, start=1):
    file_name = f"SVN-Queries_{i:02d}.xlsx"
    print(f"{file_name}")
    print(f"{batch=}")
    template.copy(prep_folder, name=file_name)
    out_file = prep_folder.get_item(file_name)
    out_wb = WorkBook(out_file)
    out_ws = out_wb.get_worksheet('Articles')
    out_range = out_ws.get_range('A7:B96')
    values = []
    for sub_batch in batch:
        values.extend(list(repeat(list(sub_batch), 9)))
    out_range.update(values=values)
