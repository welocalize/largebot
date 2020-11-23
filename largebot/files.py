from __future__ import annotations

import pandas as pd

from welo365 import O365Account, WorkBook, Folder, Drive

from largebot.logger import get_logger
from largebot.pd import get_df

logger = get_logger(__name__)

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
    'Bot Training & Testing Data (LargeBot) (Akshat)',
    AIE_SWITCH,
    'Files for Processing'
]
KEY_PATH = [
    *AIE_PATH,
    'Intent_Intent IDs Keys'
]
FILE_PATH = [
    *AIE_PATH,
    'Processed Files'
]


logger.debug('Getting welo365 Account.')
ACCOUNT = O365Account()
logger.debug('Getting AIE internal drive.')
AIE_DRIVE = ACCOUNT.get_site(AIE_SITE).get_default_document_library()
logger.debug('Getting Project Folder drive.')
PROJ_DRIVE = ACCOUNT.get_site(PROJ_SITE).get_default_document_library()
logger.debug('Building ResourceList.')


class TaskFile:
    def __init__(self, name: str, status: str, assignment: str, domain_key: DomainKeyFile):
        self.name = name
        self.file = domain_key.folder.get_item(name)
        self.domain = domain_key.domain
        self.role = domain_key.role
        self._status = status
        self._assignment = assignment

    def __repr__(self):
        return f"{self.domain}TaskFile: {self.name} [{self._status}]"

    def __iter__(self):
        return iter((self._status, self._assignment))

    @property
    def assignment(self):
        return self._assignment

    @assignment.setter
    def assignment(self, assignment: str):
        self._assignment = assignment

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status: str):
        self._status = status

    def update(self, status: str = None, assignment: str = None):
        self.status = status or self._status
        self.assignment = assignment or self._assignment

    @property
    def unassigned(self):
        return bool(self.assignment == 'Unassigned')

    @property
    def assigned(self):
        return not self.unassigned

    def copy(self, target: Folder):
        if (previous_copy := target.get_item(self.name)):
            logger.error(f"TaskFile {self.name} already present. Skipping to avoid risk of overwriting existing data.")
            return previous_copy
        return self.file.copy(target)

    def move(self, target: Folder):
        logger.debug(f"Moving file {self.name} to folder {target.name}.")
        return self.file.move(target)

    def assign(self, resource: Resource, dry_run: bool = False):
        logger.debug(f"Marking task {self.name} 'In Progress' and assigning to {resource.name} in Intent IDs tracker.")
        self.update(status='In Progress', assignment=resource.name)
        folder = resource.get_domain(self.domain).folder
        logger.debug(f"Copying source file from internal AIE directory to resource production folder.")
        if not dry_run:
            self.copy(folder)

    def record(self, status: str):
        logger.debug(f"Marking task {self.name} {status.capitalize()} in Intent IDs tracker.")
        self.update(status=status.capitalize())


class DomainFolder:
    def __init__(self, resource_folder: Folder, domain: str, role: str):
        self.folder = resource_folder.get_item(domain)
        self.parent = resource_folder
        self.completed = None
        self.accepted = None
        self.rejected = None
        if role == 'Creator':
            self.completed = self.folder.get_item('Completed')
            if self.completed is None:
                logger.debug(f"No 'Completed' folder in resource folder. Creating one.")
                self.completed = self.folder.create_child_folder('Completed')
            if (accepted := self.folder.get_item('Accepted')):
                logger.debug("Removing unnecessary 'Accepted' folder.")
                accepted.delete()
            if (rejected := self.folder.get_item('Rejected')):
                logger.debug("Removing unnecessary 'Rejected' folder.")
                rejected.delete()
        if role == 'QC':
            if (completed := self.folder.get_item('Completed')):
                logger.debug("Removing unnecessary 'Completed' folder.")
                completed.delete()
            self.accepted = self.folder.get_item('Accepted')
            if self.accepted is None:
                logger.debug(f"No 'Accepted' folder in resource folder. Creating one.")
                self.accepted = self.folder.create_child_folder('Accepted')
            self.rejected = self.folder.get_item('Rejected')
            if self.rejected is None:
                logger.debug(f"No 'Rejected' folder in resource folder. Creating one.")
                self.rejected = self.folder.create_child_folder('Rejected')


class Resource:
    def __init__(self, code: str, name: str, assignment: str, status: str, folder: Folder):
        self.code = code
        self.role = 'Creator' if code.split('_')[1] == 'Cr' else 'QC'
        self.folder = folder
        self.finance = DomainFolder(self.folder, 'Finance', self.role)
        self.media_cable = DomainFolder(self.folder, 'Media_Cable', self.role)
        self.name = name
        self._assignment = assignment
        self._status = status
        self.needs_released = None

    def __repr__(self):
        return f"{self.name} [{self.code}] - Assignment: {self._assignment} - Status: {self._status}"

    def __iter__(self):
        return iter((self.name, self._assignment, self._status))

    @property
    def assignment(self):
        return self._assignment

    @assignment.setter
    def assignment(self, assignment: str):
        self._assignment = assignment

    @property
    def assigned_domain(self):
        if self.assigned:
            return self.media_cable if self.assignment.split('_')[3] == 'MC' else self.finance

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status: str):
        self._status = status

    def update(self, assignment: str = None, status: str = None):
        self.assignment = assignment or self._assignment
        self.status = status or self._status

    def get_domain(self, domain: str = None):
        return getattr(self, domain.lower()) if domain else None

    @property
    def finished_manually(self):
        if self.assigned_domain and (domain_folder := self.assigned_domain.folder):
            return bool(folder.get_item(self.assignment) for folder in domain_folder.get_child_folders())
        return False

    @property
    def assignment_status(self):
        if self.unassigned:
            return 'N/A'
        assigned_file = None
        if self.assigned_domain and (assigned_file := self.assigned_domain.folder.get_item(self.assignment)):
            for status in ['Completed', 'Accepted', 'Rejected']:
                if (status_folder := getattr(self.assigned_domain, status.lower(), None)):
                    if (status_file := status_folder.get_item(self.assignment)):
                        if assigned_file is not None:
                            logger.warning(f"Duplicate files present. Removing production version.")
                            assigned_file.delete()
                        return status
        return 'In Progress' if assigned_file else 'N/A'

    @property
    def assigned(self):
        return bool(self.assignment not in ['', 'N/A'])

    @property
    def unassigned(self):
        return not self.assigned

    @property
    def completed(self):
        return bool(self.status == 'Completed')

    @property
    def accepted(self):
        return bool(self.status == 'Accepted')

    @property
    def rejected(self):
        return bool(self.status == 'Rejected')

    @property
    def needs_assignment(self):
        return self.completed or self.unassigned or self.accepted or self.rejected

    def assign(self, task_file: TaskFile, dry_run: bool = False):
        logger.debug(f"TaskFile {task_file.name} assigned to {self.code} and marked as such in Resource List.")
        self.update(assignment=task_file.name, status='Not Started')
        task_file.assign(self, dry_run=dry_run)

    def complete(self, dry_run: bool = False):
        if self.finished_manually:
            logger.info(f"{self.assignment} already moved to 'Completed' folder by resource.")
            if self.assignment_status == 'In Progress':
                logger.warning(f"Duplicate file {self.assignment} present in domain folder and 'Completed' folder.")
                self.assignment = ''
                return
        if (completed_file := self.assigned_domain.folder.get_item(self.assignment)):
            logger.info(f"Moving completed file {self.assignment} to 'Completed' folder.")
            if not dry_run:
                completed_file.move(self.assigned_domain.completed)
        self.needs_released = self.assignment
        self.assignment = ''

    def accept(self, dry_run: bool = False):
        if self.finished_manually:
            logger.info(f"{self.assignment} already moved to 'Accepted' folder by resource.")
            if self.assignment_status == 'In Progress':
                logger.warning(f"Duplicate file {self.assignment} present in domain folder and 'Accepted' folder.")
                self.assignment = ''
                return
        if (accepted_file := self.assigned_domain.folder.get_item(self.assignment)):
            logger.info(f"Moving accepted file {self.assignment} to 'Accepted' folder.")
            if not dry_run:
                logger.info(f"{self.assigned_domain.accepted=}, {self.assigned_domain.folder=}")
                accepted_file.move(self.assigned_domain.accepted)
        self.assignment = ''

    def reject(self, rejected_resource: Resource, dry_run: bool = False):
        if self.finished_manually:
            logger.info(f"{self.assignment} already moved to 'Rejected' folder by resource.")
            if self.assignment_status == 'In Progress':
                logger.warning(f"Duplicate file {self.assignment} present in domain folder and 'Rejected' folder.")
                self.assignment = ''
                return
        if (rejected_file := self.assigned_domain.folder.get_item(self.assignment)):
            logger.info(f"Moving rejected file {self.assignment} to 'Rejected' folder.")
            logger.info(f"Reassigning rejected file {rejected_file} to {rejected_resource.name} [{rejected_resource.code}].")
            if not dry_run:
                rejected_file.move(self.assigned_domain.rejected)
                domain = 'Media_Cable' if rejected_file.name.split('_')[3] == 'MC' else 'Finance'
                rejected_file.copy(rejected_resource.get_domain(domain).folder)
        self.assignment = ''

    def process(self, task_file: TaskFile, file_list: FileList, resource_list: ResourceList = None, dry_run: bool = False):
        logger.debug(f"Process: {self.status=}")
        if self.finished_manually and self.status == 'In Progress':
            logger.debug(f"Updating status to {self.assignment_status}.")
            self.status = self.assignment_status
        logger.debug(f"Process after finished_manually: {self.status=}")
        if self.completed:
            logger.debug(f"Completing {self.assignment} for {self.name} [{self.code}].")
            self.complete(dry_run=dry_run)
            task_file.record(status='Completed')
        logger.debug(f"Process after completed: {self.status=}")
        if self.accepted:
            logger.debug(f"Processing {self.assignment} as 'Accepted' by {self.name} [{self.code}].")
            self.accept(dry_run=dry_run)
            task_file.record(status='Accepted')
        logger.debug(f"Process after accepted: {self.status=}")
        if self.rejected:
            logger.debug(f"Processing {self.assignment} as 'Rejected' by {self.name} [{self.code}].")
            rejected_task_file = file_list.get_single_task_file(self.assignment, role='Creator')
            rejected_resource = resource_list.get_single_resource(rejected_task_file.assignment, role='Creator')
            self.reject(rejected_resource, dry_run=dry_run)
            task_file.record(status='Rejected')
        logger.debug(f"Process after rejected: {self.status=}")
        if self.needs_assignment:
            logger.debug(f"Assigning {task_file} to {self.name} [{self.code}].")
            self.assign(task_file, dry_run=dry_run)
            logger.debug(f"Process after needs_assignment: {self.status=}")
            return
        if self.status == 'In Progress' and self.assignment_status != 'In Progress':
            logger.warning(f"Assigned file {self.assignment} not in working folder. Recopying from central repository.")
            assigned_file = file_list.get_single_task_file(self.assignment, role=self.role)
            assigned_file.assign(self)
        logger.debug(f"Process after final: {self.status=}")
        return task_file


class DomainKeyFile:
    def __init__(self, drive: Drive, domain: str, phase: str, lang: str, task: str, role: str):
        self.drive = drive
        self.domain = domain
        self.phase = phase
        self.lang = lang
        self.task = task
        self.role = role
        self.key_path = [
            *KEY_PATH,
            f"{domain}_Intent Key.xlsx"
        ]
        logger.debug(f"Getting {domain} key file.")
        self.key = self.drive.get_item_by_path(*self.key_path)
        logger.debug(f"Getting {domain} WorkBook object.")
        self.wb = WorkBook(self.key)
        logger.debug(f"Getting {domain} WorkSheet object.")
        self.ws = self.wb.get_worksheet(f"{task}{role}Files")
        logger.debug(f"Getting {domain} DataFrame object.")
        self.df = get_df(self.ws)
        self.df['Domain'] = domain
        self.file_path = [
            *FILE_PATH,
            lang,
            phase,
            domain,
            f"{task}s",
            role
        ]
        logger.debug(f"Getting {domain} file folder.")
        self.folder = self.drive.get_item_by_path(*self.file_path)


class FileList:
    def __init__(self, drive: Drive, phase: str, lang: str, task: str, role: str):
        self.drive = drive
        self.task = task
        self.role = role
        logger.debug('Getting Media_Cable Key object.')
        self.media_cable = DomainKeyFile(drive, 'Media_Cable', phase, lang, task, role)
        logger.debug(f"{self.media_cable=}")
        logger.debug('Getting Finance Key object.')
        self.finance = DomainKeyFile(drive, 'Finance', phase, lang, task, role)
        logger.debug(f"{self.finance=}")
        logger.debug('Building combined DataFrame object for all TaskFile info.')
        logger.debug(f"Finance DF\n{self.finance.df=}")
        logger.debug(f"Media_Cable DF\n{self.media_cable.df=}")
        self.df = self.media_cable.df.append(self.finance.df)
        self.filenames = self.df.index.tolist()
        logger.debug(f"{self.get_domain(filename='EN_Tr_Ints_Fi_100')=}")
        logger.debug('Buliding dictionary of TaskFile objects.')
        self.task_files = (
            TaskFile(
                filename,
                *assignment,
                domain_folder
            )
            for filename, assignment in zip(
                self.filenames,
                self.df.drop(columns=['Domain']).values.tolist()
            )
            if (domain_folder := self.get_domain(filename=filename))
        )
        self.processed = []

    def get_single_task_file(self, filename: str, role: str):
        domain_folder = self.get_domain(filename=filename)
        task = 'Intent' if filename.split('_')[2][0] == 'I' else 'Utterance'
        ws = domain_folder.wb.get_worksheet(f"{task}{role}Files")
        row = int(filename.split('_')[-1]) + 1
        _range = ws.get_range(f"B{row}:C{row}")
        return TaskFile(
            filename,
            *_range.values[0],
            domain_folder
        )

    def get_domain(self, filename: str = None, domain: str = None):
        if filename:
            return self.media_cable if filename.split('_')[3] == 'MC' else self.finance
        if domain:
            return self.media_cable if domain == 'Media_Cable' else self.finance

    def __iter__(self):
        yield from self.task_files

    def update(self, finance_values: list = None, media_cable_values: list = None, dry_run: bool = False):
        if dry_run:
            return
        for domain, values in [('Finance', finance_values), ('Media_Cable', media_cable_values)]:
            if values:
                address = f"B2:{'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[len(values[0])]}{len(values) + 1}"
                _range = self.get_domain(domain=domain).ws.get_range(address)
                _range.update(values=values)


class ResourceList:
    def __init__(self, drive: Drive, lang: str = 'EN-US', phase: str = '_Training', role: str = 'Creator'):
        self.lang = lang
        self.phase = phase
        self.role = role
        self.drive = drive
        self.path = [
            *PROJ_PATH,
            lang,
            phase,
            role
        ]
        logger.debug('Getting Resource List.')
        self.file = self.drive.get_item_by_path(*self.path, f"{lang}_LargeBot_{role}_Resources_List.xlsx")
        logger.debug('Getting Resource List WorkBook object.')
        self.wb = WorkBook(self.file)
        logger.debug('Getting Resource List WorkSheet object.')
        self.ws = self.wb.get_worksheet(lang)
        self.ws.unprotect()
        logger.debug('Getting Resource List DataFrame object.')
        self.df = get_df(self.ws)
        self.frange = self.ws.get_range(f"A2:E{len(self.df) + 1}")
        self.format = self.frange.get_format()
        self.format.background_color = '#ffd8cc'
        self.format.update()
        self.ws.protect()
        self.resource_codes = self.df.index.tolist()
        logger.debug(f"{self.resource_codes=}")
        logger.debug(f"{self.df.values.tolist()=}")
        resource_folders = [
            item
            for item in self.drive.get_item_by_path(*self.path).get_items()
            if item.name in self.resource_codes
        ]
        logger.debug(f"{resource_folders=}")
        logger.debug('Building dictionary of resources.')
        self.resources = (
            Resource(resource_code, *assignment, folder)
            for resource_code, assignment, folder in zip(
                self.resource_codes,
                self.df.values.tolist(),
                tuple(
                    item
                    for item in self.drive.get_item_by_path(*self.path).get_items()
                    if item.name in self.resource_codes
                )
            )
        )
        self.processed = []

    def get_single_resource(self, resource_name: str, role: str):
        path = [*self.path[:-1], role]
        file = self.drive.get_item_by_path(*path, f"{self.lang}_LargeBot_{role}_Resources_List.xlsx")
        wb = WorkBook(file)
        ws = wb.get_worksheet(self.lang)
        df = get_df(ws)
        code = self.get_code_by_name(resource_name, df)
        folder = self.drive.get_item_by_path(*path).get_item(code)
        return Resource(code, resource_name, df.loc[code]['Assignment'], df.loc[code]['Status'], folder)

    def __iter__(self):
        yield from self.resources

    def __len__(self):
        return len(self.resource_codes)

    def update(self, values: list = None, file_list: FileList = None, dry_run: bool = False):
        self.ws.unprotect()
        if values and not dry_run:
            address = f"B2:{'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[len(values[0])]}{len(values) + 1}"
            _range = self.ws.get_range(address)
            _range.update(values=values)
            if self.role == 'Creator' and file_list is not None:
                self.release_qc_files(file_list=file_list)
        self.format.background_color = None
        self.format.update()

    def release_qc_files(self, file_list: FileList):
        for filename in [to_release for resource in self.processed if (to_release := resource.needs_released)]:
            logger.info(f"Releasing QC file for {filename}.")
            domain_key = file_list.get_domain(filename=filename)
            task = 'Intent' if filename.split('_')[2][0] == 'I' else 'Utterance'
            ws = domain_key.wb.get_worksheet(f"{task}QCFiles")
            _range = ws.get_range(filename)
            _range.values = [['Not Started', 'Unassigned']]
            _range.update()

    def get_code_by_name(self, resource_name: str, df: pd.DataFrame = None):
        df = df if df is not None else self.df
        return {
            name: code
            for name, code in zip(list(df['Name']), df.index.tolist())
        }.get(resource_name)

    def collect_creator_completed(self):
        for resource in self.resources:
            for domain in ['Finance', 'Media_Cable']:
                for task in ['Intents', 'Utterances']:
                    qc_folder = AIE_DRIVE.get_item_by_path(*FILE_PATH, self.lang, self.phase, domain, task, 'QC')
                    completed_folder = resource.get_domain(domain).completed
                    for item in completed_folder.get_items():
                        if item.is_file:
                            item.copy(qc_folder)

def assign_creators(
        LANG: str = 'EN-US',
        PHASE: str = '_Training',
        TASK: str = 'Intent',
        check_assignments: bool = False,
        dry_run: bool = False
):
    ROLE = 'Creator'
    FILE_LIST = FileList(
        drive=AIE_DRIVE,
        phase=PHASE,
        lang=LANG,
        task=TASK,
        role=ROLE
    )
    RESOURCE_LIST = ResourceList(
        drive=PROJ_DRIVE,
        lang=LANG,
        phase=PHASE,
        role=ROLE
    )

    for task_file in FILE_LIST:
        logger.info(f"Processing {task_file}.")
        FILE_LIST.processed.append(task_file)
        if task_file.assigned:
            logger.debug(f"No action needed for {task_file}.")
            continue
        for resource in RESOURCE_LIST.resources:
            logger.info(f"Processing {resource}.")
            task_file = resource.process(task_file, FILE_LIST, RESOURCE_LIST, dry_run=dry_run)
            RESOURCE_LIST.processed.append(resource)
            if not task_file:
                break
        else:
            logger.info('All resources have been processed. Exiting loop.')
            break

    FILE_LIST.processed.sort(key=lambda x: x.name)
    RESOURCE_LIST.processed.sort(key=lambda x: x.code)

    FILE_LIST.update(
        finance_values=[
            [*task_file]
            for task_file in FILE_LIST.processed
            if task_file.domain == 'Finance'
        ],
        media_cable_values=[
            [*task_file]
            for task_file in FILE_LIST.processed
            if task_file.domain == 'Media_Cable'
        ],
        dry_run=dry_run
    )
    RESOURCE_LIST.update(
        values=[
            [*resource]
            for resource in RESOURCE_LIST.processed
        ],
        file_list=FILE_LIST,
        dry_run=dry_run
    )

def assign_qcs(
        LANG: str = 'EN-US',
        PHASE: str = '_Training',
        TASK: str = 'Intent',
        check_assignments: bool = False,
        dry_run: bool = False
):
    ROLE = 'QC'
    logger.debug('Getting welo365 Account.')
    ACCOUNT = O365Account()
    logger.debug('Getting AIE internal drive.')
    AIE_DRIVE = ACCOUNT.get_site(AIE_SITE).get_default_document_library()
    logger.debug('Getting Project Folder drive.')
    PROJ_DRIVE = ACCOUNT.get_site(PROJ_SITE).get_default_document_library()
    logger.debug('Building ResourceList.')
    FILE_LIST = FileList(
        drive=AIE_DRIVE,
        phase=PHASE,
        lang=LANG,
        task=TASK,
        role=ROLE
    )
    RESOURCE_LIST = ResourceList(
        drive=PROJ_DRIVE,
        lang=LANG,
        phase=PHASE,
        role=ROLE
    )

    for task_file in FILE_LIST:
        logger.info(f"Processing {task_file}.")
        FILE_LIST.processed.append(task_file)
        if task_file.assigned:
            logger.debug(f"No action needed for {task_file}.")
            continue
        for resource in RESOURCE_LIST.resources:
            logger.info(f"Processing {resource}.")
            RESOURCE_LIST.processed.append(resource)
            task_file = resource.process(task_file, FILE_LIST, RESOURCE_LIST, dry_run=dry_run)
            if not task_file:
                break
        else:
            logger.info('All resources have been processed. Exiting loop.')
            break

    FILE_LIST.processed.sort(key=lambda x: x.name)
    RESOURCE_LIST.processed.sort(key=lambda x: x.code)

    FILE_LIST.update(
        finance_values=[
            [*task_file]
            for task_file in FILE_LIST.processed
            if task_file.domain == 'Finance'
        ],
        media_cable_values=[
            [*task_file]
            for task_file in FILE_LIST.processed
            if task_file.domain == 'Media_Cable'
        ],
        dry_run=dry_run
    )
    RESOURCE_LIST.update(
        values=[
            [*resource]
            for resource in RESOURCE_LIST.processed
        ],
        dry_run=dry_run
    )