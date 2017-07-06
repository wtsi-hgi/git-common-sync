from typing import List, Any


class GitCheckout:
    """
    Git checkout.
    """
    def __init__(self, url: str, branch: str, directory: str, *, commit: str=None):
        self.url = url
        self.branch = branch
        self.directory = directory
        self.commit = commit

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, type(self)) \
               and other.url == self.url \
               and other.branch == self.branch \
               and other.commit == self.commit \
               and other.directory == self.directory


class SubrepoSyncConfiguration:
    """
    Sub-repo synchronisation configuration.
    """
    def __init__(self, checkout: GitCheckout=None, overwrite: bool=False):
        self.checkout = checkout
        self.overwrite = overwrite


class FileSyncConfiguration:
    """
    File synchronisation configuration.
    """
    def __init__(self, source: str, destination: str, overwrite: bool=False):
        self.source = source
        self.destination = destination
        self.overwrite = overwrite


class SyncConfiguration:
    """
    All synchronisation configurations.
    """
    def __init__(self, name: str=None, files: List[FileSyncConfiguration]=None,
                 subrepos: List[SubrepoSyncConfiguration]=None):
        self.name = name
        self.files = files if files is not None else []
        self.subrepos = subrepos if subrepos is not None else []

