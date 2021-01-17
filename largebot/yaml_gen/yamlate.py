from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import SingleQuotedScalarString
from ruamel.yaml.representer import RepresenterError
from slot_faker.providers import BaseProvider
from slot_faker import SlotFaker
from welo365 import O365Account
from pydantic import BaseModel, validator
from functools import partial
from typing import Callable, List, Union
from mypy_extensions import (Arg, DefaultArg, NamedArg, DefaultNamedArg, VarArg, KwArg)

import pandas as pd


account = O365Account()

link = 'https://welocalize.sharepoint.com/:x:/s/msteams_08dd34-AmazonLex-esUSLargeBot/EXV5W83kgmpBlcUBuUzDOHUB1O6CiaYNGgJGuunC5bAtzw?e=PaPqPa'
url = 'https://welocalize.sharepoint.com/:x:/r/sites/msteams_08dd34-AmazonLex-esUSLargeBot/_layouts/15/Doc.aspx?sourcedoc=%7BCD5B7975-82E4-416A-95C5-01B94CC33875%7D&file=utterances.xlsx&action=default&mobileredirect=true'
parent_id = '{CD5B7975-82E4-416A-95C5-01B94CC33875}'

item_id = 'EXV5W83kgmpBlcUBuUzDOHUB1O6CiaYNGgJGuunC5bAtzw'

BASE_FAKER = SlotFaker()


class Slot(BaseModel):
    name: str
    type: str
    prompt: str = ''
    required: bool = False
    method: Callable[..., str]

    class Config:
        arbitrary_types_allowed = True

    @validator('method', pre=True)
    def configure_method(cls, v):
        if isinstance(v, str) and
            if (method := getattr(BASE_FAKER, v, None)):
                if (parts := v.split(',')):
                    if len(parts) == 1:
                        return method
                    _, *args = parts
                    params = {
                        p[0]: p[1]
                        for arg in args
                        if (p := arg.split('='))
                    }
                    return partial(method, **params)
        if isinstance(v, (list, tuple)):
            return partial(BASE_FAKER.random_element, elements=v)
        return v

    def __call__(self):
        if callable(self.method):
            return self.method()

    def yaml(self):
        return {
            'name': self.name,
            'type': self.type,
            'prompt': self.prompt,
            'required': self.required
        }




class SlotProvider(BaseModel):
    def __init__(
            self,
            slot: Slot,
            value_method=None,
            value_list: list = None,
            opening_utterances: list = None,
            builtin: bool = False,
            **config
    ):
        generator = Generator()
        super().__init__(generator)
        self.slot = slot
        conversational_name = value_method or slot.type or slot.name
        self.conversational_name = get_conversational_name(conversational_name)
        self.utterances = utterance_list or ['{}']
        self.opening_utterances = opening_utterances or []
        self.values = []
        if utterance_method:
            self._utterance = utterance_method
        object.__setattr__(self, f"{slot.name}_utterance", self._utterance)
        object.__setattr__(self, f"{slot.name}_utterances", self._utterances)
        object.__setattr__(self, f"{slot.name}_opening_utterance", self._opening_utterance)
        object.__setattr__(self, f"{slot.name}_prompt", self.prompt)
        if value_method:
            object.__setattr__(self, f"{slot.name}_value", value_method)
        if value_list:
            self.values = tuple(value_list)
            object.__setattr__(self, f"{slot.name}_value", self.random_element(self.values))

    @property
    def name(self):
        return self.slot.name

    @property
    def type(self):
        return self.slot.type

    @property
    def prompt(self):
        return self.slot.prompt

    @property
    def required(self):
        return self.slot.required

    def _utterance(self):
        return self.random_element(self.utterances)

    def _opening_utterance(self):
        if self.opening_utterances:
            return self.random_element(self.opening_utterances)
        return f"my {self.conversational_name} is {{}}"

    def _utterances(self):
        return self.utterances

    def prompt(self):
        return self.slot.prompt

    @property
    def yaml(self):
        if self.values:
            return {
                'name': self.type,
                'values': [
                    {'value': value}
                    for value in self.values
                ]
            }