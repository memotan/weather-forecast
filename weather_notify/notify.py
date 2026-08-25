import time

import requests


def send_ntfy(
    server: str,
    topic: str,
    title: str,
    message: str,
    priority: str = "default",
    tags: str = "partly_sunny",
    retries: int = 3,
    backoff: float = 2.0,
) -> None:
    url = f"{server.rstrip('/')}/{topic}"
    headers = {
        # ntfy requires non-ASCII header values to be sent as raw UTF-8 bytes.
        "Title": title.encode("utf-8"),
        "Priority": priority,
        "Tags": tags,
    }
    data = message.encode("utf-8")

    last_error = None
    for attempt in range(retries):
        try:
            response = requests.post(url, data=data, headers=headers, timeout=20)
            response.raise_for_status()
            return
        except requests.exceptions.RequestException as error:
            last_error = error
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
    raise last_error
