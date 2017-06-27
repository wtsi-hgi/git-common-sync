from typing import List


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


class GitCheckout:
    """
    TODO
    """
    def __init__(self, url: str, branch: str, commit: str):
        self.url = url
        self.branch = branch
        self.commit = commit
