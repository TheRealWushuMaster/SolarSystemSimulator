from __future__ import annotations

import requests
import os
import email.utils
from typing import Any
from settings import EPHEMERIS_FILE, EPHEMERIS_URL
from jplephem.spk import SPK


def check_ephemeris_file_update(self: Any) -> None:
    if os.path.exists(EPHEMERIS_FILE):
        current_timestamp: float = os.path.getmtime(EPHEMERIS_FILE)
    else:
        current_timestamp = 0.0
    response = requests.head(EPHEMERIS_URL)
    if 'Last-Modified' in response.headers:
        latest_timestamp_str: str = response.headers['Last-Modified']
    else:
        latest_timestamp_str = "0"
    latest_timestamp = email.utils.mktime_tz(email.utils.parsedate_tz(latest_timestamp_str))
    if current_timestamp < latest_timestamp:
        print("Downloading updated ephemeris file...")
        download_updated_ephemeris(self)
        print("Ephemeris file has been downloaded.")
    else:
        print("Ephemeris file is up to date.")


def download_updated_ephemeris(self: Any) -> None:
    response = requests.get(EPHEMERIS_URL)
    with open(EPHEMERIS_FILE, "wb") as file:
        file.write(response.content)


def load_ephemeris_data(self: Any) -> None:
    self.kernel = SPK.open(EPHEMERIS_FILE)


def close_ephemeris_data(self: Any) -> None:
    self.kernel.close()
