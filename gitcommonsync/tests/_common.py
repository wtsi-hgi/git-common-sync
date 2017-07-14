import hashlib
import os
from typing import Optional

from checksumdir import dirhash
from pip._vendor import requests


def get_md5(location: str, ignore_hidden_files: bool=True) -> Optional[str]:
    """
    Gets an MD5 checksum of the file or directory at the given location.
    :param location: location of file or directory
    :param ignore_hidden_files: whether hidden files should be ignored when calculating an checksum for a directory
    :return: the MD5 checksum or `None` if the given location does not exist
    """
    if not os.path.exists(location):
        return None
    if os.path.isfile(location):
        with open(location, "rb") as file:
            content = file.read()
        return hashlib.md5(content).hexdigest()
    else:
        return dirhash(location, "md5", ignore_hidden=ignore_hidden_files)


def is_accessible(url: str) -> bool:
    """
    Checks if the given URL is accessible.

    This function attempts to get the content at the location - avoid pointing to the location of a huge file!
    :param url: the URL to check
    :return: whether the given URL is accessible
    """
    try:
        return requests.get(url).status_code == requests.codes.ok
    except Exception:
        return False
