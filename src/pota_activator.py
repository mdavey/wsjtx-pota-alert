import json
import logging
import threading
import time
import urllib
import urllib.request
from typing import Callable


logger = logging.getLogger(__name__)


class PotaActivatorRefresherThread:
    def __init__(self, spot_url: str, update_frequency_min: int = 5, url_fetch_timeout_sec: int = 5):
        self._spot_url = spot_url
        self._update_frequency_min = update_frequency_min
        self._url_fetch_timeout_sec = url_fetch_timeout_sec
        self._json_data = None
        self._callback = None
        self._thread = None
        self._stop_event = threading.Event()

    def set_callback(self, callback: Callable[[dict], None]):
        self._callback = callback

    def start(self):
        self._thread = threading.Thread(target=self._thread_entry)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join()

    def get_last_response(self):
        return self._json_data

    def _thread_entry(self):
        logger.info(f"Checking for updates from {self._spot_url} (every {self._update_frequency_min} minutes)")

        while not self._stop_event.is_set():
            try:
                logger.info(f"Fetching lastest spots from {self._spot_url}")
                with urllib.request.urlopen(self._spot_url, timeout=self._url_fetch_timeout_sec) as response:
                    content = response.read().decode('utf-8')
                    self._json_data = json.loads(content)
                    self._callback(self._json_data)
            except Exception as e:
                logger.warning(f"Error fetching URL: {e}")

            # wait x-minutes checking to see if thread should exit every second
            waiting = self._update_frequency_min * 600
            while waiting > 0:
                time.sleep(0.100)
                waiting -= 1
                if self._stop_event.is_set():
                    break
