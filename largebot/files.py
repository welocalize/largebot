from __future__ import annotations

import sys
import logging
import re

from pathlib import Path

from largebot.logger import get_logger
from O365.excel import WorkBook, WorkSheet, Range
from O365.drive import Folder
from welo365.account import O365Account

logger = get_logger(__name__)

class Config:
    def __init__(self, LANG: str, DOMAIN: str, TASK: str, PROJ_PHASE: str):
        self.AIE_SITE = 'AIEnablementPractice'
        self.PROJ_SITE = 'msteams_08dd34-AmazonLex-LargeBot'
        self.ACCOUNT = O365Account(site=self.AIE_SITE)

        self.LANG = LANG
        self.DOMAIN = DOMAIN
        self.TASK = TASK
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
            'Creator'
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


class TaskFile(Ranger):
    def __init__(self, name: str, _range: Range, CONFIG: Config):
        self.name = name
        self.file = CONFIG.FILE_FOLDER.get_item(name)
        super().__init__(_range)

    def __repr__(self):
        return f"TaskFile: {self.name} [{self.status}]"

    @property
    def status(self):
        return self.values[0][0]

    def update(self, status: str):
        self.range.values = [[status]]
        self.range.update()

    @property
    def unassigned(self):
        return bool(self.status == 'Not Started')

    def copy(self, target: Folder):
        return self.file.copy(target)

    def move(self, target: Folder):
        return self.file.move(target)

    def assign(self, folder: Folder = None):
        logger.info(f"Marking task {self.name} 'In Progress' in Intent IDs tracker.")
        self.update(status='In Progress')
        if folder:
            logger.info(f"Copying source file from internal AIE directory to resource production folder.")
            self.copy(folder)

    def complete(self):
        logger.info(f"Marking task {self.name} 'Completed' in Intent IDs tracker.")
        self.update(status='Completed')


class ResourceAssignment(Ranger):
    def __init__(self, _range: Range):
        super().__init__(_range)

    @property
    def value(self):
        return self.values[0]

    @property
    def name(self):
        return self.value[0]

    @property
    def filename(self):
        return self.value[1]

    @property
    def status(self):
        return self.value[2]

    def update(self, name: str = None, filename: str = None, status: str = None):
        name = name or self.name
        filename = filename or self.filename
        status = status or self.status
        self.range.values = [[name, filename, status]]
        self.range.update()


class Resource:
    def __init__(self, code: str, _range: Range, CONFIG: Config):
        self.code = code
        self.assignment = ResourceAssignment(_range)
        self.folder: Folder = CONFIG.RESOURCE_FOLDER.get_item(code).get_item(CONFIG.DOMAIN)
        self.completed_folder = self.folder.get_item('Completed')
        if self.completed_folder is None:
            logger.info(f"No 'Completed' folder in resource folder. Creating one.")
            self.completed_folder = self.folder.create_child_folder('Completed')

    def __repr__(self):
        return f"{self.name} [{self.code}] - TaskFileAssignment: {self.filename} - TaskStatus: {self.status}"

    @property
    def name(self):
        return self.assignment.name

    @property
    def filename(self):
        return self.assignment.filename

    @property
    def status(self):
        return self.assignment.status

    def update(self, name: str = None, filename: str = None, status: str = None):
        self.assignment.update(name=name, filename=filename, status=status)

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
        self.assignment.update(filename=task_file.name, status='Not Started')
        task_file.assign(self.folder)

    def complete(self):
        already_completed_file = None
        if (alread_completed_file := self.completed_folder.get_item(self.filename)):
            logger.info(f"{self.filename} already moved to 'Completed' folder by resource.")
        if (completed_file := self.folder.get_item(self.filename)):
            if alread_completed_file is not None:
                logger.info(f"Removing duplicate file {self.filename} from resource folder.")
                completed_file.delete()
                return
            logger.info(f"Moving completed file {self.filename} to 'Completed' folder.")
            completed_file.move(self.completed_folder)


class FileList:
    SHEET_NAME = 'Files'
    def __init__(self, CONFIG: Config):
        self.CONFIG = CONFIG
        self.name = f"{CONFIG.DOMAIN}_Intent Key.xlsx"
        self.file = CONFIG.KEY_FOLDER.get_item(self.name)
        self.wb = WorkBook(self.file, use_session=False, persist=False)
        self.ws = self.wb.get_worksheet(self.SHEET_NAME)
        self.task_files = (
            TaskFile(fname, self.ws.get_range(fname), CONFIG)
            for value in self.ws.get_range(f"{CONFIG.TASK}FileName").values
            if (fname := value[0])
        )

    @property
    def unassigned_files(self):
        yield from (
            task_file
            for task_file in self.task_files
            if task_file.unassigned
        )

    def complete(self, resource: Resource):
        task_file = TaskFile(resource.filename, self.ws.get_range(resource.filename), self.CONFIG)
        logger.info(f"{task_file} completed by Resource {resource.code}.")
        task_file.complete()
        resource.complete()

    def __iter__(self):
        return self.unassigned_files

    def __next__(self):
        try:
            return next(iter(self))
        except StopIteration:
            return None


class ResourceList:
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
        self.resources = (
            Resource(resource_code, self.ws.get_range(resource_code), CONFIG)
            for resource_code in self.resource_codes
        )

    def __iter__(self):
        yield from self.resources

    def __next__(self):
        try:
            return next(iter(self))
        except StopIteration:
            return None





def automate(LANG: str, DOMAIN: str, TASK: str, PROJ_PHASE: str):
    CONFIG = Config(LANG, DOMAIN, TASK, PROJ_PHASE)

    FILE_LIST = FileList(CONFIG)
    RESOURCE_LIST = ResourceList(CONFIG)
    for resource in RESOURCE_LIST.resources:
        logger.info(f"Checking resource: {resource}")
        if resource.unassigned:
            logger.info(f"Resource {resource.code} has no current file assignment.")
            if (task_file := next(FILE_LIST)):
                resource.assign(task_file)
        if resource.completed:
            FILE_LIST.complete(resource)
            if (task_file := next(FILE_LIST)):
                logger.info(f"Assigning new task {task_file.name} to Resource {resource.code}.")
                resource.assign(task_file)
