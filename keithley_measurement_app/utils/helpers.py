"""General helper utilities."""

from typing import Iterable


def flatten(list_of_lists: Iterable[Iterable]):
    for item in list_of_lists:
        for value in item:
            yield value
