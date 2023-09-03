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

from bech32 import bech32_decode, bech32_encode, convertbits
from embit import bip39, bip32
from embit.ec import PrivateKey
from binascii import unhexlify
import hashlib

def lnurl_decode(lnurl: str) -> str:
    hrp, data = bech32_decode(lnurl)
    assert hrp
    assert data
    bech32_data = convertbits(data, 5, 8, False)
    assert bech32_data
    return bytes(bech32_data).decode()


def lnurl_encode(url: str) -> str:
    bech32_data = convertbits(url.encode(), 8, 5, True)
    assert bech32_data
    lnurl = bech32_encode("lnurl", bech32_data)
    return lnurl.upper()


class LoginView(View):
    def run(self) -> Destination:
        from seedsigner.gui.screens import LargeButtonScreen
        menu_items = [
            (("Login", None), LNURLDisplayView, True),
            (("Cancel", None), MainMenuView, False),
            ]

        screen = ButtonListScreen(
            title="Do you want login?",
            title_font_size=26,
            button_data=[entry[0] for entry in menu_items],
            show_back_button=False,
            show_power_button=False,
        )

        selected_menu_num = screen.display()

        dest = menu_items[selected_menu_num][1]

        return Destination(dest)


class LNURLDisplayView(View):
    def run(self):
        qr_encoder = EncodeQR(
            lnurl=self.controller.lnurl,
            qr_type=QRType.LNURL,  
            qr_density=self.settings.get_value(SettingsConstants.SETTING__QR_DENSITY),
        )
        QRDisplayScreen(qr_encoder=qr_encoder).display()

        return Destination(MainMenuView, clear_history=True)




