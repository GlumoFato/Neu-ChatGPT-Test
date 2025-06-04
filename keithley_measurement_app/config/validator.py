"""Input validation helpers."""

import re

IP_PATTERN = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")


def is_valid_ip(value: str) -> bool:
    return bool(IP_PATTERN.match(value))
