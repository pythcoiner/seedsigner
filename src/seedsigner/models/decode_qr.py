import base64
import json
import logging
import re

from binascii import a2b_base64, b2a_base64
from enum import IntEnum
from embit import psbt, bip39, bip32
from embit.networks import NETWORKS
from pyzbar import pyzbar
from pyzbar.pyzbar import ZBarSymbol

from . import QRType, Seed
from .settings import SettingsConstants

logger = logging.getLogger(__name__)


class DecodeQRStatus(IntEnum):
    """
        Used in DecodeQR to communicate status of adding qr frame/segment
    """
    PART_COMPLETE = 1
    PART_EXISTING = 2
    COMPLETE = 3
    FALSE = 4
    INVALID = 5


class DecodeQR:
    """
        Used to process images or string data from animated qr codes.
    """

    def __init__(self, controller, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH):
        self.wordlist_language_code = wordlist_language_code
        self.complete = False
        self.qr_type = None
        self.decoder = None
        self.controller = controller

    def add_image(self, image) -> DecodeQRStatus:
        data = DecodeQR.extract_qr_data(image, is_binary=True)
        if data is None:
            return DecodeQRStatus.FALSE

        return self.add_data(data)

    def add_data(self, data) -> DecodeQRStatus:
        if data is None:
            return DecodeQRStatus.FALSE

        self.qr_type = DecodeQR.detect_segment_type(data, wordlist_language_code=self.wordlist_language_code)

        data = data.decode('utf-8')

        if self.qr_type == QRType.PSBT__BASE64:
            self.controller.psbt = psbt.PSBT.from_base64(data)
            self.complete = True
            
        elif self.qr_type in [QRType.SEED__12, QRType.SEED__24]:
            mnemonic = data
            seed = bip39.mnemonic_to_seed(mnemonic)
            root = bip32.HDKey.from_seed(seed, version=NETWORKS["signet"]['xprv'])
            self.controller.root_key = root
            self.complete = True
            

        # if self.qr_type in [QRType.PSBT__UR2, QRType.OUTPUT__UR, QRType.ACCOUNT__UR, QRType.BYTES__UR]:
        #     self.decoder = URDecoder() # BCUR Decoder
        # 
        # elif self.qr_type == QRType.PSBT__SPECTER:
        #     self.decoder = SpecterPsbtQrDecoder() # Specter Desktop PSBT QR base64 decoder
        #
        # elif self.qr_type == QRType.PSBT__BASE64:
        #     self.decoder = Base64PsbtQrDecoder() # Single Segments Base64
        #
        # elif self.qr_type == QRType.PSBT__BASE43:
        #     self.decoder = Base43PsbtQrDecoder() # Single Segment Base43
        #
        # elif self.qr_type in [QRType.SEED__SEEDQR, QRType.SEED__COMPACTSEEDQR, QRType.SEED__MNEMONIC, QRType.SEED__FOUR_LETTER_MNEMONIC, QRType.SEED__UR2]:
        #     self.decoder = SeedQrDecoder(wordlist_language_code=self.wordlist_language_code)
        #
        # elif self.qr_type == QRType.SETTINGS:
        #     self.decoder = SettingsQrDecoder()  # Settings config
        #
        # elif self.qr_type == QRType.BITCOIN_ADDRESS:
        #     self.decoder = BitcoinAddressQrDecoder() # Single Segment bitcoin address
        #
        # elif self.qr_type == QRType.WALLET__SPECTER:
        #     self.decoder = SpecterWalletQrDecoder() # Specter Desktop Wallet Export decoder
        #
        # elif self.qr_type == QRType.WALLET__GENERIC:
        #     self.decoder = GenericWalletQrDecoder()
        #
        # elif self.qr_type == QRType.WALLET__CONFIGFILE:
        #     self.decoder = MultiSigConfigFileQRDecoder()

        if not self.decoder:
            # Did not find any recognizable format
            return DecodeQRStatus.INVALID

        data = data.decode('utf-8')


        rt = self.decoder.add(qr_str, self.qr_type)
        if rt == DecodeQRStatus.COMPLETE:
            self.complete = True
        return rt


    def get_percent_complete(self) -> int:
        if not self.decoder:
            return 0

        if self.qr_type in [QRType.PSBT__UR2, QRType.OUTPUT__UR, QRType.ACCOUNT__UR, QRType.BYTES__UR]:
            return int(self.decoder.estimated_percent_complete() * 100)

        elif self.qr_type in [QRType.PSBT__SPECTER]:
            if self.decoder.total_segments == None:
                return 0
            return int((self.decoder.collected_segments / self.decoder.total_segments) * 100)

        elif self.decoder.total_segments == 1:
            # The single frame QR formats are all or nothing
            if self.decoder.complete:
                return 100
            else:
                return 0

        else:
            return 0

    @property
    def is_complete(self) -> bool:
        return self.complete

    @property
    def is_invalid(self) -> bool:
        return self.qr_type == QRType.INVALID

    @property
    def is_psbt(self) -> bool:
        return self.qr_type in [
            QRType.PSBT__BASE64,
        ]

    # @property
    # def is_seed(self):
    #     return self.qr_type in [
    #         QRType.SEED__SEEDQR,
    #         QRType.SEED__COMPACTSEEDQR,
    #         QRType.SEED__UR2,
    #         QRType.SEED__MNEMONIC,
    #         QRType.SEED__FOUR_LETTER_MNEMONIC,
    #     ]
    # 
    # @property
    # def is_json(self):
    #     return self.qr_type in [QRType.SETTINGS, QRType.JSON]

    # @property
    # def is_address(self):
    #     return self.qr_type == QRType.BITCOIN_ADDRESS
    # 
    # @property
    # def is_wallet_descriptor(self):
    #     check = self.qr_type in [QRType.WALLET__SPECTER, QRType.WALLET__UR, QRType.WALLET__CONFIGFILE,
    #                              QRType.WALLET__GENERIC, QRType.OUTPUT__UR]
    # 
    #     if self.qr_type in [QRType.BYTES__UR]:
    #         cbor = self.decoder.result_message().cbor
    #         raw = Bytes.from_cbor(cbor).data
    #         data = raw.decode("utf-8").lower()
    #         check = 'policy:' in data and "format:" in data and "derivation:" in data
    # 
    #     return check
    # 
    # @property
    # def is_settings(self):
    #     return self.qr_type == QRType.SETTINGS

    @staticmethod
    def extract_qr_data(image, is_binary: bool = False) -> str:
        if image is None:
            return None

        barcodes = pyzbar.decode(image, symbols=[ZBarSymbol.QRCODE], binary=is_binary)

        for barcode in barcodes:
            # Only pull and return the first barcode
            return barcode.data

    @staticmethod
    def detect_segment_type(s, wordlist_language_code=None):

        try:

            s = s.decode('utf-8')

            try:
                words = s.split(' ')
                if len(words) == 12:
                    return QRType.SEED__12
                elif len(words) == 24:
                    return QRType.SEED__24
            except:
                pass

            if DecodeQR.is_base64_psbt(s):
                return QRType.PSBT__BASE64

            # # PSBT
            # if re.search("^UR:CRYPTO-PSBT/", s, re.IGNORECASE):
            #     return QRType.PSBT__UR2
            # 
            # elif re.search("^UR:CRYPTO-OUTPUT/", s, re.IGNORECASE):
            #     return QRType.OUTPUT__UR
            # 
            # elif re.search("^UR:CRYPTO-ACCOUNT/", s, re.IGNORECASE):
            #     return QRType.ACCOUNT__UR
            # 
            # elif re.search(r'^p(\d+)of(\d+) ([A-Za-z0-9+\/=]+$)', s,
            #                re.IGNORECASE):  # must be base64 characters only in segment
            #     return QRType.PSBT__SPECTER
            # 
            # elif re.search("^UR:BYTES/", s, re.IGNORECASE):
            #     return QRType.BYTES__UR
            # 
            # elif DecodeQR.is_base64_psbt(s):
            #     return QRType.PSBT__BASE64
            # 
            # # Wallet Descriptor
            # desc_str = s.replace("\n", "").replace(" ", "")
            # if re.search(r'^p(\d+)of(\d+) ', s, re.IGNORECASE):
            #     # when not a SPECTER Base64 PSBT from above, assume it's json
            #     return QRType.WALLET__SPECTER
            # 
            # elif re.search(r'^\{\"label\".*\"descriptor\"\:.*', desc_str, re.IGNORECASE):
            #     # if json starting with label and contains descriptor, assume specter wallet json
            #     return QRType.WALLET__SPECTER
            # 
            # elif "multisig setup file" in s.lower():
            #     return QRType.WALLET__CONFIGFILE
            # 
            # elif "sortedmulti" in s:
            #     return QRType.WALLET__GENERIC
            # 
            # # Seed
            # if re.search(r'\d{48,96}', s):
            #     return QRType.SEED__SEEDQR
            # 
            # # Bitcoin Address
            # elif DecodeQR.is_bitcoin_address(s):
            #     return QRType.BITCOIN_ADDRESS
            # 
            # # config data
            # if "type=settings" in s:
            #     return QRType.SETTINGS
            # 
            # Seed
            # create 4 letter wordlist only if not PSBT (performance gain)
            # wordlist = Seed.get_wordlist(wordlist_language_code)
            # try:
            #     _4LETTER_WORDLIST = [word[:4].strip() for word in wordlist]
            # except:
            #     _4LETTER_WORDLIST = []
            # 
            # if all(x in wordlist for x in s.strip().split(" ")):
            #     # checks if all words in list are in bip39 word list
            #     return QRType.SEED__MNEMONIC
            # 
            # elif all(x in _4LETTER_WORDLIST for x in s.strip().split(" ")):
            #     # checks if all 4 letter words are in list are in 4 letter bip39 word list
            #     return QRType.SEED__FOUR_LETTER_MNEMONIC
            # 
            # elif DecodeQR.is_base43_psbt(s):
            #     return QRType.PSBT__BASE43

        except UnicodeDecodeError:
            # Probably this isn't meant to be string data; check if it's valid byte data
            # below.
            pass

        # Is it byte data?
        # 32 bytes for 24-word CompactSeedQR; 16 bytes for 12-word CompactSeedQR
        # if len(s) == 32 or len(s) == 16:
        #     try:
        #         bitstream = ""
        #         for b in s:
        #             bitstream += bin(b).lstrip('0b').zfill(8)
        #         # print(bitstream)
        # 
        #         return QRType.SEED__COMPACTSEEDQR
        #     except Exception as e:
        #         # Couldn't extract byte data; assume it's not a byte format
        #         pass

        return QRType.INVALID

    @staticmethod
    def is_base64(s):
        try:
            return base64.b64encode(base64.b64decode(s)) == s.encode('ascii')
        except Exception:
            return False

    @staticmethod
    def is_base64_psbt(s):
        try:
            if DecodeQR.is_base64(s):
                psbt.PSBT.parse(a2b_base64(s))
                return True
        except Exception as e :
            print(e)
            return False
        return False

