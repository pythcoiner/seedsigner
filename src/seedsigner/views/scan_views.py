import json
import re

from embit.descriptor import Descriptor
from embit import bip32,bip39

from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON
from seedsigner.models import DecodeQR, Seed
from seedsigner.models.settings import SettingsConstants


from .view import BackStackView, MainMenuView, NotYetImplementedView, View, Destination

from .miniscript_views import PSBTCheckView, SeedSignScanView, SignView, PSBTScanView, DescriptorScanView, PSBTQRDisplayView

def process_por(seed, descriptor):
    import hashlib
    msg = seed + descriptor
    msg = bytes(msg, 'utf-8')
    return hashlib.new('ripemd160', msg).hexdigest()
    
    
class ScanView(View):
    def run(self):
        from seedsigner.gui.screens.scan_screens import ScanScreen

        wordlist_language_code = self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE)
        self.decoder = DecodeQR(wordlist_language_code=wordlist_language_code)

        # Start the live preview and background QR reading
        ScanScreen(decoder=self.decoder).display()

        # Handle the results
        if self.decoder.is_complete:
            if self.decoder.is_seed:
                seed_mnemonic = self.decoder.get_seed_phrase()
                if not seed_mnemonic:
                    # seed is not valid, Exit if not valid with message
                    raise Exception("Not yet implemented!")
                else:
                    # Found a valid mnemonic seed! All new seeds should be considered
                    #   pending (might set a passphrase, SeedXOR, etc) until finalized.
                    from .seed_views import SeedFinalizeView
                    self.controller.storage.set_pending_seed(
                        Seed(mnemonic=seed_mnemonic, wordlist_language_code=wordlist_language_code)
                    )
                    if self.settings.get_value(SettingsConstants.SETTING__PASSPHRASE) == SettingsConstants.OPTION__REQUIRED:
                        from seedsigner.views.seed_views import SeedAddPassphraseView
                        return Destination(SeedAddPassphraseView)
                    else:
                        return Destination(SeedFinalizeView)
            
            elif self.decoder.is_psbt:
                from seedsigner.views.psbt_views import PSBTSelectSeedView, PSBTOverviewView
                # from seedsigner.views.miniscript_views import PSBTCheckView
                psbt = self.decoder.get_psbt()
                self.controller.psbt = psbt
                self.controller.psbt_parser = None
                if self.controller.miniscript_descriptor:
                    return Destination(PSBTOverviewView, skip_current_view=True)
                else:
                    return Destination(PSBTSelectSeedView, skip_current_view=True)

            # elif self.decoder.is_settings:
            #     from seedsigner.models.settings import Settings
            #     settings = self.decoder.get_settings_data()
            #     Settings.get_instance().update(new_settings=settings)
            # 
            #     print(json.dumps(Settings.get_instance()._data, indent=4))
            # 
            #     return Destination(SettingsUpdatedView, {"config_name": self.decoder.get_settings_config_name()})
            
            elif self.decoder.is_wallet_descriptor:
                # from seedsigner.views.seed_views import MultisigWalletDescriptorView
                descriptor_str = self.decoder.get_wallet_descriptor()

                try:
                    # We need to replace `/0/*` wildcards with `/{0,1}/*` in order to use
                    # the Descriptor to verify change, too.
                    orig_descriptor_str = descriptor_str
                    if len(re.findall (r'\[([0-9,a-f,A-F]+?)(\/[0-9,\/,h\']+?)\].*?(\/0\/\*)', descriptor_str)) > 0:
                        p = re.compile(r'(\[[0-9,a-f,A-F]+?\/[0-9,\/,h\']+?\].*?)(\/0\/\*)')
                        descriptor_str = p.sub(r'\1/{0,1}/*', descriptor_str)
                    elif len(re.findall (r'(\[[0-9,a-f,A-F]+?\/[0-9,\/,h,\']+?\][a-z,A-Z,0-9]*?)([\,,\)])', descriptor_str)) > 0:
                        p = re.compile(r'(\[[0-9,a-f,A-F]+?\/[0-9,\/,h,\']+?\][a-z,A-Z,0-9]*?)([\,,\)])')
                        descriptor_str = p.sub(r'\1/{0,1}/*\2', descriptor_str)
                except Exception as e:
                    print(repr(e))
                    descriptor_str = orig_descriptor_str

                descriptor = Descriptor.from_string(descriptor_str)


                if descriptor.miniscript:

                        # print(f"Received miniscript descriptor: {descriptor}")
                        self.controller.miniscript_descriptor = descriptor

                        por = self.decoder.decoder.get_wallet_por()
                        if self.controller.miniscript_seed:
                            seed = bip39.mnemonic_to_seed(self.controller.miniscript_seed.mnemonic_str)
                            fingerprint = bip32.HDKey.from_seed(seed).my_fingerprint

                            for i in descriptor.keys:
                                print(i)
                                print(type(i.key))
                                print(str(i)[1:9])
                                print(str(i.fingerprint))
                                print('---')
                            por2 = process_por(self.controller.miniscript_seed.mnemonic_str, descriptor_str)

                            print(f"por={por}")
                            print(f"por2={por2}")

                        return Destination(MainMenuView, clear_history=True)

                else:
                    return Destination(NotYetImplementedView)
            
            else:
                return Destination(NotYetImplementedView)

        elif self.decoder.is_invalid:
            raise Exception("QRCode not recognized or not yet supported.")

        return Destination(MainMenuView)



class SettingsUpdatedView(View):
    def __init__(self, config_name: str):
        super().__init__()

        self.config_name = config_name
    

    def run(self):
        from seedsigner.gui.screens.scan_screens import SettingsUpdatedScreen
        screen = SettingsUpdatedScreen(config_name=self.config_name)
        selected_menu_num = screen.display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        # Only one exit point
        return Destination(MainMenuView)

