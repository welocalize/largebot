from largebot import AIE_DRIVE, FILE_PATH
from welo365 import WorkBook
import re

testing_fol = AIE_DRIVE.get_item_by_path(*FILE_PATH, 'EN-US', 'Testing')
bot_template = testing_fol.get_item('bot_template.xlsx')
bot_template_fol = testing_fol.get_item('bot template files')

convos = []
scripts = []
first = 1

for item in bot_template_fol.get_items():
    print(item.name)
    matches = re.findall(r'(\d+)', item.name)
    last = int(matches[1])
    wb = WorkBook(item)
    convos_ws = wb.get_worksheet('Conversations')
    convos_range = convos_ws.get_used_range()
    convos_values = [
        row[:5]
        for row in convos_range.values[3:]
        if row[0] != ''
    ]
    convos.extend(convos_values)
    scripts_ws = wb.get_worksheet('Scripts')
    scripts_range = scripts_ws.get_used_range()
    scripts_values = [
        [row[0], agent, *row[2:8]]
        for row in scripts_range.values[3:]
        if (
                row[0] != ''
                and (agent := row[1].replace('"', ''))
        )
    ]
    scripts.extend(scripts_values)


print(f"{len(convos)=}, {len(scripts)=}")
combo_name = f"bot_template_MC{first:03d}-MC{last:03d}.xlsx"
bot_template.copy(testing_fol, name=combo_name)
combo_file = testing_fol.get_item(combo_name)
wb = WorkBook(combo_file)
convos_ws = wb.get_worksheet('Conversations')
convos_range = convos_ws.get_range(f"A4:E{len(convos) + 3}")
convos_range.update(values=convos)
scripts_ws = wb.get_worksheet('Scripts')
scripts_range = scripts_ws.get_range(f"A4:H{len(scripts) + 3}")
scripts_range.update(values=scripts)


