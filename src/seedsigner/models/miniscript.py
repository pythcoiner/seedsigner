import hashlib

from embit.bip32 import HDKey
from embit import bip39
from embit.psbt import PSBT

from .seed import Seed


class MiniDescriptor:
    import hashlib
    from embit.descriptor.descriptor import Descriptor

    def __init__(self, parent):

        self.parent: MiniscriptController = parent
        self.is_loaded = False
        self.is_checked = False
        self.descriptor: Descriptor = None
        self.imported_por = None
        self.descriptor_alias: str = None
        self.aliases: list[str] = None

    def reset(self):
        self.__init__(self.parent)

    def load(self, descriptor: Descriptor) -> None:
        print("MiniDescriptor.load()")
        self.__init__(self.parent)
        if descriptor.miniscript:
            self.descriptor = descriptor
            self.is_loaded = True
        print("+++++++++++++++++++++++")

    def get(self) -> Descriptor:
        return self.descriptor

    def has_por(self) -> bool:
        return self.imported_por is not None

    def has_valid_por(self) -> bool:
        if self.imported_por:
            por = self.process_por()
            if self.imported_por == por:
                return True
            else:
                print(f"{self.imported_por} =! {por}")

        return False

    def process_por(self) -> str:
        seed = " ".join(self.parent.seed.mnemonic)
        descriptor = self.descriptor.full_policy
        alias = self.descriptor_alias
        msg = seed + descriptor + alias
        msg = bytes(msg, 'utf-8')
        return hashlib.new('ripemd160', msg).hexdigest()


class MiniSeed:

    def __init__(self, parent):
        from embit.bip32 import HDKey

        self.parent: MiniscriptController = parent
        self.mnemonic: str = ""
        self.seed: HDKey = None
        self.is_loaded = False

    def reset(self):
        self.__init__(self.parent)
        
    def load(self, seed: Seed):
        self.__init__(self.parent)
        self.mnemonic = seed._mnemonic
        self.seed = HDKey.from_seed(seed.seed_bytes)
        self.is_loaded = True
        
    def fingerprint(self) -> bytes:
        return self.seed.my_fingerprint
        
    def control_descriptor(self) -> bool:
        have_control = False
        for i in self.parent.descriptor.descriptor.keys:
            if i.fingerprint == self.seed.my_fingerprint:
                have_control = True
        return have_control


class MiniPSBT:
    from embit.psbt import PSBT
    
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
        print("MiniPSBT.load()")
        self.__init__(self.parent)
        self.raw = raw
        self.is_selected = True
        out = self.process()
        print('***********************')
        return out

    def process(self) -> bool:
        print("MiniPSBT.process()")

        # if descriptor already loaded
        if self.is_selected and self.parent.descriptor.is_checked:
            self.psbt = self.raw
            print(f"type(self.psbt)={type(self.psbt)}")
            
            owns = False
            for i in self.psbt.inputs:
                if self.parent.descriptor.descriptor.owns(i):
                    owns = True
                    
            if not owns:
                self.psbt = None
                return False
            
            self.is_processed = True
            return True
        else:
            return False


class MiniscriptController:
    from embit.descriptor.descriptor import Descriptor

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




