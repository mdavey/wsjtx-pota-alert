import sys
import time
import logging


from wsjtx_udp_message_parser import WsjtxUdpMessageDecode
from pota_activator import PotaActivatorRefresherThread
from user_notifications import UserNotifications
from wsjtx_udp_listener import WsjtxUdpListenerThread


logger = logging.getLogger() # root
logger.setLevel(logging.DEBUG)
logger_handler = logging.StreamHandler(sys.stdout)
logger_handler.setFormatter(logging.Formatter('%(asctime)s  %(levelname)s  %(message)s', datefmt='%Y-%d-%m %I:%M:%S %p'))
logger.addHandler(logger_handler)



if __name__ == "__main__":

    notifications = UserNotifications()
    notifications.set_audio_filename('/usr/share/sounds/freedesktop/stereo/message-new-instant.oga')

    wsjtx_thread = WsjtxUdpListenerThread()
    pota_thread  = PotaActivatorRefresherThread("https://api.pota.app/spot/activator", 5, 10)

    def on_wsjtx_message_received(msg: WsjtxUdpMessageDecode) -> None:
        if pota_thread.get_last_response() is None:
            return

        # If we can't work out the callsign of who set the message, no point going further
        callsign_of_transmitter = msg.get_src_callsign()
        if callsign_of_transmitter is None:
            return

        # just the callsigns for now
        activator_callsigns = [item["activator"] for item in pota_thread.get_last_response()]

        for callsign in activator_callsigns:
            if callsign == callsign_of_transmitter:
                notifications.notify(callsign, f"Found Activator {callsign}", msg.message)

        if 'CQ POTA' in msg.message or 'CQ WWFF' in msg.message:
            callsign = msg.message[8:]
            notifications.notify(callsign, f"Found Activator {callsign}", msg.message)


    def on_new_pota_activators(data):
        logger.info(f"Fetched {len(data)} current active pota activators")


    wsjtx_thread.set_callback(on_wsjtx_message_received)
    pota_thread.set_callback(on_new_pota_activators)

    wsjtx_thread.start()
    pota_thread.start()

    running = True
    while running:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Quiting...")
            wsjtx_thread.stop()
            pota_thread.stop()
            running = False
