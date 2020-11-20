from __future__ import annotations

import sys
import logging
import re

from itertools import chain
from pathlib import Path

from largebot.logger import get_logger
from O365.excel import WorkBook, WorkSheet, Range
from O365.drive import Folder
from welo365.account import O365Account

logger = get_logger(__name__)


class Config:
    def __init__(self, LANG: str, DOMAIN: str, TASK: str, STEP: str, PROJ_PHASE: str):
        self.AIE_SITE = 'AIEnablementPractice'
        self.PROJ_SITE = 'msteams_08dd34-AmazonLex-LargeBot'
        self.ACCOUNT = O365Account(site=self.AIE_SITE)

        self.LANG = LANG
        self.DOMAIN = DOMAIN
        self.TASK = TASK
        self.STEP = STEP
        self.PROJ_PHASE = PROJ_PHASE
        self.PROJ_PATH = [
            'Amazon Lex - LargeBot',
            'Data Creation',
            self.LANG
            ]
        self.PROJ_FOLDER = self.ACCOUNT.get_folder(*self.PROJ_PATH, site=self.PROJ_SITE)
        self.AIE_PATH = [
            'Amazon Web Services, Inc',
            'Bot Training & Testing Data (LargeBot)',
            'Production Planning',
            'Files for Processing'
        ]
        self.KEY_PATH = 'Intent_Intent IDs Keys'
        self.FILE_PATH = [
            'Processed Files',
            self.LANG,
            self.PROJ_PHASE,
            self.DOMAIN,
            f"{self.TASK}s"
        ]
        self.KEY_FOLDER = self.ACCOUNT.get_folder(*self.AIE_PATH, self.KEY_PATH)
        self.FILE_FOLDER = self.ACCOUNT.get_folder(*self.AIE_PATH, *self.FILE_PATH)
        self.RESOURCE_PATH = [
            *self.PROJ_PATH,
            self.PROJ_PHASE,
            self.STEP
        ]
        self.RESOURCE_FOLDER = self.ACCOUNT.get_folder(*self.RESOURCE_PATH, site=self.PROJ_SITE)


class Ranger:
    pattern = r'^.*!(?P<left>[A-Z]+)(?P<top>[0-9]+)(:(?P<right>[A-Z]+)(?P<bottom>[0-9]+))?$'
    def __init__(self, _range: Range):
        self.range = _range
        self.matchgroup = re.search(self.pattern, self.range.address).groupdict()

    @property
    def address(self):
        return self.range.address

    @property
    def values(self):
        return self.range.values

    def update(self, values: list[list]):
        self.range.values = values
        self.range.update()

    @property
    def left(self):
        return self.matchgroup.get('left')

    @property
    def right(self):
        return self.matchgroup.get('right')

    @property
    def top(self):
        return self.matchgroup.get('top')

    @property
    def bottom(self):
        return self.matchgroup.get('bottom')


class FileStatus(Ranger):
    @property
    def value(self):
        return self.values[0][0]

    def update(self, status: str):
        self.range.values = [[status]]
        self.range.update()


class TaskFile:
    def __init__(self, name: str, status: str, assignment: str, CONFIG: Config):
        self.name = name
        self.file = CONFIG.FILE_FOLDER.get_item(name)
        self.domain = CONFIG.DOMAIN
        self.step = CONFIG.STEP
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
        return bool(self.status == 'Not Started')

    def copy(self, target: Folder):
        return self.file.copy(target)

    def move(self, target: Folder):
        return self.file.move(target)

    def assign(self, resource: Resource):
        logger.info(f"Marking task {self.name} 'In Progress' and assigning to {resource.name} in Intent IDs tracker.")
        self.update(status='In Progress', assignment=resource.name)
        folder = resource.get_domain(self.domain).folder
        logger.info(f"Copying source file from internal AIE directory to resource production folder.")
        self.copy(folder)

    def complete(self):
        logger.info(f"Marking task {self.name} 'Completed' in Intent IDs tracker.")
        self.update(status='Completed')


# class ResourceAssignment:
#     def __init__(self, name: str, filename: str, status: str):
#         self._name = name
#         self._filename = filename
#         self._status = status
#
#     @property
#     def name(self):
#         return self._name
#
#     @name.setter
#     def name(self, name: str):
#         self._name = name
#
#     @property
#     def filename(self):
#         return self._filename
#
#     @filename.setter
#     def filename(self, filename:str):
#         self._filename = filename
#
#     @property
#     def status(self):
#         return self._status
#
#     @status.setter
#     def status(self, status: str):
#         self._status = status
#
#     def update(self, name: str = None, filename: str = None, status: str = None):
#         self.name = name or self._name
#         self.filename = filename or self._filename
#         self.status = status or self._status


class DomainFolder:
    def __init__(self, resource_folder: Folder, domain: str):
        self.folder = resource_folder.get_item(domain)
        self.parent = resource_folder
        self.completed = self.folder.get_item('Completed')
        if self.completed is None:
            logger.info(f"No 'Completed' folder in resource folder. Creating one.")
            self.completed = self.folder.create_child_folder('Completed')


class Resource:
    def __init__(self, code: str, name: str, filename: str, status: str, CONFIG: Config):
        self.code = code
        self.task = CONFIG.TASK
        self.folder = CONFIG.RESOURCE_FOLDER.get_item(code)
        self.finance = DomainFolder(self.folder, 'Finance')
        self.media_cable = DomainFolder(self.folder, 'Media_Cable')
        self.name = name
        self._filename = filename
        self._status = status

    def __repr__(self):
        return f"{self.name} [{self.code}] - {self.task}FileAssignment: {self._filename} - TaskStatus: {self._status}"

    def __iter__(self):
        return iter((self.name, self._filename, self._status))

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, filename: str):
        self._filename = filename

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status: str):
        self._status = status

    def update(self, filename: str = None, status: str = None):
        self.filename = filename or self._filename
        self.status = status or self._status

    def get_domain(self, domain: str):
        return getattr(self, domain.lower())

    @property
    def assigned(self):
        return bool(self.filename)

    @property
    def unassigned(self):
        return not self.assigned

    @property
    def completed(self):
        return bool(self.status == 'Completed')

    def assign(self, task_file: TaskFile):
        logger.info(f"TaskFile {task_file.name} assigned to {self.code} and marked as such in Resource List.")
        self.update(filename=task_file.name, status='Not Started')
        task_file.assign(self)

    def complete(self, task_file: TaskFile):
        domain_folder = self.get_domain(task_file.domain)
        already_completed_file = None
        if (alread_completed_file := domain_folder.completed.get_item(self.filename)):
            logger.info(f"{self.filename} already moved to 'Completed' folder by resource.")
        if (completed_file := domain_folder.folder.get_item(self.filename)):
            if alread_completed_file is not None:
                logger.info(f"Removing duplicate file {self.filename} from resource folder.")
                completed_file.delete()
                return
            logger.info(f"Moving completed file {self.filename} to 'Completed' folder.")
            completed_file.move(domain_folder.completed)


class FileList(Ranger):
    SHEET_NAME = 'Files'
    def __init__(self, CONFIG: Config):
        self.CONFIG = CONFIG
        self.name = f"{CONFIG.DOMAIN}_Intent Key.xlsx"
        self.file = CONFIG.KEY_FOLDER.get_item(self.name)
        self.wb = WorkBook(self.file, use_session=False, persist=False)
        self.ws = self.wb.get_worksheet(self.SHEET_NAME)
        super().__init__(self.ws.get_range(f"{CONFIG.TASK}{CONFIG.STEP}"))
        self.filenames = [
            filename
            for value in self.ws.get_range(f"{CONFIG.TASK}FileName").values
            if (filename := value[0])
        ]
        self.task_files = {
            filename: TaskFile(filename, *assignment, CONFIG)
            for filename, assignment in zip(self.filenames, self.values)
        }

    def get(self, filename: str):
        if 'xlsx' in filename:
            filename = filename.split('.')[0]
        return self.task_files.get(filename)

    # @property
    # def unassigned_files(self):
    #     return [
    #         task_file
    #         for filename in self.filenames
    #         if (
    #             (task_file := self.get(filename))
    #             and task_file.unassigned
    #         )
    #     ]

    def complete(self, resource: Resource):
        task_file = self.get(resource.filename)
        logger.info(f"{task_file} completed by Resource {resource.code}.")
        task_file.complete()
        resource.complete(task_file)

    def __iter__(self):
        return iter(task_file for task_file in self.task_files.values() if task_file.unassigned)

    def update(self):
        self.range.values = [
            [*task_file]
            for task_file in self.task_files.values()
        ]
        self.range.update()

class ResourceList(Ranger):
    def __init__(self, CONFIG: Config):
        self.CONFIG = CONFIG
        self.name = f"{CONFIG.LANG}_LargeBot Resources List.xlsx"
        self.file = CONFIG.PROJ_FOLDER.get_item(self.name)
        self.wb = WorkBook(self.file, use_session=False, persist=False)
        self.ws = self.wb.get_worksheet(CONFIG.LANG)
        self.resource_codes = [
            resource_code
            for value in self.ws.get_range('ResourceCodes').values
            if (resource_code := value[0])
        ]
        address = f"B2:D{len(self.resource_codes) + 1}"
        super().__init__(self.ws.get_range(address))
        self.resources = [
            Resource(resource_code, *assignment, CONFIG)
            for resource_code, assignment in zip(self.resource_codes, self.values)
        ]

    def __iter__(self):
        return iter(self.resources)

    def __len__(self):
        return len(self.resource_codes)

    def update(self):
        self.range.values = [
            [*resource]
            for resource in self.resources
        ]
        self.range.update()

def automate(
        LANG: str = 'EN-US',
        TASK: str = 'Intent',
        STEP: str = 'Creator',
        PROJ_PHASE: str = '_Training',
        check_assignments: bool = False
):
    MC_CONFIG = Config(LANG, 'Media_Cable', TASK, STEP, PROJ_PHASE)
    FI_CONFIG = Config(LANG, 'Finance', TASK, STEP, PROJ_PHASE)
    RESOURCE_LIST = ResourceList(MC_CONFIG)
    FI_FILE_LIST = FileList(FI_CONFIG)
    MC_FILE_LIST = FileList(MC_CONFIG)
    file_lists = {
        'MC': MC_FILE_LIST,
        'FI': FI_FILE_LIST
    }

    def get_file_list(*args):
        for gen in args:
            yield from gen


    FILE_LIST = [*MC_FILE_LIST, *FI_FILE_LIST]

    for resource in RESOURCE_LIST:
        logger.info(f"Checking resource: {resource}")
        if resource.unassigned:
            logger.info(f"Resource {resource.code} has no current file assignment.")
            task_file, *FILE_LIST = FILE_LIST
            resource.assign(task_file)
        if resource.completed:
            if (domain_list := file_lists.get(resource.filename.split('_')[3])):
                domain_list.complete(resource)
            task_file, *FILE_LIST = FILE_LIST
            logger.info(f"Assigning new task {task_file.name} to Resource {resource.code}.")
            resource.assign(task_file)

    RESOURCE_LIST.update()
    FI_FILE_LIST.update()
    MC_FILE_LIST.update()


    '''
    # if check_assignments:
    #     for domain, dom in [('Finance', 'FI'), ('Media_Cable', 'MC')]:
    #         if resource.status in ['In Progress', 'Not Started'] and resource.filename:
    #             if resource.filename.split('_')[3].lower() == dom.lower():
    #                 file = resource.get_domain(domain).folder.get_item(resource.filename)
    #                 if not file:
    #                     logger.info(f"Reassigning {resource.filename} to {resource.name}.")
    #                     file_list = file_lists.get(dom)
    #                     task_file = file_list.get(resource.filename)
    #                     task_file.assign(resource)
    #         domain_folder = resource.get_domain(domain).folder
    #         for item in domain_folder.get_items():
    #             file_list = file_lists.get(dom)
    #             if item.is_file:
    #                 task_file = file_list.get(item.name)
    #                 if not task_file.assignment:
    #                     logger.info(f"Adding missing assignment for {task_file.name} to tracker: {resource.name}.")
    #                     task_file.update(status='In Progress', assignment=resource.name)
    #                 if task_file.status != 'In Progress':
    #                     logger.info(f"Updating task status to 'In Progress' for {task_file.name} assigned to {resource.name}.")
    #                     task_file.update(status='In Progress')
    #                 if task_file.assignment != resource.name:
    #                     logger.error(f"Conflicting assignment information for {task_file.name} and {resource.name}.")
    #             if item.is_folder:
    #                 for completed_item in item.get_items():
    #                     if resource.filename in completed_item.name:
    #                         if (domain_list := file_lists.get(resource.filename.split('_')[3])):
    #                             domain_list.complete(resource)
    #                             if (task_file := next(FI_FILE_LIST)):
    #                                 logger.info(f"Assigning new task {task_file.name} to Resource {resource.code}.")
    #                                 resource.assign(task_file)
    #                     task_file = file_list.get(completed_item.name)
    #                     if task_file.assignment != resource.name:
    #                         logger.error(f"Incorrect or missing assignment for {task_file.name} for {resource.name}.")
    #                         task_file.update(assignment=resource.name)
    #                     if task_file.status != 'Completed':
    #                         logger.error(f"Incorrect file status for {task_file.name} for {resource.name}.")
    #                         task_file.update(status='Completed')
    logger.info(f"Checking resource: {resource}")
    if resource.unassigned:
        logger.info(f"Resource {resource.code} has no current file assignment.")
        if (task_file := next(FI_FILE_LIST)):
            resource.assign(task_file)
    if resource.completed:
        if (domain_list := file_lists.get(resource.filename.split('_')[3])):
            domain_list.complete(resource)
        if (task_file := next(FI_FILE_LIST)):
            logger.info(f"Assigning new task {task_file.name} to Resource {resource.code}.")
            resource.assign(task_file)

    # return RESOURCE_LIST, FI_FILE_LIST, MC_FILE_LIST
    '''

