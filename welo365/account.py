from __future__ import annotations

import logging
import os
import sys

from O365 import Account, FileSystemTokenBackend
from O365.connection import MSGraphProtocol
from pathlib import Path

from welo365.sharepoint import Sharepoint

logfile = Path.cwd() / 'output.log'
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
date_format = "%H:%M:%S"
formatter = logging.Formatter(log_format, date_format)
ch = logging.StreamHandler(sys.stderr)
ch.setFormatter(formatter)
ch.setLevel(logging.INFO)
logger.addHandler(ch)
fh = logging.FileHandler(logfile)
fh.setFormatter(formatter)
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)

DOMAIN = 'welocalize.sharepoint.com'
CREDS = (os.environ.get('welo365_client_id'), os.environ.get('welo365_client_secret'))


class O365Account(Account):
    def __init__(
            self,
            site: str = None,
            creds: tuple[str, str] = CREDS,
            scopes: list[str] = None,
            auth_flow_type: str = 'authorization'
    ):
        WORKDIR = Path.cwd()
        token_backend = None
        for token_path in [WORKDIR, *WORKDIR.parents]:
            TOKEN = token_path / 'o365_token.txt'
            if TOKEN.exists():
                logger.info(f"Using token file {TOKEN}")
                token_backend = FileSystemTokenBackend(token_path=token_path)
                token_backend.load_token()
                token_backend.get_token()
                break
        scopes = scopes or ['offline_access', 'Sites.Manage.All']
        OPTIONS = {
            'token_backend': token_backend
        } if token_backend is not None else {
            'scopes': scopes,
            'auth_flow_type': auth_flow_type
        }
        super().__init__(creds, **OPTIONS)
        # if scrape:
        #     self.scrape(scopes)
        if not self.is_authenticated:
            self.authenticate()
        self.drives = self.storage().get_drives()
        self.site = self.get_site(site) if site else None
        self.drive = self.site.get_default_document_library() if self.site else self.storage().get_default_drive()
        self.root_folder = self.drive.get_root_folder()

    def sharepoint(self, *, resource=''):
        if not isinstance(self.protocol, MSGraphProtocol):
            raise RuntimeError(
                'Sharepoint api only works on Microsoft Graph API'
            )
        return Sharepoint(parent=self, main_resource=resource)

    def get_site(self, site: str):
        return self.sharepoint().get_site(DOMAIN, f"/sites/{site}")

    def get_folder(self, *subfolders: str, site: str = None):
        if len(subfolders) == 0:
            return self.drive

        site = self.get_site(site) if site else self.site
        drive = site.get_default_document_library() if site else self.drive

        items = drive.get_items()
        for subfolder in subfolders:
            try:
                subfolder_drive = list(filter(lambda x: subfolder in x.name, items))[0]
                items = subfolder_drive.get_items()
            except:
                raise ('Path {} not exist.'.format('/'.join(subfolders)))
        return subfolder_drive
