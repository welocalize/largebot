from largebot import PROJ_CONFIG
from welo365 import WorkBook
import pandas as pd
import re
from rapidfuzz import fuzz

builtins = {
    'NUMBER': 'AMAZON.Number',
    'FIRSTNAME': 'AMAZON.FirstName',
    'LASTNAME': 'AMAZON.LastName',
    'PHONENUMBER': 'AMAZON.PhoneNumber',
    'ALPHANUMERIC': 'AMAZON.AlphaNumeric',
    'EMAILADDRESS': 'AMAZON.EmailAddress',
    'POSTALADDRESS': 'AMAZON.PostalAddress',
    'DATEINTERVAL': 'AMAZON.DateInterval',
    'TIME': 'AMAZON.Time',
    'DATE': 'AMAZON.Date',
    'CURRENCY': 'AMAZON.Currency',
    'DURATION': 'AMAZON.Duration',
    'STATE': 'AMAZON.State',
    'COUNTRY': 'AMAZON.Country',
    'CITY': 'AMAZON.City',
    'AIRPORT': 'AMAZON.Airport',
    'DAYOFWEEK': 'AMAZON.DayOfWeek',
    'PERCENTAGE': 'AMAZON.Percentage',
    'SPEED': 'AMAZON.Speed',
    'STREETNAME': 'AMAZON.StreetName',
    'WEIGHT': 'AMAZON.Weight'
}

LANG = 'EN-US'
PROJ_DRIVE, PROJ_PATH = PROJ_CONFIG.get(LANG)

wkdir = PROJ_DRIVE.get_item_by_path(*PROJ_PATH, 'EN-US', '_Training', 'Delivery Prep', 'Final 40% Drop', 'Ryan')

intsxl = wkdir.get_item('Intents.xlsx')
wb = WorkBook(intsxl)
intsws = wb.get_worksheet('Ints')
_range = intsws.get_used_range()
columns, *values = _range.values
intsdf = pd.DataFrame(values, columns=columns)
print(intsdf.columns)
intents_slot_type_names = []
intents_slot_names = {}
templates = []
# crosscheck = {'Intents': {}, 'Utterances': {}}

for row in intsdf.itertuples(name='row'):
    slot_type_name = builtins.get(row.SlotTypeName, None) or row.SlotTypeName
    if slot_type_name not in intents_slot_type_names:
        intents_slot_type_names.append(slot_type_name)
    if row.SlotName not in intents_slot_names:
        intents_slot_names[row.SlotName] = []
    if slot_type_name not in intents_slot_names[row.SlotName]:
        intents_slot_names[row.SlotName].append(slot_type_name)
    templates.append(
        [
            row.IntentID, row.IntentName, row.IntentDescription,
            'FALSE', 'FALSE',
            row.SlotName, slot_type_name, bool(row.SlotNameRequired == 'Required'),
            row.InputContextOne, row.InputContextTwo, row.InputContextThree, row.OutputContext,
            row.SlotPrompt
        ]
    )
    # crosscheck['Intents'].setdefault(row.IntentID, []).append(row.SlotName)


slot_names_with_multiple_types = {
    slot_name: _types
    for slot_name, _types in intents_slot_names.items()
    if len(_types) > 1
}

results = [[slot, [], [], 0] for slot in intents_slot_names]
for i, slot in enumerate(list(intents_slot_names.keys())):
    for j, choice in enumerate(list(intents_slot_names.keys())[i + 1:]):
        if fuzz.ratio(slot, choice, score_cutoff=90):
            results[i][3] += 1
            results[j + i + 1][3] += 1
            results[i][1].append(choice)
            results[i][2].append(slot)
            results[i][2].append(choice)
            results[i][2].sort()
            results[j + i + 1][1].append(slot)
            results[j + i + 1][2].append(slot)
            results[j + i + 1][2].append(choice)
            results[j + i + 1][2].sort()

possibly_redundant_slot_names = []
for slot_name, unique_matches, matches, match_count in results:
    if (_matches := tuple(matches)) and _matches not in possibly_redundant_slot_names:
        if len(_matches) == 2:
            match1, match2 = _matches
            repeats = [f"{match1}s", f"{match1}es"]
            for a, b in [('One', 'Two'), ('Date', 'Name'), ('From', 'To')]:
                repeats.append(match1.replace(a, b))
                repeats.append(match1.replace(b, a))
            if match2 in repeats:
                continue
        possibly_redundant_slot_names.append(_matches)

slotws = wb.get_worksheet('SlotTypeNames')
_range = slotws.get_used_range()
columns, *values = _range.values
slotdf = pd.DataFrame(values, columns=columns)

slot_type_names = {}
slot_values = {}
for row in slotdf.itertuples(name='row'):
    for value in (row.SampleValueOne, row.SampleValueTwo, row.SampleValueThree):
        slot_type_names.setdefault(row.SlotTypeName, []).append(value)
        slot_values.setdefault(value, []).append(row.SlotTypeName)

uttsxl = wkdir.get_item('Utterances.xlsx')
wb = WorkBook(uttsxl)
uttsws = wb.get_worksheet('Sample Utterances')
_range = uttsws.get_used_range()
columns, *values = _range.values
uttsdf = pd.DataFrame(values, columns=columns)
print(uttsdf.columns)


'''
slot_errors = []
int = 0
utt_ints = []
for i, row in enumerate(uttsdf.itertuples(name='row')):
    slot_error = []
    intent_slot_names = [
        slot.strip()
        for slot in crosscheck['Intents'][row.IntentID]
    ]
    if row.IntentID not in utt_ints:
        print(row.IntentID)
        utt_ints.append(row.IntentID)
        crosscheck['Utterances'][row.IntentID] = []
        
        if len(utt_ints) > 1:
            last_intent_id = utt_ints[-2]
            print(f"{last_intent_id=}")
            utt_slot_names = [
                slot.strip()
                for slot in crosscheck['Utterances'][last_intent_id]
            ]
            int_slot_names = [
                slot.strip()
                for slot in crosscheck['Intents'][last_intent_id]
            ]
            print(f"{utt_slot_names=}")
            print(f"{intent_slot_names=}")
            for int_slot in int_slot_names:
                if int_slot not in utt_slot_names:
                    print(int_slot)
                    slot_errors[-1].append(f"{int_slot}MissingError")
                    print(slot_errors[-1])
        
    if row.SlotNameOne and row.SlotNameOne != 'Null':
        crosscheck['Utterances'][row.IntentID].append(row.SlotNameOne)
        if row.SlotNameOne not in intents_slot_names:
            slot_error.append(f"{row.SlotNameOne}MissingError")
    if row.SlotNameTwo and row.SlotNameTwo != 'Null':
        crosscheck['Utterances'][row.IntentID].append(row.SlotNameTwo)
        if row.SlotNameTwo not in intents_slot_names:
            slot_error.append(f"{row.SlotNameTwo}MissingError")
    print(slot_error)
    slot_errors.append(slot_error)


df_slot_errors = [[', '.join(set(slot_error))] for slot_error in slot_errors]
_range = uttsws.get_range('G2:G24301')
_range.update(values=df_slot_errors)

'''
utterances = uttsdf.Utterance.tolist()
intent_names = uttsdf.IntentName.tolist()
singleslot = {}
multislot = {}
noslots = {}
for intent_name, utterance in zip(intent_names, utterances):
    slots = re.findall(r'\{(\w+)\}', utterance)
    if len(slots) == 1:
        singleslot.setdefault(intent_name, {}).setdefault(slots[0], []).append(utterance)
        continue
    if len(slots) == 0:
        noslots.setdefault(intent_name, []).append(utterance)
        continue
    for slot in slots:
        multislot.setdefault(intent_name, {}).setdefault(slot, []).append(utterance)


for template in templates:
    _utterances = ['']
    if slot_utterances := singleslot.get(template[1], {}).get(template[5], []):
        _utterances = slot_utterances
    template.append(_utterances)



intent_templates = []
_intent_names = []

def get_col(i: int):
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    col = letters[(i % 26) - 1]
    if i > 26 and (index := i // 26):
        col = f"{letters[index - 1]}{col}"
    return col


templates_template = wkdir.get_item('IntentTemplates.xlsx')
test = wkdir.get_item('TestTemplates.xlsx')
if not test:
    templates_template.copy(wkdir, name='TestTemplates.xlsx')
    test = wkdir.get_item('TestTemplates.xlsx')
wb = WorkBook(test)
uttws = wb.get_worksheet('Utterances')

u = 2
named_ranges = []
named_values = []
max_len = None

for i, template in enumerate(templates):
    named_range = f"{template[1]}_{template[5]}"
    print(i, named_range)
    if template[1] not in _intent_names:
        _intent_names.append(template[1])
        if i > 0:
            last_row = [
                *templates[i-1][0:5], 'FALSE', 'FALSE', 'FALSE', '', '', '', '', '', 'FALSE', 'FALSE', 'FALSE', 'FALSE', 'FALSE', 'FALSE', 'FALSE', 'FALSE'
            ]
            intent_templates.append(last_row)
            named_values.append([''])
            u += 1
        first_row = [
            *template[0:5], 'FALSE', 'FALSE', 'FALSE', '', '', '', '', '', '', '', '', '', '', '', '', ''
        ]
        intent_utterances = noslots.get(template[1], [''])
        max_len = len(intent_utterances) if (max_len is None or max_len < len(intent_utterances)) else max_len
        intent_templates.append(first_row)
        named_values.append(intent_utterances)
        u += 1
    intent_templates.append([*template[0:-1], f"{{{template[5]}}}", '', '', '', '', '', '', ''])
    _utterances = template[-1]
    u += 1
    max_len = len(_utterances) if (max_len is None or max_len < len(_utterances)) else max_len
    named_values.append(_utterances)

last_row = [
    *templates[-1][0:5], 'FALSE', 'FALSE', 'FALSE', '', '', '', '', '', 'FALSE', 'FALSE', 'FALSE', 'FALSE', 'FALSE', 'FALSE', 'FALSE', 'FALSE'
]
intent_templates.append(last_row)
named_values.append([''])

for row in named_values:
    for i in range(max_len - len(row)):
        row.append('')


update_address = f"A2:{get_col(max_len)}{len(named_values) + 1}"
_range = uttws.get_range(update_address)
_range.update(values=named_values)


scripts_ws = wb.get_worksheet('Scripts')
scripts_address = f"A2:U{len(intent_templates) + 1}"
_range = scripts_ws.get_range(scripts_address)
_range.update(values=intent_templates)

