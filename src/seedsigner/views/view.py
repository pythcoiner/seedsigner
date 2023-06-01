from dataclasses import dataclass
from typing import List

from seedsigner.gui.components import FontAwesomeIconConstants, GUIConstants
from seedsigner.gui.screens import RET_CODE__POWER_BUTTON
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, DireWarningScreen, LargeButtonScreen, ButtonListScreen
from seedsigner.gui.screens.screen import PowerOffScreen, PowerOffNotRequiredScreen, ResetScreen, WarningScreen, QRDisplayScreen
from seedsigner.models.threads import BaseThread
from seedsigner.models import Settings
from seedsigner.models import QRType
from seedsigner.models.settings import SettingsConstants
from seedsigner.models.encode_qr import EncodeQR

from embit.networks import NETWORKS
from embit.descriptor import Descriptor
from embit.psbt import OutputScope
from embit.bip32 import HDKey
from embit.psbt import PSBT


class BackStackView:
    """
        Empty class that just signals to the Controller to pop the most recent View off
        the back_stack.
    """
    pass


"""
    Views contain the biz logic to handle discrete tasks, exactly analogous to a Flask
    request/response function or a Django View. Each page/screen displayed to the user
    should be implemented in its own View.

    In a web context, the View would prepare data for the html/css/js presentation
    templates. We have to implement our own presentation layer (implemented as `Screen`
    objects). For the sake of code cleanliness and separation of concerns, the View code
    should not know anything about pixel-level rendering.

    Sequences that require multiple pages/screens should be implemented as a series of
    separate Views. Exceptions can be made for complex interactive sequences, but in
    general, if your View is instantiating multiple Screens, you're probably putting too
    much functionality in that View.

    As with http requests, Views can receive input vars to inform their behavior. Views
    can also prepare the next set of vars to set up the next View that should be
    displayed (akin to Flask's `return redirect(url, param1=x, param2=y))`).

    Navigation guidance:
    "Next" - Continue to next step
    "Done" - End of flow, return to entry point (non-destructive)
    "OK/Close" - Exit current screen (non-destructive)
    "Cancel" - End task and return to entry point (destructive)
"""
class View:
    def __init__(self) -> None:
        # Import here to avoid circular imports
        from seedsigner.controller import Controller
        from seedsigner.gui import Renderer
        from seedsigner.models import Settings

        self.controller: Controller = Controller.get_instance()
        self.settings = Settings.get_instance()

        # TODO: Pull all rendering-related code out of Views and into gui.screens implementations
        self.renderer = Renderer.get_instance()
        self.canvas_width = self.renderer.canvas_width
        self.canvas_height = self.renderer.canvas_height

        self.buttons = self.controller.buttons


    def run(self, **kwargs):
        if hasattr(self, "screen"):
            self.screen.display()
        else:
            raise Exception("Must implement in the child class")



@dataclass
class Destination:
    """
        Basic struct to pass back to the Controller to tell it which View the user should
        be presented with next.
    """
    View_cls: View                  # The target View to route to
    view_args: dict = None          # The input args required to instantiate the target View
    skip_current_view: bool = False  # The current View is just forwarding; omit current View from history
    clear_history: bool = False     # Optionally clears the back_stack to prevent "back"


    def __repr__(self):
        if self.View_cls is None:
            out = "None"
        else:
            out = self.View_cls.__name__
        if self.view_args:
            out += f"({self.view_args})"
        else:
            out += "()"
        if self.clear_history:
            out += f" | clear_history: {self.clear_history}"
        return out


    def run(self):
        if not self.view_args:
            # Can't unpack (**) None so we replace with an empty dict
            self.view_args = {}
        # Instantiate the `View_cls` and run() it with the `view_args` dict
        return self.View_cls(**self.view_args).run()


    def __eq__(self, obj):
        """
            Equality test IGNORES the skip_current_view and clear_history options
        """
        return (isinstance(obj, Destination) and 
            obj.View_cls == self.View_cls and
            obj.view_args == self.view_args)
    

    def __ne__(self, obj):
        return not obj == self


#########################################################################################
#
# Root level Views don't have a sub-module home so they live at the top level here.
#
#########################################################################################
class MainMenuView(View):
    def run(self) -> Destination:
        # from .seed_views import SeedsMenuView
        # from .settings_views import SettingsMenuView
        from .scan_views import ScanView
        # from .tools_views import ToolsMenuView
        from seedsigner.gui.screens import LargeButtonScreen
        menu_items = [
            (("PSBT", FontAwesomeIconConstants.QRCODE), ScanView),
            (("Descriptor", FontAwesomeIconConstants.QRCODE), ScanView),
            # (("Seeds", FontAwesomeIconConstants.KEY), SeedsMenuView),
            # (("Tools", FontAwesomeIconConstants.SCREWDRIVER_WRENCH), ToolsMenuView),
            # (("Settings", FontAwesomeIconConstants.GEAR), SettingsMenuView),
        ]

        screen = LargeButtonScreen(
            title="Home",
            title_font_size=26,
            button_data=[entry[0] for entry in menu_items],
            show_back_button=False,
            show_power_button=False,
        )
        selected_menu_num = screen.display()

        if selected_menu_num == RET_CODE__POWER_BUTTON:
            return Destination(PowerOptionsView)

        return Destination(menu_items[selected_menu_num][1])


class HomeView(View):
    def run(self) -> Destination:

        from .scan_views import ScanView
        from seedsigner.gui.screens import LargeButtonScreen
        menu_items = [
            (("PSBT", FontAwesomeIconConstants.QRCODE), PSBTScanView, QRType.PSBT__BASE64),
            (("Descriptor", FontAwesomeIconConstants.QRCODE), ScanView, QRType.DESCRIPTOR),
        ]

        screen = LargeButtonScreen(
            title="Home",
            title_font_size=26,
            button_data=[entry[0] for entry in menu_items],
            show_back_button=False,
            show_power_button=False,
        )
        selected_menu_num = screen.display()

        self.controller.scan_target = menu_items[selected_menu_num][2]

        return Destination(menu_items[selected_menu_num][1])

class PSBTCheckView(View):
    def run(self) -> Destination:

        from .scan_views import ScanView
        from seedsigner.gui.screens import ButtonListScreen

        tx = self.controller.psbt
        menu_items = []
        descriptor: Descriptor = self.controller.descriptor

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
        for out in tx.outputs: # type: OutScope
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
            (("Cancel ", FontAwesomeIconConstants.QRCODE), HomeView),
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

                # if menu_items[selected_menu_num][2] == 'sign':
                #     print('---- Sign tx ----')
                #     tx = self.controller.psbt
                #     print(tx)
                #     signed = tx.sign_with(self.controller.root_key)
                #     print(signed)
                #     print(tx)

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
        menu_items.append((("Cancel", None), HomeView, False))

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
        return Destination(HomeView, clear_history=True)





# class PowerOptionsView(View):
#     def run(self):
#         RESET = ("Restart", FontAwesomeIconConstants.ROTATE_RIGHT)
#         POWER_OFF = ("Power Off", FontAwesomeIconConstants.POWER_OFF)
#         button_data = [RESET, POWER_OFF]
#         selected_menu_num = LargeButtonScreen(
#             title="Reset / Power",
#             show_back_button=True,
#             button_data=button_data
#         ).display()
#
#         if selected_menu_num == RET_CODE__BACK_BUTTON:
#             return Destination(BackStackView)
#
#         elif button_data[selected_menu_num] == RESET:
#             return Destination(RestartView)
#
#         elif button_data[selected_menu_num] == POWER_OFF:
#             return Destination(PowerOffView)
#
#
#
# class RestartView(View):
#     def run(self):
#         thread = RestartView.DoResetThread()
#         thread.start()
#         ResetScreen().display()
#
#
#     class DoResetThread(BaseThread):
#         def run(self):
#             import time
#             from subprocess import call
#
#             # Give the screen just enough time to display the reset message before
#             # exiting.
#             time.sleep(0.25)
#
#             # Kill the SeedSigner process; Running the process again.
#             # `.*` is a wildcard to detect either `python`` or `python3`.
#             if Settings.HOSTNAME == Settings.SEEDSIGNER_OS:
#                 call("kill $(pidof python*) & python /opt/src/main.py", shell=True)
#             else:
#                 call("kill $(ps aux | grep '[p]ython.*main.py' | awk '{print $2}')", shell=True)
#
#
#
# class PowerOffView(View):
#     def run(self):
#         if Settings.HOSTNAME == Settings.SEEDSIGNER_OS:
#             PowerOffNotRequiredScreen().display()
#             return Destination(BackStackView)
#         else:
#             thread = PowerOffView.PowerOffThread()
#             thread.start()
#             PowerOffScreen().display()
#
#
#     class PowerOffThread(BaseThread):
#         def run(self):
#             import time
#             from subprocess import call
#             while self.keep_running:
#                 time.sleep(5)
#                 call("sudo shutdown --poweroff now", shell=True)



class NotYetImplementedView(View):
    """
        Temporary View to use during dev.
    """
    def run(self):
        WarningScreen(
            title="Work In Progress",
            status_headline="Not Yet Implemented",
            text="This is still on our to-do list!",
            button_data=["Back to Main Menu"],
        ).display()

        return Destination(MainMenuView)



class UnhandledExceptionView(View):
    def __init__(self, error: List[str]):
        self.error = error


    def run(self):
        DireWarningScreen(
            title="System Error",
            status_headline=self.error[0],
            text=self.error[1] + "\n" + self.error[2],
            button_data=["OK"],
            show_back_button=False,
            allow_text_overflow=True,  # Fit what we can, let the rest go off the edges
        ).display()
        
        return Destination(MainMenuView, clear_history=True)
