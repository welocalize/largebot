from __future__ import annotations

import re

from O365.excel import Range as _Range
from O365.excel import WorkBook as _WorkBook
from O365.excel import WorkSheet as _WorkSheet


class Range(_Range):
    pattern = r'^.*!(?P<left>[A-Z]+)(?P<top>[0-9]+)(:(?P<right>[A-Z]+)(?P<bottom>[0-9]+))?$'

    def __init__(self, parent=None, session=None, **kwargs):
        super().__init__(parent=parent, session=session, **kwargs)
        self.matchgroup = re.search(self.pattern, self.address).groupdict()

    def update(self, values: list):
        self.values = values
        super().update()

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


class WorkSheet(_WorkSheet):
    range_constructor = Range

    def protect(self):
        payload = {
            'options': {
                'allowFormatCells': False,
                'allowFormatColumns': False,
                'allowFormatRows': False,
                'allowInsertColumns': False,
                'allowInsertRows': False,
                'allowInsertHyperlinks': False,
                'allowDeleteColumns': False,
                'allowDeleteRows': False,
                'allowSort': True,
                'allowAutoFilter': True,
                'allowPivotTables': True
            }
        }
        url = self.build_url('/protection/protect')
        return bool(self.session.post(url, json=payload))

    def unprotect(self):
        url = self.build_url('/protection/unprotect')
        return bool(self.session.post(url))


class WorkBook(_WorkBook):
    worksheet_constructor = WorkSheet

    def __init__(self, file_item, *, use_session=False, persist=False):
        super().__init__(file_item, use_session=use_session, persist=persist)
