import time

import requests


def get_json(url: str, params: dict = None, timeout: int = 30, retries: int = 3, backoff: float = 2.0) -> dict:
    """GET a URL and return its JSON body, retrying on transient network errors."""
    last_error = None
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as error:
            last_error = error
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
    raise last_error
