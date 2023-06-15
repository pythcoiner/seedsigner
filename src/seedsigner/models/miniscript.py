from dataclasses import dataclass

from embit.descriptor.descriptor import Descriptor
from embit.psbt import PSBT
from embit.bip32 import HDKey

from seedsigner.views.view import View

@dataclass
class MiniDescriptor:
    is_loaded = False
    is_checked = False
    descriptor: Descriptor = None
    por = None
    descriptor_alias: str = None
    aliases: list[str] = None

    def reset(self):
        self.is_loaded = False
        self.has_valid_por = False
        self.is_checked = False
        self.descriptor = None
        self.por = None
        self.descriptor_alias = None
        self.aliases = None

    def load(self, descriptor: Descriptor):
        if descriptor.miniscript:
            self.descriptor = descriptor
            self.is_loaded = True

    def get(self):
        return self.descriptor

    def has_por(self):
        return self.por is not None

    def has_valid_por(self):
        if self.por:
            por = self.process_por()
            if self.por == por:
                return True

        return False

    def process_por(self) -> str:
        pass

@dataclass
class MiniKey:
    root_key: HDKey = None


@dataclass
class MiniscriptController:
    descriptor = MiniDescriptor()

    def route(self) -> View:
        pass

    