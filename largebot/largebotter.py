from __future__ import annotations

import datetime
import random
import pymsteams
from itertools import repeat
from typing import Optional, Union

import arrow
import pandas as pd
from pydantic import BaseModel as _BaseModel
from pydantic import Extra
from requests.exceptions import HTTPError
from welo365 import WorkBook, Drive, WorkSheet, Folder
from O365.drive import File

from largebot.config import AIE_DRIVE, PROJ_DRIVE, STEPS, FILE_PATH, PROJ_PATH, WEBHOOKS
from largebot.logger import get_logger
from largebot.pd import get_df
from largebot.qctool import qc_check

logger = get_logger(__name__)


def prep_utts(item, lang, phase, domain):
    logger.info(f"Prepping utterances from intents for {item}")
    UTT_PATH = [
        *FILE_PATH,
        lang,
        phase,
        domain,
        'Utterance'
    ]
    prep_folder = AIE_DRIVE.get_item_by_path(
        *UTT_PATH,
        'Prep'
    )
    template = prep_folder.get_item('TEMPLATE.xlsx')
    intent_folder = AIE_DRIVE.get_item_by_path(
        *UTT_PATH,
        'Intent'
    )
    out_folder = AIE_DRIVE.get_item_by_path(
        *UTT_PATH,
        'Creator'
    )

    int_file = intent_folder.get_item(item.name)
    in_file = prep_folder.get_item(item.name.split('_', 3)[3])
    out_file = out_folder.get_item(in_file.name)
    in_wb = WorkBook(in_file)
    in_ws = in_wb.get_worksheet('Sample Utterances')
    template.copy(out_folder, name=in_file.name)
    int_wb = WorkBook(int_file)
    int_ws = int_wb.get_worksheet('Intent_Slot Creation')
    out_wb = WorkBook(out_file)
    out_ws = [ws for ws in out_wb.get_worksheets()]
    out_intents = out_ws[0].get_range('Intents')
    in_intents = in_ws.get_range(out_intents.address.split('!')[1])
    int_range = in_ws.get_range('C7:C56')
    descriptions = int_range.values
    descriptions = list(set(desc[0] for desc in descriptions))
    descriptions = [
        [y]
        for x in descriptions
        for y in repeat(x, 60)
    ]
    utt_descriptions = [
        ['IntentDescription'],
        ['User wants to book a flight'],
        ['User wants to book a flight'],
        ['User wants to book a flight'],
        *descriptions
    ]
    out_intents.update(values=in_intents.values)
    addresses = (
        ('H7:H16', 'DataValidation!A2:A12'),
        ('H17:H26', 'DataValidation!B2:B12'),
        ('H27:H36', 'DataValidation!C2:C12'),
        ('H37:H46', 'DataValidation!D2:D12'),
        ('H47:H56', 'DataValidation!E2:E12')
    )
    for inloc, outloc in addresses:
        inrange = int_ws.get_range(inloc)
        slots = inrange.values
        slots.append(['Null'])
        outrange = out_ws[1].get_range(outloc)
        outrange.update(values=slots)
    modrange = out_ws[0].get_range('Modality')
    modality = modrange.values
    random.shuffle(modality)
    modrange.update(values=modality)
    utt_range = out_ws[0].get_range('C1:C304')
    utt_range.insert_range(shift='right')
    utt_range.update(values=utt_descriptions)
    logger.info(f"Utterance prep for {item} completed")


class BaseModel(_BaseModel):
    class Config:
        arbitrary_types_allowed = True
        allow_mutation = True
        extra = Extra.allow


class DataFrameXL(WorkBook):
    def __init__(
            self,
            *parts: str,
            drive: Drive,
            index_col: Optional[Union[int, str]] = None
    ):
        super().__init__(drive.get_item_by_path(*parts))
        self.worksheets = {
            worksheet.name: worksheet
            for worksheet in self.get_worksheets()
            if worksheet.name not in ['Data', 'MasterIntentList', 'ForResourcesToCopy']
        }
        self.dfs = {
            ws_name: get_df(ws, index_col=index_col)
            for ws_name, ws in self.worksheets.items()
        }

    def __getattr__(self, key):
        return self.__getattribute__(key.strip().replace(' ', '_'))

    def __setattr__(self, name, value):
        self.__dict__[name.strip().replace(' ', '_')] = value

    def __delitem__(self, key):
        self.__delattr__(key.strip().replace(' ', '_'))

    def __getitem__(self, key):
        return self.__getattribute__(key.strip().replace(' ', '_'))

    def __setitem__(self, key, value):
        self.__setattr__(key, value)


class FileName:
    def __init__(self, name: str):
        self.lang = ''
        self.phase = ''
        self.task = ''
        self.domain = ''
        self.number = ''
        name = name.split('.')[0] if '.xlsx' in name else name
        if name == 'Not Active':
            self.name = name
            return
        self.name = name.split()[0]
        parts = self.name.split('_')
        if len(parts) == 5:
            self.lang = f"{parts[0]}-US"
            self.phase = '_Training' if parts[1] == 'Tr' else 'Testing'
            self.task = 'Intent' if parts[2][0] == 'I' else 'Utterance'
            self.domain = 'Finance' if parts[3][0] == 'F' else 'Media_Cable'
            self.number = parts[4]

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


class FileAssignment(BaseModel):
    file_name: FileName
    status: str
    resource_name: str
    resource_code: str
    role: str

    def __init__(
            self,
            file_name: Union[str, FileName],
            status: str,
            resource_name: str,
            resource_code: str,
            role: str
    ):
        file_name = FileName(file_name) if isinstance(file_name, str) else file_name
        resource_name = resource_name or ''
        resource_code = resource_code or ''
        super().__init__(
            file_name=file_name,
            status=status,
            resource_name=resource_name,
            resource_code=resource_code,
            role=role
        )

    def __iter__(self):
        return iter(
            (
                self.file_name.name,
                self.status,
                self.resource_name,
                self.resource_code
            )
        )

    def __repr__(self):
        return f"{self.file_name.name} [{self.role}:{self.status}]"

    def __str__(self):
        return repr(self)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return tuple(self) == tuple(other)
        return False

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return tuple(self) != tuple(other)
        return False

    @property
    def needs_assignment(self):
        return bool(self.status == 'Not Started' and self.resource_name == 'Unassigned')

    def get_source(self):
        return AIE_DRIVE.get_item_by_path(
            *FILE_PATH,
            self.file_name.lang,
            self.file_name.phase,
            self.file_name.domain,
            self.file_name.task,
            self.role,
            f"{self.file_name.name}.xlsx"
        )

    def copy_source(self, target: Folder = None):
        if not target:
            RESOURCE_PATH = [
                *PROJ_PATH,
                self.file_name.lang,
                self.file_name.phase,
                self.role,
                self.resource_code,
                self.file_name.domain
            ]
            target = PROJ_DRIVE.get_item_by_path(
                *RESOURCE_PATH
            )
        if (item := self.get_source()):
            item.copy(target)

    def get_working(self, in_progress: bool = False):
        RESOURCE_PATH = [
            self.role,
            self.resource_code,
            self.file_name.domain
        ]
        if not in_progress and self.status in [
            'Completed', 'Re-work Completed', 'Accepted', 'Rejected'
        ]:
            RESOURCE_PATH.append(self.status)
        return PROJ_DRIVE.get_item_by_path(
            *PROJ_PATH,
            self.file_name.lang,
            self.file_name.phase,
            *RESOURCE_PATH,
            f"{self.file_name.name}.xlsx"
        )

    def copy_working(self, target: Folder = None):
        if not target:
            ROOT = [
                *FILE_PATH,
                self.file_name.lang,
                self.file_name.phase,
                self.file_name.domain
            ]
            paths = {
                'IntentCreator': [
                    *ROOT,
                    'Intent',
                    'QC'
                ],
                'IntentQC': [
                    *ROOT,
                    'Utterance',
                    'Intent'
                ],
                'UtteranceCreator': [
                    *ROOT,
                    'Utterance',
                    'QC'
                ],
                'UtteranceQC': [
                    *ROOT,
                    'DeliveryPrep'
                ]
            }
            target_path = paths.get(f"{self.file_name.task}{self.role}")
            target = AIE_DRIVE.get_item_by_path(*target_path)
        if target and (item := self.get_working()):
            if (previous_version := target.get_item(item.name)):
                if self.role == 'QC' and self.file_name.task == 'Intent':
                    try:
                        self.prep_utts()
                    except (ValueError, HTTPError) as e:
                        logger.error(f"Error trying to prepare utterances: {e}")
                    return
                for i in range(1, 100):
                    previous_name = f"{item.name.split('.')[0]}_v{i}.xlsx"
                    previous = target.get_item(previous_name)
                    if not previous:
                        break
                previous_version.copy(target, name=previous_name)
                previous_version.delete()
            item.copy(target)
            if self.role == 'Creator' and self.file_name.task == 'Utterance':
                qc_file = target.get_item(item.name)
                self.qc_check(qc_file)
            if self.role == 'QC' and self.file_name.task == 'Intent':
                try:
                    self.prep_utts()
                except (ValueError, HTTPError) as e:
                    logger.error(f"Error trying to prepare utterances: {e}")

    def move_working(self, target: str):
        if (item := self.get_working(in_progress=True)):
            target_folder = PROJ_DRIVE.get_item_by_path(
                *PROJ_PATH,
                self.file_name.lang,
                self.file_name.phase,
                self.role,
                self.resource_code,
                self.file_name.domain,
                target
            )
            if (previous_version := target_folder.get_item(self.file_name.name)):
                previous_version.copy(
                    target_folder,
                    name=f"{self.file_name.name}_{datetime.datetime.utcnow().strftime('%Y%m%d')}.xlsx"
                )
                previous_version.delete()
            item.move(target_folder)

    def qc_check(self, qc_file: File):
        qc_check(qc_file)

    def prep_utts(self):
        logger.info(f"Prepping utterances from intents for {self}")
        UTT_PATH = [
            *FILE_PATH,
            self.file_name.lang,
            self.file_name.phase,
            self.file_name.domain,
            'Utterance'
        ]
        prep_folder = AIE_DRIVE.get_item_by_path(
            *UTT_PATH,
            'Prep'
        )
        template = prep_folder.get_item('TEMPLATE.xlsx')
        intent_folder = AIE_DRIVE.get_item_by_path(
            *UTT_PATH,
            'Intent'
        )
        out_folder = AIE_DRIVE.get_item_by_path(
            *UTT_PATH,
            'Creator'
        )
        int_file = intent_folder.get_item(self.file_name.name)
        in_file = prep_folder.get_item(self.file_name.name.replace('Ints', 'Utts'))
        out_file = out_folder.get_item(in_file.name)
        if out_file:
            logger.info(f"{out_file.name} done already")
            return
        in_wb = WorkBook(in_file)
        in_ws = in_wb.get_worksheet('Sample Utterances')
        template.copy(out_folder, name=in_file.name)
        int_wb = WorkBook(int_file)
        int_ws = int_wb.get_worksheet('Intent_Slot Creation')
        out_file = out_folder.get_item(in_file.name)
        out_wb = WorkBook(out_file)
        out_ws = [ws for ws in out_wb.get_worksheets()]
        int_range = int_ws.get_range('C7:C56')
        descriptions = int_range.values
        descriptions = list(
            dict.fromkeys(
                [
                    desc[0] for desc in descriptions if desc[0]
                ]
            ).keys()
        )
        if len(descriptions) != 5:
            int_file.delete()
            out_file.delete()
            logger.info(f"{descriptions=}")
            raise ValueError(f"Too many intent descriptions for file {self.file_name.name}")
        descriptions = [
            [y]
            for x in descriptions
            for y in repeat(x, 60)
        ]
        utt_descriptions = [
            ['IntentDescription'],
            ['User wants to book a flight'],
            ['User wants to book a flight'],
            ['User wants to book a flight'],
            *descriptions
        ]
        out_intents = out_ws[0].get_range('Intents')
        in_intents = in_ws.get_range(out_intents.address.split('!')[1])
        out_intents.update(values=in_intents.values)
        addresses = (
            ('H7:H16', 'DataValidation!A2:A12'),
            ('H17:H26', 'DataValidation!B2:B12'),
            ('H27:H36', 'DataValidation!C2:C12'),
            ('H37:H46', 'DataValidation!D2:D12'),
            ('H47:H56', 'DataValidation!E2:E12')
        )
        for inloc, outloc in addresses:
            inrange = int_ws.get_range(inloc)
            slots = inrange.values
            slots.append(['Null'])
            outrange = out_ws[1].get_range(outloc)
            outrange.update(values=slots)
        modrange = out_ws[0].get_range('Modality')
        modality = modrange.values
        random.shuffle(modality)
        modrange.update(values=modality)
        utt_range = out_ws[0].get_range('C1:C304')
        utt_range.insert_range(shift='right')
        utt_range.update(values=utt_descriptions)
        logger.info(f"Utterance prep for {self} completed")


class FileSheet(DataFrameXL):
    def __init__(
            self,
            task: str,
            role: str,
            ws: WorkSheet,
            df: pd.DataFrame
    ):
        self.name = f"{task}{role}"
        self.task = task
        self.role = role
        self.ws = ws
        self.df = df
        self.file_names = [
            name.lower()
            for name in self.df['FileName'].tolist()
        ]
        for file_name, file_assignment in zip(
                self.file_names,
                self.df.values.tolist()
        ):
            self.__setattr__(
                file_name,
                FileAssignment(*file_assignment, role)
            )

    def __getitem__(self, key):
        return self.files[key]

    def __delitem__(self, key):
        del self.files[key]

    def __setitem__(self, key, value):
        self.files[key] = value

    @property
    def files(self):
        return [
            getattr(self, file_name)
            for file_name in self.file_names
        ]

    @property
    def values(self):
        return [
            [*file_assignment]
            for file_assignment in self.files
        ]

    def summary(self):
        df = self.df
        df['Domain'] = df['FileName'].apply(lambda x: 'Finance' if x.split('_')[3] == 'Fi' else 'Media_Cable')
        return pd.crosstab(df.Status, df.Domain)

    @property
    def unassigned(self):
        yield from (
            file_assignment
            for file_assignment in self.files
            if file_assignment.needs_assignment
        )

    @property
    def columns(self):
        return self.df.columns.tolist()

    def publish(self):
        _range = self.ws.get_range(f"A1:D{len(self.values) + 1}")
        _range.update(
            values=[
                self.columns,
                *self.values
            ]
        )


class ResourceAssignment(BaseModel):
    resource_code: str
    resource_name: str
    file_name: FileName
    status: str
    role: str
    lang: str
    phase: str
    summary: dict = {}
    drive: Drive = None
    finance: Folder = None
    media_cable: Folder = None

    def __init__(
            self,
            resource_code: str,
            resource_name: str,
            file_name: Union[FileName, str],
            status: str,
            role: str,
            lang: str,
            phase: str
    ):
        file_name = FileName(file_name) if isinstance(file_name, str) else file_name
        status = status or ''
        super().__init__(
            resource_code=resource_code,
            resource_name=resource_name,
            file_name=file_name,
            status=status,
            role=role,
            lang=lang,
            phase=phase
        )

    def __iter__(self):
        return iter(
            (
                self.resource_code,
                self.resource_name,
                self.file_name.name,
                self.status
            )
        )

    def __repr__(self):
        return f"{self.resource_name} [{self.resource_code}]"

    def __str__(self):
        return repr(self)

    def get_drive(self):
        if self.drive is None:
            drive = PROJ_DRIVE.get_item_by_path(
                *PROJ_PATH,
                self.lang,
                self.phase,
                self.role,
                self.resource_code
            )
            self.drive = drive
        return self.drive

    def get_domain_folder(self, domain: str):
        return self.get_drive().get_item(domain)

    def get_file_status(self):
        for domain in ['Media_Cable', 'Finance']:
            for item in self.get_domain_folder(domain).get_items():
                if item.is_file:
                    file_name = FileName(item.name)
                    if (task := file_name.task):
                        self.summary.setdefault(task, []).append(
                            self.get_file_assignment(
                                file_name, 'In Progress'
                            )
                        )
                if item.is_folder:
                    for done in item.get_items():
                        file_name = FileName(done.name)
                        if (task := file_name.task):
                            self.summary.setdefault(task, []).append(
                                self.get_file_assignment(
                                    file_name, item.name
                                )
                            )

    def get_file_assignment(self, file_name: Union[str, FileName] = None, status: str = None):
        file_name = file_name or self.file_name
        status = status or self.status
        return (
            FileAssignment(
                file_name, status, self.resource_name, self.resource_code, self.role
            )
        )

    @property
    def needs_assignment(self):
        return bool(
            self.status in (
                'Completed',
                'Accepted',
                'Rejected',
                'Re-work Completed',
                'Needs Assignment'
            )
        )

    def assign(self, assignment: FileAssignment):
        self.file_name = assignment.file_name
        self.status = 'Not Started'
        assignment.status = self.status
        assignment.resource_name = self.resource_name
        assignment.resource_code = self.resource_code
        assignment.role = self.role
        assignment.copy_source()

    def get_working(self, target: str = None, in_progress: bool = False):
        RESOURCE_PATH = [
            self.role,
            self.resource_code,
            self.file_name.domain
        ]
        if not in_progress and self.status in [
            'Completed', 'Re-work Completed', 'Accepted', 'Rejected'
        ]:
            RESOURCE_PATH.append(self.status)
        if target:
            RESOURCE_PATH.append(target)
        return PROJ_DRIVE.get_item_by_path(
            *PROJ_PATH,
            self.file_name.lang,
            self.file_name.phase,
            *RESOURCE_PATH,
            f"{self.file_name.name}.xlsx"
        )

    def copy_working(self, target: Folder = None):
        if self.status in (
                'Not Started',
                'In Progress',
                'Re-work In Progress',
                'Has Creator Assignment'
        ):
            return
        if not target:
            ROOT = [
                *FILE_PATH,
                self.file_name.lang,
                self.file_name.phase,
                self.file_name.domain
            ]
            paths = {
                'IntentCreator': [
                    *ROOT,
                    'Intent',
                    'QC'
                ],
                'IntentQC': [
                    *ROOT,
                    'Utterance',
                    'Intent'
                ],
                'UtteranceCreator': [
                    *ROOT,
                    'Utterance',
                    'QC'
                ],
                'UtteranceQC': [
                    *ROOT,
                    'DeliveryPrep'
                ]
            }
            target_path = paths.get(f"{self.file_name.task}{self.role}")
            target = AIE_DRIVE.get_item_by_path(*target_path)
        if target and (item := self.get_working()):
            if (previous_version := target.get_item(item.name)):
                if self.role == 'QC':
                    if self.file_name.task == 'Intent':
                        self.prep_utts()
                    return
                logger.info(f"Copying {item} to {target}")
                for i in range(1, 100):
                    previous_name = f"{item.name.split('.')[0]}_v{i}.xlsx"
                    previous = target.get_item(previous_name)
                    if not previous:
                        break
                previous_version.copy(target, name=previous_name)
                previous_version.delete()
            item.copy(target)
            if self.role == 'Creator' and self.file_name.task == 'Utterance':
                try:
                    qc_file = target.get_item(item.name)
                    self.qc_check(qc_file)
                except ValueError as e:
                    logger.error(f"Problem with {item.name}: {e}")
            if self.role == 'QC':
                if self.file_name.task == 'Intent':
                    self.prep_utts()

    def move_working(self, target: str = None):
        target = target or self.status
        if target in ['Not Active']:
            return
        if target in ['In Progress', 'Re-work In Progress']:
            item = self.get_working(in_progress=True)
            if not item:
                for status in (
                        'Completed',
                        'Accepted',
                        'Rejected',
                        'Re-work Completed'
                ):
                    item = self.get_working(target=status)
                    if item:
                        logger.info(f"{item.name} already moved by {self}; new status: {status}.")
                        self.status = status
                        break

            return
        if (item := self.get_working(in_progress=True)):
            if item.parent_path.split('/')[-1] in ['Media_Cable', 'Finance'] and self.role == 'Creator':
                completed_item = self.get_working(target='Completed')
                if item.get_versions()[0].modified_by.display_name != 'Ryan O\'Rourke':
                    self.status = 'Re-work In Progress' if completed_item else 'In Progress'
            target_folder = PROJ_DRIVE.get_item_by_path(
                *PROJ_PATH,
                self.file_name.lang,
                self.file_name.phase,
                self.role,
                self.resource_code,
                self.file_name.domain,
                target
            )
            if target_folder:
                if (previous_version := target_folder.get_item(self.file_name.name)):
                    previous_version.copy(
                        target_folder,
                        name=f"{self.file_name.name}_{datetime.datetime.utcnow().strftime('%Y%m%d')}.xlsx"
                    )
                    previous_version.delete()
                item.move(target_folder)

    def qc_check(self, qc_file: File):
        qc_check(qc_file)

    def prep_utts(self):
        logger.info(f"Prepping utterances from intents for {self.file_name}")
        UTT_PATH = [
            *FILE_PATH,
            self.file_name.lang,
            self.file_name.phase,
            self.file_name.domain,
            'Utterance'
        ]
        prep_folder = AIE_DRIVE.get_item_by_path(
            *UTT_PATH,
            'Prep'
        )
        template = prep_folder.get_item('TEMPLATE.xlsx')
        intent_folder = AIE_DRIVE.get_item_by_path(
            *UTT_PATH,
            'Intent'
        )
        out_folder = AIE_DRIVE.get_item_by_path(
            *UTT_PATH,
            'Creator'
        )

        int_file = intent_folder.get_item(self.file_name.name)
        in_file = prep_folder.get_item(self.file_name.name.split('_', 3)[3])
        out_file = out_folder.get_item(in_file.name)
        if out_file:
            logger.info(f"{self.file_name.name} done already")
            return
        in_wb = WorkBook(in_file)
        in_ws = in_wb.get_worksheet('Sample Utterances')
        template.copy(out_folder, name=in_file.name)
        int_wb = WorkBook(int_file)
        int_ws = int_wb.get_worksheet('Intent_Slot Creation')
        out_file = out_folder.get_item(in_file.name)
        out_wb = WorkBook(out_file)
        out_ws = [ws for ws in out_wb.get_worksheets()]
        out_intents = out_ws[0].get_range('Intents')
        in_intents = in_ws.get_range(out_intents.address.split('!')[1])
        out_intents.update(values=in_intents.values)
        addresses = (
            ('H7:H16', 'DataValidation!A2:A12'),
            ('H17:H26', 'DataValidation!B2:B12'),
            ('H27:H36', 'DataValidation!C2:C12'),
            ('H37:H46', 'DataValidation!D2:D12'),
            ('H47:H56', 'DataValidation!E2:E12')
        )
        for inloc, outloc in addresses:
            inrange = int_ws.get_range(inloc)
            slots = inrange.values
            slots.append(['Null'])
            outrange = out_ws[1].get_range(outloc)
            outrange.update(values=slots)
        modrange = out_ws[0].get_range('Modality')
        modality = modrange.values
        random.shuffle(modality)
        modrange.update(values=modality)
        logger.info(f"Utterance prep for {self} completed")

    def process(self):
        self.move_working()
        if self.status in [
            'Completed',
            'Re-work Completed',
            'Accepted',
            'Rejected'
        ]:
            self.copy_working()
            self.status = 'Needs Assignment'
        if not self.summary:
            self.get_file_status()


class FileBook(DataFrameXL):
    drive: Drive = AIE_DRIVE

    def __init__(
            self,
            lang: str = 'EN-US',
            phase: str = '_Training',
            drive: Drive = AIE_DRIVE
    ):
        super().__init__(
            *FILE_PATH,
            lang,
            phase,
            'FileBook.xlsx',
            drive=drive
        )
        for task in ('Intent', 'Utterance'):
            for role in ('Creator', 'QC'):
                sheet_name = f"{task}{role}"
                ws = self.worksheets.get(sheet_name)
                df = self.dfs.get(sheet_name)
                self.__setattr__(
                    sheet_name,
                    FileSheet(task, role, ws, df)
                )

    def publish_all(self):
        for task, role in STEPS:
            sheet = getattr(self, f"{task}{role}")
            sheet.publish()

    def reset(
            self,
            role: Optional[str] = None,
            task: Optional[str] = None,
            status_only: bool = True,
            prereq_only: bool = True
    ):
        roles = [role] if role else ['Creator', 'QC']
        tasks = [task] if task else ['Intent', 'Utterance']
        steps = [
            f"{task}{role}"
            for task in tasks
            for role in roles
        ]
        steps.sort()
        for i, (task, role) in enumerate(STEPS):
            step = f"{task}{role}"
            if step not in steps:
                continue
            step = getattr(self, step)
            prestep = None
            if i != 0:
                prestep_name = f"{STEPS[i - 1][0]}{STEPS[i - 1][1]}"
                prestep = getattr(self, prestep_name)
            for j, file in enumerate(step.files):
                if not prestep and prereq_only:
                    continue
                if prestep:
                    prereq = prestep[j]
                    logger.debug(f"{prereq=}, {file=}")
                    if prereq.status not in (
                            'Completed',
                            'Re-work Completed',
                            'Accepted'
                    ):
                        file.status = 'Not Ready'
                    if file.status == 'Not Ready':
                        file.status = 'Not Started' if prereq.status in (
                            'Completed',
                            'Re-work Completed',
                            'Accepted'
                        ) else file.status
                if not status_only:
                    file.resource_name = 'Unassigned'
                    file.resource_code = 'Unassigned'


class ResourceSheet(DataFrameXL):
    def __init__(
            self,
            lang: str = 'EN-US',
            phase: str = '_Training',
            role: str = 'Creator',
            drive: Drive = PROJ_DRIVE
    ):
        super().__init__(
            *PROJ_PATH,
            lang,
            phase,
            role,
            f"{lang}_LargeBot_{role}_Resources_List.xlsx",
            drive=drive
        )
        self.lang = lang
        self.phase = phase
        self.role = role
        self.ws = self.worksheets.get(lang)
        self.ws.unprotect()
        self.df = self.dfs.get(lang)
        self.resources = [
            ResourceAssignment(*resource, role, lang, phase)
            for resource in self.df.values.tolist()
        ]
        for resource in self.resources:
            self.__setattr__(
                resource.resource_code,
                resource
            )
            self.__setattr__(
                resource.resource_name,
                resource
            )

    @property
    def codes(self):
        return [
            resource.resource_code
            for resource in self.resources
        ]

    @property
    def names(self):
        return [
            resource.resource_name
            for resource in self.resources
        ]

    def block(self):
        frange = self.ws.get_range(f"A2:D{len(self.values) + 1}")
        format = frange.get_format()
        format.background_color = '#ffd8cc'
        format.update()
        self.ws.protect()

    def unblock(self):
        self.ws.unprotect()
        frange = self.ws.get_range(f"A2:D{len(self.values) + 1}")
        format = frange.get_format()
        ws = self.get_worksheet('Data')
        data_range = {
            'EN-US': 'A1',
            'ES-US': 'B1'
        }
        _range = ws.get_range(data_range.get(self.lang))
        _range.update(
            values=[
                [f"{arrow.utcnow()}"]
            ]
        )
        format.background_color = None
        format.update()
        self.publish()

    @property
    def values(self):
        return [
            [*resource]
            for resource in self.resources
        ]

    def publish(self):
        _range = self.ws.get_range(f"A2:D{len(self.values) + 1}")
        _range.update(
            values=self.values
        )

    def get_resource_status(self, resource_code: str):
        resource = getattr(self, resource_code, None)
        if resource:
            return {
                'ResourceCode': resource.resource_code,
                'ResourceName': resource.resource_name,
                'FileName': resource.file_name.name,
                'Status': resource.status
            }


class TeamsMessage:
    def __init__(self, task: str = 'Utterance', role: str = 'Creator', lang: str = 'EN-US', phase: str = '_Training'):
        self.book = FileBook(lang=lang, phase=phase)

        self.summary = getattr(self.book, f"{task}{role}").summary()

        self.message = pymsteams.connectorcard(WEBHOOKS.get(role))
        self.message.summary(f"{task} {role} Progress")
        table = f"""\n
        \t{task} {role} Progress
        \t\t\tFinance\t\tMedia_Cable
        Completed\t\t{self.summary['Finance'].get('Completed', 0)}\t\t\t{self.summary['Media_Cable'].get('Completed', 0)}
        Not Started\t\t{self.summary['Finance'].get('Not Started', 0)}\t\t\t{self.summary['Media_Cable'].get('Not Started', 0)}
        In Progress\t\t{self.summary['Finance'].get('In Progress', 0)}\t\t\t{self.summary['Media_Cable'].get('In Progress', 0)}
        """ if role == 'Creator' else f"""\n
        \t{task} {role} Progress
        \t\t\tFinance\t\tMedia_Cable
        Accepted\t\t{self.summary['Finance'].get('Accepted', 0)}\t\t\t{self.summary['Media_Cable'].get('Accepted', 0)}
        Rejected\t\t{self.summary['Finance'].get('Rejected', 0)}\t\t\t{self.summary['Media_Cable'].get('Rejected', 0)}
        Not Started\t\t{self.summary['Finance'].get('Not Started', 0)}\t\t\t{self.summary['Media_Cable'].get('Not Started', 0)}
        In Progress\t\t{self.summary['Finance'].get('In Progress', 0)}\t\t\t{self.summary['Media_Cable'].get('In Progress', 0)}
        """
        self.message.text(table)

    def print(self):
        self.message.printme()

    def send(self):
        self.message.send()


class ResourceBot:
    def __init__(
            self,
            lang: str = 'EN-US',
            phase: str = '_Training',
            dry_run: bool = False
    ):
        self.lang = lang
        self.phase = phase
        self.Creator = ResourceSheet(lang, phase, role='Creator')
        self.QC = ResourceSheet(lang, phase, role='QC')
        self.file_book = FileBook(lang, phase)
        self.dry_run = dry_run
        self.pending_assignments = []

    def __enter__(self):
        self.block()
        return self

    def __exit__(self, type, value, traceback):
        self.unblock()

    def block(self):
        self.Creator.block()
        self.QC.block()

    def unblock(self):
        for resource, assignment in self.pending_assignments:
            logger.info(f"Actually assigning {assignment} to {resource}")
            resource.assign(assignment)
        if not self.dry_run:
            self.Creator.unblock()
            self.QC.unblock()
            self.file_book.publish_all()

    def refresh(self, status_only: bool = False, prereq_only: bool = False):
        self.file_book.reset('Creator', 'Intent')
        for task, role in STEPS:
            resource_sheet = getattr(self, role)
            file_sheet = getattr(self.file_book, f"{task}{role}")
            for resource in resource_sheet.resources[::-1]:
                resource.process()
                for file_assignment in resource.summary.get(task, []):
                    if (
                            (file_sheet_assignment := getattr(file_sheet, file_assignment.file_name.name, None))
                            and file_assignment != file_sheet_assignment
                    ):
                        logger.debug(
                            f"Updating {role} file assignment for {file_sheet_assignment} to {file_assignment}.")
                        object.__setattr__(
                            file_sheet,
                            file_assignment.file_name.name,
                            file_assignment
                        )
            self.file_book.reset(role, task, status_only=status_only, prereq_only=prereq_only)
            # resource_sheet.publish()

    def populate_source_folder(self, role: str = None, task: str = None):
        folders = {
            'Creator': ['Completed', 'Re-work Completed'],
            'QC': ['Accepted']
        }
        errors = []
        for resource in getattr(self, role).resources:
            if not resource.summary:
                resource.get_file_status()
            for domain in ['Media_Cable', 'Finance']:
                ROOT = [
                    *FILE_PATH,
                    self.lang,
                    self.phase,
                    domain
                ]
                paths = {
                    'IntentCreator': [
                        *ROOT,
                        'Intent',
                        'QC'
                    ],
                    'IntentQC': [
                        *ROOT,
                        'Utterance',
                        'Intent'
                    ],
                    'UtteranceCreator': [
                        *ROOT,
                        'Utterance',
                        'QC'
                    ],
                    'UtteranceQC': [
                        *ROOT,
                        'DeliveryPrep'
                    ]
                }
                path = paths.get(f"{task}{role}")
                if not path:
                    logger.error(f"No source folder path for {task}{role}")
                target = AIE_DRIVE.get_item_by_path(*path)
                file_names = [item.name.split('.')[0] for item in target.get_items()]
                for file in resource.summary.get(task, []):
                    if file.file_name.domain != domain or file.status not in folders.get(role):
                        continue
                    if file.file_name.name in file_names:
                        logger.debug(f"{file} already copied; skipping")
                        continue
                    logger.info(f"Copying {file} to source for next step.")
                    try:
                        file.copy_working()
                    except (ValueError, HTTPError) as e:
                        logger.info(f"Error with {file}: {e}")
                        errors.append(file)
        logger.info(f"These files were not processed: {errors}")

    def assign(self):
        steps = (
            'IntentCreator',
            'UtteranceCreator',
            'IntentQC',
            'UtteranceQC'
        )
        for resource_list in (self.Creator,):
            for resource in resource_list.resources:
                status = resource.status
                if resource.needs_assignment:
                    for step in steps:
                        if resource.role not in step:
                            continue
                        file_sheet = getattr(self.file_book, step)
                        try:
                            index = file_sheet.file_names.index(resource.file_name.name.lower())
                            file_sheet[index].status = status
                            assignment = next(file_sheet.unassigned)
                            assignment.resource_name = resource.resource_name
                            logger.info(f"Queuing assigning {assignment} to {resource}")
                            self.pending_assignments.append(
                                (resource, assignment)
                            )
                            break
                        except StopIteration:
                            logger.info(f"No unassigned files for {step}.")
                            continue
                if resource.role == 'Creator' and resource.resource_name in self.QC.names:
                    if not resource.needs_assignment:
                        qc_resource = getattr(self.QC, resource.resource_name)
                        qc_resource.status = 'Has Creator Assignment'

    def assign_one(self, resource_code: str):
        matrix = {
            'Cr': (getattr(self.file_book, 'UtteranceCreator'), self.Creator),
            'QC': (getattr(self.file_book, 'UtteranceQC'), self.QC)
        }
        file_sheet, resource_list = matrix.get(resource_code.split('_')[1])
        resource = getattr(resource_list, resource_code)
        status = resource.status
        resource.process()
        if resource.needs_assignment:
            try:
                index = file_sheet.file_names.index(resource.file_name.name.lower())
                file_sheet[index].status = status
                assignment = next(file_sheet.unassigned)
                assignment.resource_name = resource.resource_name
                resource.assign(assignment)
                if not self.dry_run:
                    file_sheet.publish()
                    resource_list.publish()
            except StopIteration:
                pass
        return {
            'ResourceCode': resource.resource_code,
            'ResourceName': resource.resource_name,
            'FileName': resource.file_name.name,
            'Status': resource.status
        }

    def rebuild_file_sheet(self, role: str):
        for resource in getattr(self, role).resources[::-1]:
            if not resource.summary:
                resource.get_file_status()
            for task in resource.summary:
                file_sheet = getattr(self.file_book, f"{task}{role}")
                for file in resource.summary[task]:
                    if file.file_name.name.lower() in file_sheet.file_names:
                        logger.info(f"Updating {file} in {file_sheet}")
                        index = file_sheet.file_names.index(file.file_name.name.lower())
                        file_sheet[index].status = file.status
                        file_sheet[index].resource_name = file.resource_name
                        file_sheet[index].resource_code = file.resource_code

    def rebuild_file_sheets(self):
        for role in ('Creator', 'QC'):
            self.rebuild_file_sheet(role)
        for sheet_name in ('IntentCreator', 'IntentQC', 'UtteranceCreator', 'UtteranceQC'):
            file_sheet = getattr(self.file_book, sheet_name)
            for file in file_sheet.files:
                print(f"{file.file_name.name}\t{file.status}\t{file.resource_name}\t{file.resource_code}")


def how_long(
        LANG: str = 'EN-US',
        PHASE: str = '_Training'
):
    for ROLE in ['Creator', 'QC']:
        PATH = [
            *PROJ_PATH,
            LANG,
            PHASE,
            ROLE,
            f"{LANG}_LargeBot_{ROLE}_Resources_List.xlsx"
        ]
        ADDRESS = {
            'EN-US': 'A1',
            'ES-US': 'B1'
        }
        wb = WorkBook(PROJ_DRIVE.get_item_by_path(*PATH))
        last_updated = wb.get_worksheet('Data').get_range(ADDRESS.get(LANG)).values[0][0]
        _range = wb.get_worksheet(LANG).get_range('E1')
        _range.update(
            values=[
                [f"Notes - last updated {arrow.get(last_updated).humanize()}"]
            ]
        )