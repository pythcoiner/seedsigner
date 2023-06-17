import hashlib
from dataclasses import dataclass

from embit.descriptor.descriptor import Descriptor
from embit.psbt import PSBT
from embit.bip32 import HDKey

from seedsigner.views.view import Destination, MainMenuView, NotYetImplementedView
from seedsigner.views.miniscript_views import SeedNotSelectedView, DescriptorWrongSeedView, MiniscriptShowPolicyView
from seedsigner.views.miniscript_views import DescriptorInvalidPoRView, DescriptorRegisterPolicyView


class MiniDescriptor:

    def __init__(self, parent: MiniscriptController):
        self.parent: MiniscriptController = None
        self.is_loaded = False
        self.is_checked = False
        self.descriptor: Descriptor = None
        self.imported_por = None
        self.descriptor_alias: str = None
        self.aliases: list[str] = None

    def reset(self):
        self.__init__(self.parent)

    def load(self, descriptor: Descriptor) -> None:
        self.__init__(parent)
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

    def __init__(self, parent):
        self.parent: MiniscriptController = None
        self.mnemonic: str = ""
        self.seed: HDKey = None
        self.is_loaded = False

    def reset(self):
        self.__init__(self.parent)
        
    def load(self, mnemonic: str):
        self.__init__(parent)
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


class MiniPSBT:
    
    def __init__(self, parent):
        self.parent: MiniscriptController = parent
        self.descriptor: Descriptor = self.parent.descriptor.descriptor
        self.seed: HDKey = self.parent.seed.seed
        self.raw: str = None
        self.psbt: PSBT = None
        self.is_selected = False
        self.is_processed = False
        self.is_checked = False
        self.is_signed = False
        self.owners_fingerprints = []

    def reset(self):
        self.__init__(self.parent)
        
    def load(self, raw) -> bool:
        self.__init__(self.parent)
        self.raw = raw
        self.is_selected = True
        return self.process()

    def process(self) -> bool:
        # if descriptor
        if self.is_selected and self.parent.descriptor.is_checked:
            self.psbt = PSBT.from_string(self.raw)
            owns = False
            for i in self.psbt.inputs:
                if self.descriptor.owns(i):
                    owns = True
            if not owns:
                self.psbt = None
                return False
            self.is_processed = True
            return True
        else:
            return False


class MiniscriptController:

    def __init__(self):
        self.descriptor = MiniDescriptor(self)
        self.seed = MiniSeed(self)
        self.psbt = MiniPSBT(self)

    def load_seed(self, seed: str):
        self.seed = MiniSeed(self)
        self.seed.load(seed)
        
    def load_descriptor(self, descriptor: Descriptor):
        self.descriptor = MiniDescriptor(self)
        self.descriptor.load(descriptor)

    def load_psbt(self, psbt: str):
        self.psbt = MiniPSBT(self)
        self.psbt.load(psbt)

    def route(self) -> Destination:
        """
        If user doesn't follow the 'normal' workflow, it's better to handle all the view routing cases in only one
        method that can be called recursively from any step in the process. This routing method is not the default
        routing, default behavior will be handle directly in views.
        """

        descriptor_init = self.descriptor.is_loaded and not self.descriptor.is_checked
        psbt_init = self.psbt.is_selected and not self.psbt.is_processed

        # descriptor loaded but not seed
        if not self.seed.is_loaded and descriptor_init:
            return Destination(SeedNotSelectedView, clear_history=True)

        # seed loaded, now load descriptor
        elif self.seed.is_loaded and descriptor_init:

            #  seed have control on descriptor
            if self.seed.control_descriptor(self.descriptor):

                # PoR is supplied with descriptor
                if self.descriptor.has_por():
                    #  PoR is valid
                    if self.descriptor.has_valid_por():
                        return Destination(MiniscriptShowPolicyView, view_args={'alias': self.descriptor.descriptor_alias})
                    #  PoR is not valid
                    else:
                        return Destination(DescriptorInvalidPoRView, clear_history=True)
                # descriptor doesn't got PoR supplied with
                else:
                    return Destination(DescriptorRegisterPolicyView, clear_history=True)

            # seed doesn't control descriptor
            else:
                return Destination(DescriptorWrongSeedView, clear_history=True)

        # seed and descriptor already loaded, now load PSBT
        elif self.descriptor.is_checked and psbt_init:

            #  descriptor not owns PSBT
            if not self.psbt.process():
                return Destination(DescriptorNotOwnsPSBTView)

            #  descriptor owns psbt
            else:
                return Destination(DescriptorShowPolicy)

        else:
            return Destination(NotYetImplementedView, clear_history=True)


