import requests


def send_ntfy(
    server: str,
    topic: str,
    title: str,
    message: str,
    priority: str = "default",
    tags: str = "partly_sunny",
) -> None:
    url = f"{server.rstrip('/')}/{topic}"
    headers = {
        # ntfy requires non-ASCII header values to be sent as raw UTF-8 bytes.
        "Title": title.encode("utf-8"),
        "Priority": priority,
        "Tags": tags,
    }
    response = requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=20)
    response.raise_for_status()
