import subprocess
import time
import logging

import dearpygui.dearpygui as dpg

from wsjtx_udp_message_parser import WsjtxUdpMessageDecode
from pota_activator import PotaActivatorRefresherThread
from user_notifications import UserNotifications
from wsjtx_udp_listener import WsjtxUdpListenerThread


# Set up a custom log handler to redirect everything into the UI
class UiLogHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        value = dpg.get_value("log_input_text")
        new_value = log_entry + "\n" + value
        dpg.set_value("log_input_text", new_value)


logger = logging.getLogger() # root
logger.setLevel(logging.DEBUG)
logger_handler = UiLogHandler()
logger_handler.setFormatter(logging.Formatter("%(asctime)s  %(levelname)s  %(message)s", datefmt="%I:%M:%S %P"))
logger.addHandler(logger_handler)


def screen_resolution() -> tuple[int, int]:
    try:
        v = subprocess.run(["xrandr"], capture_output=True, text=True)
        for line in v.stdout.splitlines():
            if "*" in line:
                res = line.strip().split(" ")[0].split("x")
                return int(res[0]), int(res[1])
    except Exception as e:
        logger.error(f"Error running xrandr to get screen resolution: {e}")

    logger.error("Cannot get screen res, assuming 1920x1080")
    return 1920, 1080


# Use this these values to position the window in the center of the screen
APP_WIDTH = 800
APP_HEIGHT = 500
(SCREEN_WIDTH, SCREEN_HEIGHT) = screen_resolution()


# Start the UI
dpg.create_context()

# Setup fonts.   Make default_font the default
with dpg.font_registry():
    # first argument ids the path to the .ttf or .otf file
    default_font = dpg.add_font("../assets/NotoSans-Regular.ttf", 18)
    heading_font = dpg.add_font("../assets/NotoSans-Bold.ttf", 18)

dpg.bind_font(default_font)

# Setup global theme.  Rounded corners for fun, and turn off the window border as there is only a single window
with dpg.theme() as global_theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 8)
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 6)
        dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0)

dpg.bind_theme(global_theme)

# Add second theme.  Used to change the color of text
with dpg.theme() as text_heading_theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Text, (160, 70, 40))

# Now the main window
with dpg.window(tag="Primary Window"):
    dpg.add_text("POTA Spots:")
    dpg.bind_item_font(dpg.last_item(), heading_font)
    dpg.bind_item_theme(dpg.last_item(), text_heading_theme)

    with dpg.group(horizontal=True):
        dpg.add_spacer(width=4)
        dpg.add_text("Last Updated:")
        dpg.add_text("", tag="pota_last_updated_text")

    with dpg.group(horizontal=True):
        dpg.add_spacer(width=4)
        dpg.add_text("Recent Spots:")
        dpg.add_text("", tag="pota_recent_spots_text")

    dpg.add_text("WSJT-X Messages:")
    dpg.bind_item_font(dpg.last_item(), heading_font)
    dpg.bind_item_theme(dpg.last_item(), text_heading_theme)

    with dpg.group(horizontal=True):
        dpg.add_spacer(width=4)
        dpg.add_text("Last Updated:")
        dpg.add_text("", tag="wsjtx_last_updated_text")

    with dpg.group(horizontal=True):
        dpg.add_spacer(width=4)
        dpg.add_text("Total Decodes:")
        dpg.add_text("", tag="wsjtx_total_decodes_text")

    dpg.add_text("Log:")
    dpg.bind_item_font(dpg.last_item(), heading_font)
    dpg.bind_item_theme(dpg.last_item(), text_heading_theme)

    dpg.add_input_text(multiline=True, height=240, readonly=True, width=780, tag="log_input_text")


pota_thread = PotaActivatorRefresherThread("https://api.pota.app/spot/activator", 5, 10)
wsjtx_thread = WsjtxUdpListenerThread()

total_wsjtx_decodes = 0

def on_wsjtx_message_received(msg: WsjtxUdpMessageDecode) -> None:
    global total_wsjtx_decodes
    total_wsjtx_decodes += 1

    dpg.set_value("wsjtx_last_updated_text", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    dpg.set_value("wsjtx_total_decodes_text", f"{total_wsjtx_decodes:,}")

    # If we haven't got a list of POTA spots, just stop
    if pota_thread.get_last_response() is None:
        return

    # If we can't work out the callsign of who set the message, no point going further
    callsign_of_transmitter = msg.get_src_callsign()
    if callsign_of_transmitter is None:
        return

    # Get the activator call signs from the POTA spots, and check against this message
    activator_callsigns = [item["activator"] for item in pota_thread.get_last_response()]

    for callsign in activator_callsigns:
        if callsign == callsign_of_transmitter:
            notifications.notify(callsign, f"Found Activator {callsign}", msg.message)

    # Also just check if the message says is POTA or WWFF without being spotted yet
    if 'CQ POTA' in msg.message or 'CQ WWFF' in msg.message:
        callsign = msg.message[8:]
        notifications.notify(callsign, f"Found Activator {callsign}", msg.message)


def on_new_pota_activators(data):
    logger.info(f"Fetched {len(data)} current active POTA activators")
    dpg.set_value("pota_last_updated_text", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    dpg.set_value("pota_recent_spots_text", str(len(data)))


# Create viewport and set primary window
dpg.create_viewport(title='WSJT-X Pota Alert', width=APP_WIDTH, height=APP_HEIGHT, x_pos=(SCREEN_WIDTH//2)-(APP_WIDTH//2), y_pos=(SCREEN_HEIGHT//2)-(APP_HEIGHT//2))
dpg.set_viewport_resizable(True)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("Primary Window", True)

# Notification System
notifications = UserNotifications()
notifications.set_audio_filename('../assets/message-new-instant.oga')

# WSJT-X Listening
wsjtx_thread.set_callback(on_wsjtx_message_received)
wsjtx_thread.start()

# POTA.app updator
pota_thread.set_callback(on_new_pota_activators)
pota_thread.start()

# Go!
dpg.start_dearpygui()
dpg.destroy_context()

# If dpg is closed, make sure to stop these as well
wsjtx_thread.stop()
pota_thread.stop()