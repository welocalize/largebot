import sys
import logging
import re

from pathlib import Path

from largebot.logger import get_logger
from O365.excel import WorkBook, WorkSheet, Range
from O365.drive import Folder
from welo365.account import O365Account


logger = get_logger(__name__)

creds = ('37aba2ba-24ac-4a9b-9553-15967ff85768', 'IO53Ev.b0T.D9_t00Hd7tsijl.GR7-u-3_')
scopes = ['offline_access', 'Sites.Manage.All']
account = O365Account(creds, scopes, scrape=False)

TEAM = 'msteams_08dd34-AmazonLex-LargeBot'
LANG = 'EN-US'
DOMAIN = 'Finance'
TASK = 'Intent'
PROD_PHASE = '_Training'
PROD_PATH = '/'.join([
    'Amazon Lex - LargeBot',
    'Data Creation',
    LANG
    ])
PROD_SITE = f"/sites/{TEAM}"
PROD_FOLDER = account.get_folder_from_path(PROD_PATH, PROD_SITE)
INTERNAL_SITE = '/sites/AIEnablementPractice'
INTERNAL_PATH = '/'.join([
    'Amazon Web Services, Inc',
    'Bot Training & Testing Data (LargeBot)',
    'Production Planning',
    'Files for Processing'
])
KEY_PATH = f"{INTERNAL_PATH}/Intent_Intent IDs Keys"
FILE_PATH = f"{INTERNAL_PATH}/Processed Files/{LANG}/{PROD_PHASE}/{DOMAIN}/{TASK}s"
KEY_FOLDER = account.get_folder_from_path(KEY_PATH, INTERNAL_SITE)
FILE_FOLDER = account.get_folder_from_path(FILE_PATH, INTERNAL_SITE)
RESOURCE_PATH = f"{PROD_PATH}/{PROD_PHASE}/Creator"
RESOURCE_FOLDER = account.get_folder_from_path(RESOURCE_PATH, PROD_SITE)


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
    def __init__(self, name: str, _range: Range):
        self.name = name
        self.file = FILE_FOLDER.get_item(name)
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
    def __init__(self, code: str, _range: Range):
        self.code = code
        self.assignment = ResourceAssignment(_range)
        self.folder: Folder = RESOURCE_FOLDER.get_item(code).get_item(DOMAIN)
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
        completed_file = self.folder.get_item(self.filename)
        logger.info(f"Moving completed file {self.filename} to 'Completed' folder.")
        completed_file.move(self.completed_folder)


class FileList:
    def __init__(self, task: str = TASK, sheet_name: str = 'Files'):
        self.name = f"{DOMAIN}_Intent Key.xlsx"
        self.file = KEY_FOLDER.get_item(self.name)
        self.wb = WorkBook(self.file, use_session=False, persist=False)
        self.ws = self.wb.get_worksheet(sheet_name)
        self.task_files = (
            TaskFile(fname, self.ws.get_range(fname))
            for value in self.ws.get_range(f"{task}FileName").values
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
        task_file = TaskFile(resource.filename, self.ws.get_range(resource.filename))
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
    def __init__(self, lang: str = LANG, sheet_name: str = LANG):
        self.name = f"{lang}_LargeBot Resources List.xlsx"
        self.file = PROD_FOLDER.get_item(self.name)
        self.wb = WorkBook(self.file, use_session=False, persist=False)
        self.ws = self.wb.get_worksheet(sheet_name)
        self.resource_codes = [
            resource_code
            for value in self.ws.get_range('ResourceCodes').values
            if (resource_code := value[0])
        ]
        self.resources = (
            Resource(resource_code, self.ws.get_range(resource_code))
            for resource_code in self.resource_codes
        )

    def __iter__(self):
        yield from self.resources

    def __next__(self):
        try:
            return next(iter(self))
        except StopIteration:
            return None





def main():
    FILE_LIST = FileList()
    RESOURCE_LIST = ResourceList()
    for resource in RESOURCE_LIST.resources:
        logger.info(f"Checking resource: {resource}")
        if resource.unassigned:
            logger.info(f"Resource {resource.code} has no current file assignment.")
            if (task_file := next(FILE_LIST)):
                resource.assign(task_file)
        if resource.completed:
            FILE_LIST.complete(resource)
            if (task_file := next(FILE_LIST)):
                resource.assign(task_file)

# resource_codes = [
#     value[0]
#     for value in resource_list.get_range('Resource_Code').values
# ]
#
# filenames = [
#    value[0]
#     for value in file_list.get_range(f"{TASK}FileName").values
# ]
#
# unassigned_files = []
# completed_files = []
#
# for filename in filenames:
#     filestatus = file_list.get_range(filename).values[0][0]
#     if filestatus == 'Not Started':
#         unassigned_files.append(filename)
#
# def main():
#     for resource_code in resource_codes:
#         resource_range = resource_list.get_range(resource_code)
#         resource_name, filename, filestatus, notes = resource_range.values[0]
#         if resource_name != '':
#             if filename == '':
#                 filename = unassigned_files[0]
#                 unassigned_files = unassigned_files[1:]
#             if filename != '' and filestatus == 'Completed':
#                 completed_files.append(filename)
#                 filename = unassigned_files[0]
#                 filestatus = 'Not Started'
#                 unassigned_files = unassigned_files[1:]
#         resource_range.values = [[resource_name, filename, filestatus, notes]]
#         resource_range.update()