from typing import Callable, List
from slot_faker import SlotFaker

slot_faker = SlotFaker()

class SlotType:
    def __init__(self, name: str):
        self.name = name


class Slot:
    def __init__(self, name: str, slot_type: SlotType, faker: Callable = None):
        self.name = name
        self.slot_type = slot_type
        self.value = faker() if faker else None

    @property
    def type(self):
        return self.slot_type.name


class Utterance:
    def __init__(self, template: str, *slots: List[Slot]):
        self.template = template
        self.slots = slots

    @property
    def sample(self):
        sample = self.template
        for slot in self.slots:
            sample = sample.replace(f"{{{slot.name}}}", slot.value)

i