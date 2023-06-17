import hashlib
from dataclasses import dataclass

from embit.descriptor.descriptor import Descriptor
from embit.psbt import PSBT
from embit.bip32 import HDKey

from seedsigner.views.view import Destination, MainMenuView, NotYetImplementedView
from seedsigner.views.miniscript_views import SeedNotSelectedView, DescriptorWrongSeedView, MiniscriptShowPolicyView
from seedsigner.views.miniscript_views import DescriptorInvalidPoRView, DescriptorRegisterPolicyView


class MiniDescriptor:
    parent: MiniscriptController = None
    is_loaded = False
    is_checked = False
    descriptor: Descriptor = None
    imported_por = None
    descriptor_alias: str = None
    aliases: list[str] = None

    def __init__(self, parent: MiniscriptController):
        self.parent = parent

    def reset(self) -> None:
        self.is_loaded = False
        self.is_checked = False
        self.descriptor = None
        self.por = None
        self.descriptor_alias = None
        self.aliases = None

    def load(self, descriptor: Descriptor) -> None:
        if descriptor.miniscript:
            self.descriptor = descriptor
            self.is_loaded = True

    def get(self) -> Descriptor:
        return self.descriptor

    def has_por(self) -> bool:
        return self._imported_por is not None

    def has_valid_por(self) -> bool:
        if self.por:
            por = self.process_por()
            if self._imported_por == por:
                return True

        return False

    def process_por(self) -> str:
        seed = self.parent.seed.mnemonic
        descriptor = self.descriptor.full_policy
        alias = self.descriptor_alias
        
        msg = seed + descriptor + alias
        msg = bytes(msg, 'utf-8')
        return hashlib.new('ripemd160', msg).hexdigest()


class MiniSeed:
    parent: MiniscriptController = None
    mnemonic: str = ""
    seed: HDKey = None
    is_loaded = False

    def __init__(self, parent):
        self.parent = parent
        
    def load(self, mnemonic: str):
        self.mnemonic = mnemonic
        self.seed = bip32.HDKey.from_seed(bip39.mnemonic_to_seed(mnemonic))
        self.is_loaded = False
        
    def fingerprint(self) -> int | bytes:
        return self.seed.my_fingerprint
        
    def control_descriptor(self) -> bool:  
        have_control = False
        for i in self.parent.descriptor.descriptor.keys:
            if i.fingerprint == self.fingerprint:
                have_control = True
                
        return have_control


class MiniscriptController:

    def __init__(self):
        self.descriptor = MiniDescriptor(self)
        self.seed = MiniSeed(self)
        
    def load_descriptor(self, descriptor):
        self.descriptor = MiniDescriptor(self)
        self.descriptor.load(descriptor)
        
    def route(self, _from=None) -> Destination:
        
        descriptor_init = self.descriptor.is_loaded and not self.descriptor.is_checked
        
        if not self.seed.is_loaded and descriptor_init:
            return Destination(SeedNotSelectedView, clear_history=True)
        
        elif self.seed.is_loaded and descriptor_init:

            if self.seed.control_descriptor(self.descriptor):
                if self.descriptor.has_por():
                    if self.descriptor.has_valid_por():
                        return Destination(MiniscriptShowPolicyView, view_args={'alias': self.descriptor.descriptor_alias})
                    else:
                        return Destination(DescriptorInvalidPoRView, clear_history=True)
                else:
                    return Destination(DescriptorRegisterPolicyView, clear_history=True)
            else:
                return Destination(DescriptorWrongSeedView, clear_history=True)
        else:
            return Destination(NotYetImplementedView, clear_history=True)
            
        
            

    