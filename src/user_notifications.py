import logging
import subprocess
import time


logger = logging.getLogger(__name__)


class UserNotifications:
    def __init__(self, time_between_notifications_seconds: int = 180):
        self._time_between_notifications_seconds = time_between_notifications_seconds
        self._audio_filename = None
        self._recent_notifications: dict = {}

    def set_audio_filename(self, filename: str):
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
            subprocess.run(["notify-send", message, body])
        except Exception as e:
            logger.error(f"Unable to send notification: {e}")

    def _play_audio(self):
        try:
            subprocess.run(["paplay", self._audio_filename])
        except Exception as e:
            logger.error(f"Unable to play audio file {self._audio_filename}: {e}")
