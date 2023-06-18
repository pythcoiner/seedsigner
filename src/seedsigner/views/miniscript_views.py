from seedsigner.gui.components import FontAwesomeIconConstants
from seedsigner.gui.screens.screen import DireWarningScreen, ButtonListScreen
from seedsigner.gui.screens.screen import WarningScreen, QRDisplayScreen
from seedsigner.models import QRType
from seedsigner.models.settings import SettingsConstants
from seedsigner.models.encode_qr import EncodeQR

from embit.networks import NETWORKS
from embit.descriptor import Descriptor
from embit import bip39, bip32
from embit.bip32 import HDKey
from embit.psbt import PSBT

from .view import BackStackView, View, Destination, MainMenuView, NotYetImplementedView
from seedsigner.models import miniscript as mini


class MiniscriptRouterView(View):
    def run(self) -> Destination:
        """
        If user doesn't follow the 'normal' workflow, it's better to handle all the view routing cases in only one
        method that can be called recursively from any step in the process. This routing method is not the default
        routing, default behavior will be handle directly in views.
        """

        print('MiniscriptRouterView()')
        miniscript = self.controller.miniscript

        print("Seed:")
        print(f"{miniscript.seed}")
        print(f"miniscript.seed.is_loaded={miniscript.seed.is_loaded}")

        print("Descriptor:")
        print(f"{miniscript.descriptor}")
        print(f"miniscript.descriptor.is_loaded={miniscript.descriptor.is_loaded}")
        print(f"miniscript.descriptor.is_checked={miniscript.descriptor.is_checked}")

        print("PSBT:")
        print(f"{miniscript.psbt}")
        print(f"miniscript.psbt.is_selected={miniscript.psbt.is_selected}")
        print(f"miniscript.psbt.is_processed={miniscript.psbt.is_processed}")
        print(f"miniscript.psbt.is_checked={miniscript.psbt.is_checked}")
        print(f"miniscript.psbt.is_signed={miniscript.psbt.is_signed}")

        descriptor_init = miniscript.descriptor.is_loaded and not miniscript.descriptor.is_checked
        psbt_init = miniscript.psbt.is_selected and not miniscript.psbt.is_processed

        if descriptor_init:
            print("descriptor_init")

        if psbt_init:
            print("psbt_init")

        # descriptor loaded but not seed
        if not miniscript.seed.is_loaded and descriptor_init:
            print("descriptor loaded but not seed")
            return Destination(SeedNotSelectedView, clear_history=True)

        # seed loaded, now load descriptor
        elif miniscript.seed.is_loaded and descriptor_init:
            print("seed loaded, now load descriptor")
            #  seed have control on descriptor
            if miniscript.seed.control_descriptor():
                print("seed have control on descriptor")
                # PoR is supplied with descriptor
                if miniscript.descriptor.has_por():
                    print("PoR is supplied with descriptor")
                    #  PoR is valid
                    if miniscript.descriptor.has_valid_por():
                        print("PoR is valid")
                        return Destination(MiniscriptShowPolicyView,
                                           view_args={'alias': miniscript.descriptor.descriptor_alias})
                    #  PoR is not valid
                    else:
                        print("PoR is not valid")
                        return Destination(DescriptorInvalidPoRView, clear_history=True)
                # descriptor doesn't got PoR supplied with
                else:
                    print("descriptor doesn't got PoR supplied with")
                    return Destination(DescriptorRegisterPolicyView, clear_history=True)

            # seed doesn't control descriptor
            else:
                print("seed doesn't control descriptor")
                return Destination(DescriptorWrongSeedView, clear_history=True)

        # seed and descriptor already loaded, now load PSBT
        elif miniscript.descriptor.is_checked and psbt_init:
            print("seed and descriptor already loaded, now load PSBT")
            #  descriptor not owns PSBT
            if not miniscript.psbt.process():
                print("descriptor not owns PSBT")
                return Destination(DescriptorNotOwnsPSBTView)

            #  descriptor owns psbt
            else:
                alias = miniscript.descriptor.descriptor_alias
                return Destination(MiniscriptShowPolicyView, view_args={"alias": alias})

        # seed and psbt is loaded and descriptor not loaded
        elif miniscript.seed.is_loaded and miniscript.psbt.is_selected and not miniscript.descriptor.is_loaded:
            return Destination(DescriptorNotSelectedView)
        
        # only psbt loaded
        elif not miniscript.seed.is_loaded and not miniscript.descriptor.is_loaded and miniscript.psbt.is_selected:
            return Destination(DescriptorNotSelectedView)

        else:
            return Destination(MainMenuView, clear_history=True)


class PSBTCheckView(View):
    def run(self) -> Destination:
        # TODO: add detailed review on input and output details

        from .scan_views import ScanView
        from seedsigner.gui.screens import ButtonListScreen

        tx = self.controller.miniscript.psbt.psbt
        menu_items = []
        descriptor: Descriptor = self.controller.miniscript.descriptor.descriptor

        for inp in tx.inputs:
            sats = inp.utxo.value
            addr = inp.utxo.script_pubkey.address(NETWORKS['signet'])
            addr = addr[:7] + '...' + addr[-5:]

            from_myself = descriptor.owns(inp)
            if from_myself:
                menu_items.append(((f"{sats} from myself", None), None, None))
            else:
                menu_items.append(((f"{sats} from ", None), None, None))
                menu_items.append(((f"{addr}", None), None, None))
        not_to_myself = 0
        for out in tx.outputs:  # type: OutScope
            sats = out.value
            addr = out.script_pubkey.address(NETWORKS['signet'])
            addr = addr[:7] + '...' + addr[-5:]
            #  TODO: show address details

            to_myself = descriptor.owns(out)
            if not to_myself:
                not_to_myself += 1
                menu_items.append(((f"{sats} to", None), None, None))
                menu_items.append(((str(addr), None), None, None))

        if not_to_myself == 0:
            menu_items.append((("self send", None), None, None))

        menu_items += [
            (("Sign ", None), SignView),
            (("Cancel ", None), MainMenuView),
        ]

        screen = ButtonListScreen(
            title="Check PSBT:",
            title_font_size=26,
            button_data=[entry[0] for entry in menu_items],
            show_back_button=False,
            show_power_button=False,
        )

        out = False
        dest = None
        while not out:
            selected_menu_num = screen.display()

            if menu_items[selected_menu_num][1] is not None:
                dest = menu_items[selected_menu_num][1]
                out = True

        return Destination(dest)


# class SeedSignScanView(View):
#     def run(self) -> Destination:
#
#         from .scan_views import ScanView
#         from seedsigner.gui.screens import LargeButtonScreen
#         menu_items = []
#
#         menu_items.append((("Scan your seed", None), None, None, None))
#         menu_items.append((("Scan", FontAwesomeIconConstants.QRCODE), ScanView, QRType.SEED, SignView))
#
#         screen = ButtonListScreen(
#             title="SEED",
#             title_font_size=26,
#             button_data=[entry[0] for entry in menu_items],
#             show_back_button=False,
#             show_power_button=False,
#         )
#         out = False
#         dest = None
#         while not out:
#             selected_menu_num = screen.display()
#
#             if menu_items[selected_menu_num][1] is not None:
#                 self.controller.scan_target = menu_items[selected_menu_num][2]
#                 dest = menu_items[selected_menu_num][1]
#                 self.controller.scan_target = menu_items[selected_menu_num][2]
#                 self.controller.next_view = menu_items[selected_menu_num][3]
#                 out = True
#
#         return Destination(dest)


class SignView(View):
    def run(self) -> Destination:
        from .scan_views import ScanView
        from seedsigner.gui.screens import LargeButtonScreen
        menu_items = []

        menu_items.append((("Display signed PSBT", None), PSBTQRDisplayView, True))
        menu_items.append((("Cancel", None), MainMenuView, False))

        screen = ButtonListScreen(
            title="Signing...",
            title_font_size=26,
            button_data=[entry[0] for entry in menu_items],
            show_back_button=False,
            show_power_button=False,
        )

        selected_menu_num = screen.display()

        dest = menu_items[selected_menu_num][1]

        if menu_items[selected_menu_num][2]:
            root: bip32.HDKey = self.controller.miniscript.seed.seed
            psbt: PSBT = self.controller.miniscript.psbt.psbt
            signed = psbt.sign_with(root)

        return Destination(dest)


class PSBTQRDisplayView(View):
    def run(self):
        qr_encoder = EncodeQR(
            psbt=self.controller.miniscript.psbt.psbt,
            qr_type=QRType.PSBT__SPECTER,  # All coordinators (as of 2022-08) use this format
            qr_density=self.settings.get_value(SettingsConstants.SETTING__QR_DENSITY),
            wordlist_language_code=self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE),
        )
        QRDisplayScreen(qr_encoder=qr_encoder).display()

        self.controller.miniscript.psbt.reset()
        self.controller.miniscript.descriptor.reset()

        return Destination(MainMenuView, clear_history=True)


class MiniscriptShowPolicyView(View):
    def __init__(self, alias):
        super().__init__()
        self.alias = alias

    def run(self):
        menu_items = [self.alias, 'OK', 'Cancel']

        while True:
            selected_menu_num = ButtonListScreen(
                title="Descriptor Alias:",
                is_button_text_centered=True,
                button_data=menu_items
            ).display()

            if menu_items[selected_menu_num] == 'OK':
                self.controller.miniscript.descriptor.is_checked = True

                # if PSBT load and not signed
                psbt: mini.MiniPSBT = self.controller.miniscript.psbt
                if not psbt.is_selected:
                    print("not psbt")
                    return Destination(MainMenuView, clear_history=True)
                elif psbt.is_processed and not psbt.is_checked:
                    return Destination(PSBTCheckView)
                else:
                    return Destination(MiniscriptRouterView)

            elif menu_items[selected_menu_num] == 'Cancel':
                return Destination(MainMenuView)


class SeedNotSelectedView(View):

    def run(self):
        from .seed_views import LoadSeedView
        WarningScreen(
            title="Seed not selected!",
            status_headline="",
            text="No selected seed, please scan/select one!",
            button_data=["OK"],
        ).display()

        return Destination(LoadSeedView)


class DescriptorNotSelectedView(View):

    def run(self):
        from .scan_views import ScanView
        WarningScreen(
            title="Descriptor missing!",
            status_headline="",
            text="No descriptor, please scan one!",
            button_data=["OK"],
        ).display()

        return Destination(ScanView)


class DescriptorWrongSeedView(View):

    def run(self):
        from .seed_views import LoadSeedView
        WarningScreen(
            title="Wrong seed!",
            status_headline="",
            text="this seed doesn't controll this descriptor, please choose another one!",
            button_data=["OK"],
        ).display()

        return Destination(LoadSeedView)


class DescriptorInvalidPoRView(View):

    def run(self):
        from .seed_views import LoadSeedView
        WarningScreen(
            title="Invalid PoR!",
            status_headline="",
            text="The PoR supplied is invalid, please have a check!",
            button_data=["OK"],
        ).display()

        return Destination(DescriptorRegisterPolicyView)


class DescriptorRegisterPolicyView(View):

    def run(self):

        descriptor: Descriptor = self.controller.miniscript.descriptor.descriptor
        policy = descriptor.to_string()

        alias = self.controller.miniscript.descriptor.descriptor_alias
        menu_items = [alias, ]

        for i, k in enumerate(descriptor.keys):
            policy = policy.replace(str(k), chr(65 + i))
            menu_items.append(chr(65 + i) + " =")
            key = str(k)
            menu_items += [key[i:i+15] for i in range(0, len(key), 15)]

        menu_items.append('Policy:')

        n = 15
        chunks = [policy[i:i+n] for i in range(0, len(policy), n)]

        for i in chunks:
            print(i)
            menu_items.append(i)

        menu_items += ['Save', 'Continue', 'Cancel']

        while True:
            selected_menu_num = ButtonListScreen(
                title="Check Descriptor:",
                is_button_text_centered=True,
                button_data=menu_items
            ).display()

            if menu_items[selected_menu_num] == 'Continue':
                self.controller.miniscript.descriptor.is_checked = True
                return Destination(MiniscriptRouterView)


            elif menu_items[selected_menu_num] == 'Cancel':
                return Destination(MainMenuView)
    
class DescriptorNotOwnsPSBTView(View):

    def run(self):
        from .scan_views import ScanView
        WarningScreen(
            title="Wrong descriptor!",
            status_headline="",
            text="The descriptor doesn't owns this PSBT, please select another descriptor!",
            button_data=["OK"],
        ).display()

        return Destination(ScanView, clear_history=True)

