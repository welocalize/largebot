from __future__ import annotations

import re

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
        self.domain = 'Finance' if name.split('_')[3][0] == 'F' else 'Media_Cable'
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

    @property
    def ready(self):
        return bool(self.status != 'Not Ready')

    @property
    def needs_assignment(self):
        return self.unassigned and self.ready

    def copy(self, target: Folder):
        if (previous_copy := target.get_item(self.name)):
            logger.error(f"TaskFile {self.name} already present. Skipping to avoid risk of overwriting existing data.")
            return previous_copy
        return self.file.copy(target)

    def move(self, target: Folder):
        logger.debug(f"Moving file {self.name} to folder {target.name}.")
        return self.file.move(target)

    def assign(self, resource: Resource, dry_run: bool = False):
        logger.info(f"Marking task {self.name} 'In Progress' and assigning to {resource.name} in Intent IDs tracker.")
        self.update(status='In Progress', assignment=resource.name)
        folder = resource.get_domain(self.domain).folder
        logger.debug(f"Copying source file from internal AIE directory to resource production folder.")
        if not dry_run:
            self.copy(folder)

    def record(self, status: str):
        logger.info(f"Marking task {self.name} {status.capitalize()} in Intent IDs tracker.")
        self.update(status=status.capitalize())


class DomainFolder:
    def __init__(self, resource_folder: Folder, domain: str, role: str):
        self.folder = resource_folder.get_item(domain)
        self.parent = resource_folder
        self.completed = None
        self.re_work_completed = None
        self.accepted = None
        self.rejected = None
        if role == 'Creator':
            folders = list(self.folder.get_child_folders())
            self.completed = next(
                filter(
                    lambda x: x.name == 'Completed',
                    folders
                ),
                None
            ) or self.folder.create_child_folder('Completed')
            self.re_work_completed = next(
                filter(
                    lambda x: x.name in ['Re-work Completed', 'Re-work Complete'],
                    folders
                ),
                None
            ) or self.folder.create_child_folder('Re-work Completed')
            if self.re_work_completed.name == 'Re-work Complete':
                self.re_work_completed = self.re_work_completed.move(self.folder, name='Re-work Completed')
            if (accepted := next(filter(lambda x: x.name == 'Accepted', folders), None)):
                logger.debug("Removing unnecessary 'Accepted' folder.")
                accepted.delete()
            if (rejected := next(filter(lambda x: x.name == 'Rejected', folders), None)):
                logger.debug("Removing unnecessary 'Rejected' folder.")
                rejected.delete()
        if role == 'QC':
            folders = list(self.folder.get_child_folders())
            if (completed := next(filter(lambda x: x.name == 'Completed', folders), None)):
                logger.debug("Removing unnecessary 'Completed' folder.")
                completed.delete()
            if (re_work_completed := next(filter(lambda x: x.name == 'Re-work Completed', folders), None)):
                logger.debug("Removing unnecessary 'Re-work Completed' folder.")
                re_work_completed.delete()
            self.accepted = next(
                filter(
                    lambda x: x.name == 'Accepted',
                    folders
                ),
                None
            ) or self.folder.create_child_folder('Accepted')
            self.rejected = next(
                filter(
                    lambda x: x.name == 'Rejected',
                    folders
                ),
                None
            ) or self.folder.create_child_folder('Rejected')


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
        assigned_file = None
        if self.assigned_domain and (assigned_file := self.assigned_domain.folder.get_item(self.assignment)):
            for status in ['Completed', 'Re-work Completed', 'Accepted', 'Rejected']:
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
        return bool(self.assignment in ['', 'N/A'])

    @property
    def re_work_completed(self):
        return bool(self.status == 'Re-work Completed')

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
        return self.completed or self.re_work_completed or self.unassigned or self.accepted or self.rejected

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

    def re_work_complete(self, dry_run: bool = False):
        if self.finished_manually:
            logger.info(f"{self.assignment} already moved to 'Re-work Completed' folder by resource.")
            if self.assignment_status == 'In Progress':
                logger.warning(f"Duplicate file {self.assignment} present in domain folder and 'Re-work Completed' folder.")
                self.assignment = ''
                return
        if (completed_file := self.assigned_domain.folder.get_item(self.assignment)):
            logger.info(f"Moving completed file {self.assignment} to 'Re-work Completed' folder.")
            if not dry_run:
                completed_file.move(self.assigned_domain.re_work_completed)
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

    def reject(self, rejected_resource: Resource, dry_run: bool = False, return_file: bool = True):
        if self.finished_manually:
            logger.info(f"{self.assignment} already moved to 'Rejected' folder by resource.")
            if self.assignment_status == 'In Progress':
                logger.warning(f"Duplicate file {self.assignment} present in domain folder and 'Rejected' folder.")
                self.assignment = ''
                return
        if (rejected_file := self.assigned_domain.folder.get_item(self.assignment)):
            logger.info(f"Moving rejected file {self.assignment} to 'Rejected' folder.")
            if not dry_run:
                logger.info(
                    f"Reassigning rejected file {rejected_file} to {rejected_resource.name} [{rejected_resource.code}]."
                )
                rejected_file.move(self.assigned_domain.rejected)
                if return_file:
                    self.return_file(rejected_file.name, rejected_resource)
        self.assignment = ''

    def return_file(self, filename: str, rejected_resource: Resource):
        domain = 'Media_Cable' if filename.split('_')[3] == 'MC' else 'Finance'
        rejected_info = re.search(r'(?P<rej_domain>MC|Fi)(_|-|\s)(?P<rej_number>[\d]{2,3})', filename)
        if not rejected_info:
            return
        rej_domain = rejected_info.groupdict().get('rej_domain')
        rej_number = rejected_info.groupdict().get('rej_number')
        for item in self.assigned_domain.rejected.get_items():
            if rej_domain in item.name and rej_number in item.name:
                logger.info(f"Copying {item.name} to folder of resource: {rejected_resource.name}.")
                item.copy(rejected_resource.get_domain(domain).folder)

    def return_all_files(self, resource_list: ResourceList, file_list: FileList):
        for domain in self.finance, self.media_cable:
            if domain.rejected:
                for item in domain.rejected.get_items():
                    if re.match(r'^(EN|ES)_(T[A-z])_(Ints|Utts)_(MC|Fi)_([\d]{3}).xlsx$', item.name):
                        rejected_task_file = file_list.get_single_task_file(self.assignment, role='Creator')
                        rejected_resource = resource_list.get_single_resource(rejected_task_file.assignment,
                                                                              role='Creator')
                        self.return_file(item.name, rejected_resource)

    def process(
            self,
            task_file: TaskFile,
            file_list: FileList,
            resource_list: ResourceList = None,
            dry_run: bool = False,
            return_file: bool = True
    ):
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
        if self.re_work_completed:
            logger.debug(f"Re-work Completing {self.assignment} for {self.name} [{self.code}].")
            self.re_work_complete(dry_run=dry_run)
            task_file.record(status='Re-work Completed')
        logger.debug(f"Process after completed: {self.status=}")
        if self.accepted:
            logger.debug(f"Processing {self.assignment} as 'Accepted' by {self.name} [{self.code}].")
            self.accept(dry_run=dry_run)
            task_file.record(status='Accepted')
        logger.debug(f"Process after accepted: {self.status=}")
        if self.rejected:
            logger.debug(f"Processing {self.assignment} as 'Rejected' by {self.name} [{self.code}].")
            rejected_task_file = file_list.reject_task_file(self.assignment, role='Creator')
            rejected_resource = resource_list.reject_task_file(rejected_task_file, role='Creator')
            self.reject(rejected_resource, dry_run=dry_run, return_file=return_file)
            task_file.record(status='Rejected')
        logger.debug(f"Process after rejected: {self.status=}")
        if self.needs_assignment:
            logger.debug(f"Assigning {task_file} to {self.name} [{self.code}].")
            self.assign(task_file, dry_run=dry_run)
            logger.debug(f"Process after needs_assignment: {self.status=}")
            return
        if self.status in ['In Progress'] and self.assignment_status != 'In Progress':
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
                domain_key
            )
            for filename, assignment in zip(
            self.filenames,
            self.df.drop(columns=['Domain']).values.tolist()
        )
            if (domain_key := self.get_domain(filename=filename))
        )
        self.processed = []

    def get_single_task_file(self, filename: str, role: str):
        domain_key = self.get_domain(filename=filename)
        task = 'Intent' if filename.split('_')[2][0] == 'I' else 'Utterance'
        ws = domain_key.wb.get_worksheet(f"{task}{role}Files")
        row = int(filename.split('_')[-1]) + 1
        _range = ws.get_range(f"B{row}:C{row}")
        return TaskFile(
            filename,
            *_range.values[0],
            domain_key
        )

    def update_single_task(self, task_file: TaskFile, role: str):
        domain_key = self.get_domain(task_file.domain)
        task = 'Intent' if task_file.name.split('_')[2][0] == 'I' else 'Utterance'
        ws = domain_key.wb.get_worksheet(f"{task}{role}Files")
        row = int(task_file.name.split('_')[-1]) + 1
        _range = ws.get_range(f"B{row}:C{row}")
        _range.update(
            values=[
                [*task_file]
            ]
        )

    def reject_task_file(self, filename: str, resource: Resource):
        rejected_task_file = self.get_single_task_file(filename, resource.role)
        rejected_task_file.update(status='Re-work In Progress', assignment=resource.name)
        self.update_single_task(rejected_task_file, resource.role)
        return rejected_task_file

    def get_domain(self, filename: str = None, domain: str = None):
        if filename:
            return self.media_cable if filename.split('_')[3] == 'MC' else self.finance
        if domain:
            return self.media_cable if domain == 'Media_Cable' else self.finance

    def __iter__(self):
        yield from self.task_files

    def update(self, dry_run: bool = False):
        if self.processed:
            self.processed.sort(key=lambda x: x.name)
            for domain in ['Finance', 'Media_Cable']:
                domain_key = self.get_domain(domain=domain)
                updates = [
                    task_file
                    for task_file in self.processed
                    if task_file.domain == domain
                ]
                values = [
                    [*task_file]
                    for task_file in updates
                ]
                address = f"B2:{'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[len(values[0])]}{len(values) + 1}"
                logger.debug(f"{domain} update address: {domain_key.task}{domain_key.role}!{address}.")
                _range = domain_key.ws.get_range(address)
                for task_file, (old_status, old_assignment) in zip(
                        updates, _range.values
                ):
                    update = (f"{old_assignment} [{old_status}]", f"{task_file.assignment} [{task_file.status}]")
                    if update[0] == update[1]:
                        logger.debug(f"{task_file.name}: {update[0]} -> {update[1]}")
                    else:
                        logger.info(f"{task_file.name}: {update[0]} -> {update[1]}")
                if not dry_run:
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
        self.resource_codes = self.df.index.tolist()
        self.frange = None
        self.format = None
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

    def get_worksheet(self, role: str):
        path = [*self.path[:-1], role]
        file = self.drive.get_item_by_path(*path, f"{self.lang}_LargeBot_{role}_Resources_List.xlsx")
        wb = WorkBook(file)
        return wb.get_worksheet(self.lang)

    def get_single_resource(self, resource_name: str, role: str):
        path = [*self.path[:-1], role]
        df = get_df(self.get_worksheet(role))
        code = self.get_code_by_name(resource_name, df)
        folder = self.drive.get_item_by_path(*path, code)
        return Resource(code, resource_name, df.loc[code]['Assignment'], df.loc[code]['Status'], folder)

    def update_single_resource(self, resource: Resource):
        ws = self.get_worksheet(resource.role)
        row = int(resource.code.split('_')[-1]) + 1
        _range = ws.get_range(f"B{row}:D{row}")
        _range.update(
            values=[
                [*resource]
            ]
        )

    def reject_task_file(self, task_file: TaskFile, role: str):
        rejected_resource = self.get_single_resource(task_file.name, role)
        rejected_resource.update(
            assignment=task_file.name,
            status='Re-work In Progress'
        )
        self.update_single_resource(rejected_resource)
        return rejected_resource

    def __iter__(self):
        yield from self.resources

    def __len__(self):
        return len(self.resource_codes)

    def __enter__(self):
        self.block()
        return self

    def __exit__(self, type, value, traceback):
        self.unblock()

    def block(self):
        self.frange = self.ws.get_range(f"A2:E{len(self.df) + 1}")
        self.format = self.frange.get_format()
        self.format.background_color = '#ffd8cc'
        self.format.update()
        self.ws.protect()

    def unblock(self):
        self.ws.unprotect()
        self.format.background_color = None
        self.format.update()

    def update(self, file_list: FileList = None, dry_run: bool = False):
        self.unblock()
        if self.processed:
            self.processed.sort(key=lambda x: x.code)
            values = [
                [*resource]
                for resource in self.processed
            ]
            address = f"B2:{'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[len(values[0])]}{len(values) + 1}"
            logger.info(f"Resource update address: {address}.")
            _range = self.ws.get_range(address)
            for resource, (_, old_assignment, old_status) in zip(
                    self.processed, _range.values
            ):
                update = (f"{old_assignment} [{old_status}]", f"{resource.assignment} [{resource.status}]")
                if update[0] == update[1]:
                    logger.debug(f"{resource.name}: {update[0]} -> {update[1]}")
                else:
                    logger.info(f"{resource.name}: {update[0]} -> {update[1]}")
            if not dry_run:
                _range.update(values=values)
                if self.role == 'Creator' and file_list is not None:
                    self.release_qc_files(file_list=file_list)

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

    def get_status_audit(self, domains: list = None, file_list: FileList = None):
        domains = domains or ['Finance', 'Media_Cable']
        summary = {
            domain: {
                'Intent': {},
                'Utterance': {}
            }
            for domain in domains
        }
        if not file_list:
            for domain in domains:
                dom = 'Fi' if domain == 'Finance' else 'MC'
                for task in summary[domain]:
                    for i in range(1, 101):
                        summary[domain][task][f"EN_Tr_{task[0:3]}s_{dom}_{i:03d}"] = ('Not Started', 'Unassigned')
        if file_list:
            for domain in domains:
                domain_key = file_list.get_domain(domain=domain)
                status, assignment, _ = list(domain_key.df.columns)
                for row in domain_key.df.itertuples(name='row'):
                    item_task = 'Intent' if str(row.Index).split('_')[2][0] == 'I' else 'Utterance'
                    summary[domain][item_task][str(row.Index)] = (getattr(row, status), getattr(row, assignment))
        for resource in self.resources:
            for domain in domains:
                for task in summary[domain]:
                    domain_folder = resource.get_domain(domain).folder
                    for item in domain_folder.get_items():
                        if item.is_file and (filename := item.name.split('.')[0]) and filename in summary[domain][task]:
                            summary[domain][task][filename] = ('In Progress', resource.name)
                    for folder in domain_folder.get_child_folders():
                        for item in folder.get_items():
                            if item.is_file and (filename := item.name.split('.')[0]) and filename in summary[domain][task]:
                                summary[domain][task][filename] = (folder.name, resource.name)
        return summary


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

    with ResourceList(
            drive=PROJ_DRIVE,
            lang=LANG,
            phase=PHASE,
            role=ROLE
    ) as RESOURCE_LIST:
        if all(
                status in ['Not Started', 'In Progress']
                for status in RESOURCE_LIST.df['Status'].tolist()
        ):
            logger.info('All resources currently have an active assignment.')
            return

        for task_file in FILE_LIST:
            logger.debug(f"Processing {task_file}.")
            FILE_LIST.processed.append(task_file)
            if not task_file.needs_assignment:
                logger.debug(f"No action needed for {task_file}.")
                continue
            for resource in RESOURCE_LIST.resources:
                logger.info(f"Processing {resource} and {task_file}.")
                task_file = resource.process(task_file, FILE_LIST, RESOURCE_LIST, dry_run=dry_run)
                RESOURCE_LIST.processed.append(resource)
                if not task_file:
                    break
            # else:
            #     logger.info('All resources have been processed. Exiting loop.')
            #     break

        FILE_LIST.update(
            dry_run=dry_run
        )
        RESOURCE_LIST.update(
            file_list=FILE_LIST,
            dry_run=dry_run
        )


def assign_qcs(
        LANG: str = 'EN-US',
        PHASE: str = '_Training',
        TASK: str = 'Intent',
        check_assignments: bool = False,
        dry_run: bool = False,
        return_all: bool = False
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

    with ResourceList(
            drive=PROJ_DRIVE,
            lang=LANG,
            phase=PHASE,
            role=ROLE
    ) as RESOURCE_LIST:
        if all(
                status in ['Not Started', 'In Progress']
                for status in RESOURCE_LIST.df['Status'].tolist()
        ):
            logger.info('All resources currently have an active assignment.')
            return

        for task_file in FILE_LIST:
            logger.info(f"Processing {task_file} [{task_file.domain}].")
            FILE_LIST.processed.append(task_file)
            if not task_file.needs_assignment:
                logger.info(f"No action needed for {task_file}.")
                continue
            for resource in RESOURCE_LIST.resources:
                logger.info(f"Processing {resource} and {task_file}.")
                RESOURCE_LIST.processed.append(resource)
                if return_all:
                    logger.info('Returning all rejected files.')
                    resource.return_all_files(RESOURCE_LIST, FILE_LIST)
                task_file = resource.process(task_file, FILE_LIST, RESOURCE_LIST, dry_run=dry_run)
                if not task_file:
                    break
            '''
            else:
                logger.info('All resources have been processed. Exiting loop.')
                break
            '''

        FILE_LIST.update(
            dry_run=dry_run
        )
        RESOURCE_LIST.update(
            dry_run=dry_run
        )
