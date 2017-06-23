from typing import List


class SubRepoSyncConfiguration:
    """
    TODO
    """
    def __init__(self, remote: str, branch: str, overwrite: bool=False):
        self.remote = remote
        self.branch = branch
        self.overwrite = overwrite


class FileSyncConfiguration:
    """
    TODO
    """
    def __init__(self, source: str, destination: str, overwrite: bool=False):
        self.source = source
        self.destination = destination
        self.overwrite = overwrite


class SyncConfiguration:
    """
    TODO
    """
    def __init__(self, name: str=None, files_directory: str=None, files: List[FileSyncConfiguration]=None,
                 subrepos: List[SubRepoSyncConfiguration]=None):
        self.name = name
        self.files_directory = files_directory
        self.files = files if files is not None else []
        self.subrepos = subrepos if subrepos is not None else []
