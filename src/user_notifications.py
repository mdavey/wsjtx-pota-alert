import logging
import os.path
import subprocess
import time
from functools import cache


logger = logging.getLogger(__name__)


class UserNotifications:
    def __init__(self, time_between_notifications_seconds: int = 180):
        self._time_between_notifications_seconds = time_between_notifications_seconds
        self._audio_filename = None
        self._recent_notifications: dict = {}

    def set_audio_filename(self, filename: str):
        if not os.path.exists(filename):
            logger.error(f"Notification sound not found: {filename}")
        else:
            self._audio_filename = filename

    def notify(self, callsign: str, title: str, message: str):
        show_notification = False

        # Has it a new callsign?
        if callsign not in self._recent_notifications:
            show_notification = True

        # Have we seen it, but at least self._time_between_seconds ago?
        elif time.time() > self._recent_notifications[callsign]+self._time_between_notifications_seconds:
            show_notification = True

        if show_notification:
            logger.info(f"{title} -- {message}")
            self._recent_notifications[callsign] = time.time()  # reset/set time
            self._show_toast_notification(title, message)
            self._play_audio()
        else:
            logger.debug(f"Found POTA activator, but suppressing alert: {callsign}")

    @staticmethod
    def _show_toast_notification(message: str, body: str):
        try:
            subprocess.run(["notify-send", message, body], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"Unable to send notification: {e}")

    def _play_audio(self):
        if self._audio_filename is None:
            return

        try:
            cmd_and_args = self._get_suitable_audio_player()
            if cmd_and_args is not None:
                cmd_and_args.append(self._audio_filename)
                subprocess.Popen(cmd_and_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)
            else:
                logger.error(f"Unable to find program to play notification.  Please install paplay or ffplay, or vorbis-tools for ogg123")
        except Exception as e:
            logger.error(f"Unable to play audio file {self._audio_filename}: {e}")

    @cache
    def _get_suitable_audio_player(self):
        """
        Try and find a suitable audio player.  Try generic stuff first, and pray.
        """
        possible_programs = [
            {"cmd": "ffplay", "full_cmd":["ffplay", "-vn", "-nodisp", "-autoexit"]},
            {"cmd": "paplay", "full_cmd":["paplay"]},
            {"cmd": "ogg123", "full_cmd":["ogg123"]},
        ]
        for program in possible_programs:
            r = subprocess.run(["which", program["cmd"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
            if r.returncode == 0:
                return program["full_cmd"]
        return None