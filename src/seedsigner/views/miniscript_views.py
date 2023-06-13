from dataclasses import dataclass
from typing import List

from seedsigner.gui.components import FontAwesomeIconConstants
from seedsigner.gui.screens.screen import DireWarningScreen, ButtonListScreen
from seedsigner.gui.screens.screen import WarningScreen, QRDisplayScreen
from seedsigner.models import QRType
from seedsigner.models.settings import SettingsConstants
from seedsigner.models.encode_qr import EncodeQR

from embit.networks import NETWORKS
from embit.descriptor import Descriptor
from embit.bip32 import HDKey
from embit.psbt import PSBT

from .view import BackStackView, View, Destination, MainMenuView


class PSBTCheckView(View):
    def run(self) -> Destination:

        from .scan_views import ScanView
        from seedsigner.gui.screens import ButtonListScreen

        tx = self.controller.psbt
        menu_items = []
        descriptor: Descriptor = self.controller.miniscript_descriptor

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
            (("Sign ", FontAwesomeIconConstants.QRCODE), SeedSignScanView),
            (("Cancel ", FontAwesomeIconConstants.QRCODE), MainMenuView),
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

        self.controller.miniscript_descriptor = None

        return Destination(dest)


class SeedSignScanView(View):
    def run(self) -> Destination:

        from .scan_views import ScanView
        from seedsigner.gui.screens import LargeButtonScreen
        menu_items = []

        menu_items.append((("Scan your seed", None), None, None, None))
        menu_items.append((("Scan", FontAwesomeIconConstants.QRCODE), ScanView, QRType.SEED, SignView))

        screen = ButtonListScreen(
            title="SEED",
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
                self.controller.scan_target = menu_items[selected_menu_num][2]
                dest = menu_items[selected_menu_num][1]
                self.controller.scan_target = menu_items[selected_menu_num][2]
                self.controller.next_view = menu_items[selected_menu_num][3]
                out = True

        return Destination(dest)


class SignView(View):
    def run(self) -> Destination:
        from .scan_views import ScanView
        from seedsigner.gui.screens import LargeButtonScreen
        menu_items = []

        menu_items.append((("Sign", None), PSBTQRDisplayView, True))
        menu_items.append((("Cancel", None), MainMenuView, False))

        screen = ButtonListScreen(
            title="SEED",
            title_font_size=26,
            button_data=[entry[0] for entry in menu_items],
            show_back_button=False,
            show_power_button=False,
        )

        selected_menu_num = screen.display()

        dest = menu_items[selected_menu_num][1]

        if menu_items[selected_menu_num][2]:
            root: HDKey = self.controller.root_key
            psbt: PSBT = self.controller.psbt
            psbt.sign_with(root)

        return Destination(dest)


class PSBTScanView(View):
    def run(self) -> Destination:

        from .scan_views import ScanView
        from seedsigner.gui.screens import LargeButtonScreen
        menu_items = []

        menu_items.append((("Scan your PSBT", None), None, None, None))
        menu_items.append((("Scan", FontAwesomeIconConstants.QRCODE), ScanView, QRType.PSBT__BASE64, PSBTCheckView))

        screen = ButtonListScreen(
            title="PSBT",
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
                self.controller.scan_target = menu_items[selected_menu_num][2]
                dest = menu_items[selected_menu_num][1]
                self.controller.scan_target = menu_items[selected_menu_num][2]
                self.controller.next_view = menu_items[selected_menu_num][3]
                out = True

        return Destination(dest)


class DescriptorScanView(View):
    def run(self) -> Destination:

        from .scan_views import ScanView
        from seedsigner.gui.screens import LargeButtonScreen
        menu_items = []

        menu_items.append((("Scan your Descriptor", None), None, None, None))
        menu_items.append((("Scan", FontAwesomeIconConstants.QRCODE), ScanView, QRType.DESCRIPTOR, PSBTCheckView))

        screen = ButtonListScreen(
            title="PSBT",
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
                self.controller.scan_target = menu_items[selected_menu_num][2]
                self.controller.next_view = menu_items[selected_menu_num][3]
                out = True

        return Destination(dest)


class PSBTQRDisplayView(View):
    def run(self):
        qr_encoder = EncodeQR(
            psbt=self.controller.psbt,
            qr_type=QRType.PSBT__SPECTER,  # All coordinators (as of 2022-08) use this format
            qr_density=self.settings.get_value(SettingsConstants.SETTING__QR_DENSITY),
            wordlist_language_code=self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE),
        )
        QRDisplayScreen(qr_encoder=qr_encoder).display()

        # We're done with this PSBT. Route back to MainMenuView which always
        #   clears all ephemeral data (except in-memory seeds).
        return Destination(MainMenuView, clear_history=True)