from largebot import AIE_DRIVE, FILE_PATH
from welo365 import WorkBook
from largebot.botter.amazon import Utterer
from termcolor import colored, cprint



def print_row(row):
    colors = ('red', 'blue', 'yellow', 'green', 'magenta', 'cyan')
    for i, cell in enumerate(row):
        cprint(cell, colors[(i + len(colors)) % len(colors)], 'on_white', end='\t')
    print('')



scripts = AIE_DRIVE.get_item_by_path(*FILE_PATH[0:2], 'Testing', 'Test.xlsx')
ints_del = AIE_DRIVE.get_item_by_path(*FILE_PATH[0:2], 'Testing', 'ints_delivery.xlsx')
test_int = AIE_DRIVE.get_item_by_path(*FILE_PATH[0:2], 'Testing', 'ES_Tr_Ints_MC_090.xlsx')
wb = WorkBook(scripts)
ws = wb.get_worksheet('Scripts')
_range = ws.get_used_range()
_, *values = _range.values
values = [row[:12] for row in values]

amazon = Utterer()

def clean_script(values: list):
    script_dict = {}
    scripts = []
    for row in values:
        turn_id = row[10]
        intent_name = row[1]
        if not isinstance(turn_id, int):
            continue
        responses = ['', '', '', '', '', '', '', '']
        if (slot_type := row[8]) and isinstance(slot_type, str) and 'AMAZON' in slot_type:
            slot_type = slot_type.replace('_', '.')
            row[8] = slot_type
            # generator = getattr(amazon, slot_type.split('.')[1], None)
            # if generator:
            #     for i in range(len(responses)):
            #         responses[i] = generator()
        row.extend(responses)
        domain = 'Media_Cable' if 'MC' in row[0] else 'Finance'
        script_dict.setdefault(domain, {}).setdefault(intent_name, []).append(row)

    for domain in ('Media_Cable', 'Finance'):
        for intent_name, script in script_dict[domain].items():
            script.sort(key=lambda x: x[10])
            for i in range(len(script)):
                script[i][10] = i
            scripts.extend(script)

    script_dict['script'] = scripts

    turns = {}
    for domain in ('Media_Cable', 'Finance'):
        for intent_name, script in script_dict[domain].items():
            if intent_name != 'script':
                for i, turn in enumerate(script):
                    turns.setdefault(intent_name, {}).update({turn[6]: i})

    script_dict['turns'] = turns

    int_ids = {}

    for row in script_dict['script']:
        int_ids[row[0]] = row[1]

    script_dict['intent_ids'] = int_ids

    return script_dict


def publish_test():
    script_dict = clean_script(values)
    test = AIE_DRIVE.get_item_by_path(*FILE_PATH[0:2], 'Testing', 'Test.xlsx')
    wb = WorkBook(test)
    ws = wb.get_worksheet('Scripts')
    _range = ws.get_range(f"A2:T{len(script_dict['script']) + 1}")
    _range.update(values=script_dict['script'])


def es_intent_prep(sd: dict, ti, newf, domain):
    test_int = ti
    script_dict = sd
    test_wb = WorkBook(test_int)
    test_ws = test_wb.get_worksheet('Intent_Slot Creation')
    test_range = test_ws.get_used_range()
    test_values = test_range.values
    new_wb = WorkBook(newf)
    new_ws = new_wb.get_worksheet('Intent_Slot Creation')
    address = f"A7:R{test_range.bottom}"
    new_range = new_ws.get_range(address)

    new_values = []
    filtered_values = [
        row
        for row in test_values[6:]
        if row[6] not in (False, 'FALSE', 'False')
    ]

    def get_en_intent_name(es_intent_id):
        dom = 'MC' if domain == 'Media_Cable' else 'Fi'
        intent_id = f"{dom} {es_intent_id}"
        return script_dict['intent_ids'].get(intent_id, '')

    en_int_name = None
    item_dict = {}

    for i, row in enumerate(filtered_values):
        error_flag = ''
        int_name = row[1]
        en_int_name = get_en_intent_name(row[0])
        if not en_int_name:
            print("No data for this sheet. Skipping.")
            return
        kept_slots = list(script_dict['turns'].get(en_int_name, {}).keys())
        if int_name != en_int_name:
            print(f"Error with {domain} {row[0]}: ES {row[1]} vs. EN {en_int_name}")
            row[1] = en_int_name
            error_flag = 'ChangedIntentName'
        if not row[6] or row[6] not in kept_slots:
            continue
        row.append(error_flag)
        item_dict.setdefault(en_int_name, []).append(row)

    max_len = max(len(row) for script in item_dict.values() for row in script)

    for int_name, script_values in item_dict.items():
        en_int_name = get_en_intent_name(script_values[0][0])
        script_values.sort(key=lambda x: script_dict['turns'][en_int_name][x[6]])
        blank_row = [cell for cell in script_values[0][:4]]
        for i in range(len(script_values[0]) - len(blank_row) - 1):
            blank_row.append('')
        blank_row.append(script_values[0][-1])
        for i in range(10 - len(script_values)):
            new_row = [cell for cell in blank_row]
            script_values.append(new_row)
        for i, row in enumerate(script_values, start=1):
            row[5] = f"{row[0]}-{i}"
        new_values.extend(script_values)
    new_range.update(values=new_values)


script_dict = clean_script(values=values)

def prepes(domain):
    es_fol = AIE_DRIVE.get_item_by_path(*FILE_PATH, 'ES-US', '_Training')
    domain_fol = es_fol.get_item(domain).get_item('Intent')
    feedback = domain_fol.get_item('Feedback')
    wkdir = domain_fol.get_item('Working')
    if not wkdir:
        domain_fol.create_child_folder('Working')
        wkdir = domain_fol.get_item('Working')
    template = domain_fol.get_item('Template.xlsx')
    for item in wkdir.get_items():
        print(f"Deleting {item.name}")
        item.delete()
    for item in feedback.get_items():
        print(f"Copying {item.name}")
        template.copy(wkdir, name=item.name)
        copied_item = wkdir.get_item(item.name)
        wb = WorkBook(item)
        ws = wb.get_worksheet('Intent Clarification')
        _range = ws.get_used_range()
        new_wb = WorkBook(copied_item)
        new_ws = new_wb.get_worksheet('Intent Clarification')
        new_range = new_ws.get_range(_range.address)
        new_range.update(values=_range.values)
        es_intent_prep(script_dict, item, copied_item, domain)


def for_vince():
    for domain in ('Media_Cable', 'Finance'):
        prepes(domain)
