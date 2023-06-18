import json
import re

from embit.descriptor import Descriptor
from embit import bip32,bip39

from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON
from seedsigner.models import DecodeQR, Seed
from seedsigner.models.settings import SettingsConstants

from .view import BackStackView, MainMenuView, NotYetImplementedView, View, Destination

from .miniscript_views import PSBTCheckView, SignView  #, DescriptorScanView  , SeedSignScanView, PSBTScanView,
from .miniscript_views import PSBTQRDisplayView, SeedNotSelectedView, DescriptorNotSelectedView, DescriptorRegisterPolicyView
from .miniscript_views import MiniscriptRouterView
    
    
class ScanView(View):
    def run(self):
        from seedsigner.gui.screens.scan_screens import ScanScreen
        from seedsigner.views.seed_views import SeedsMenuView, LoadSeedView
        from seedsigner.views.miniscript_views import MiniscriptShowPolicyView

        wordlist_language_code = self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE)
        self.decoder = DecodeQR(wordlist_language_code=wordlist_language_code)

        # Start the live preview and background QR reading
        ScanScreen(decoder=self.decoder).display()

        # Handle the results
        if self.decoder.is_complete:
            #  Seed
            if self.decoder.is_seed:
                print("decoder is seed")
                seed_mnemonic = self.decoder.get_seed_phrase()
                if not seed_mnemonic:
                    # seed is not valid, Exit if not valid with message
                    return Destination(NotYetImplementedView)
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

            #  PSBT
            elif self.decoder.is_psbt:
                print("decoder is psbt")
                from seedsigner.views.psbt_views import PSBTSelectSeedView, PSBTOverviewView
                from seedsigner.views.miniscript_views import PSBTCheckView, MiniscriptShowPolicyView

                self.controller.miniscript.load_psbt(self.decoder.get_psbt())

                # seed & descriptor already loaded and descriptor owns psbt
                if self.controller.miniscript.psbt.is_processed:
                    print("psbt is processed")
                    alias = self.controller.miniscript.descriptor.descriptor_alias
                    return Destination(MiniscriptShowPolicyView, view_args={"alias": alias})

                else:
                    print("psbt is not processed")
                    return Destination(MiniscriptRouterView)

            # Descriptor
            elif self.decoder.is_wallet_descriptor:
                print("decoder is descriptor")
                descriptor_str = self.decoder.get_wallet_descriptor()

                #  process the str
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

                    self.controller.miniscript.load_descriptor(descriptor)
                    print(type(self.decoder))
                    self.controller.miniscript.descriptor.imported_por = self.decoder.decoder.get_wallet_por()
                    self.controller.miniscript.descriptor.descriptor_alias = self.decoder.decoder.get_wallet_alias()

                    seed = self.controller.miniscript.seed
                    descriptor = self.controller.miniscript.descriptor

                    if seed.is_loaded and seed.control_descriptor() and descriptor.has_valid_por():
                        alias = self.controller.miniscript.descriptor.descriptor_alias
                        return Destination(MiniscriptShowPolicyView, view_args={"alias": alias})

                    elif seed.is_loaded and not descriptor.has_por():
                        return Destination(DescriptorRegisterPolicyView)

                    else:
                        return Destination(MiniscriptRouterView)

            return Destination(NotYetImplementedView)

        else:
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

