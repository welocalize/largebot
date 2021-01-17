from __future__ import annotations

from faker import Faker, Factory
from faker.providers import BaseProvider
import pandas as pd
from pathlib import Path
from functools import partial

MASTER = Path.cwd() / 'master.csv'


class PhraseList:
    def __init__(self):
        df = pd.read_csv(MASTER)
        names = df.columns.tolist()
        for name in names:
            self.__setattr__(name, partial(self.phrase, phrases=df[name].tolist()))

    def phrase(self, phrases):
        return self.random_element(phrases)


class Provider(PhraseList, BaseProvider):
    pass



