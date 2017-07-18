from typing import List, Any, Set, Dict


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
    @property
    def destination(self) -> str:
        """
        TODO
        :return:
        """
        return self.checkout.directory

    def __init__(self, checkout: GitCheckout=None, overwrite: bool=False):
        self.checkout = checkout
        self.overwrite = overwrite


# TODO: Extract shared superclass for this and `TemplateSyncConfiguration`
class FileSyncConfiguration:
    """
    File synchronisation configuration.
    """
    def __init__(self, source: str, destination: str, overwrite: bool=False):
        self.source = source
        self.destination = destination
        self.overwrite = overwrite


class TemplateSyncConfiguration(FileSyncConfiguration):
    """
    Template synchronisation configuration.
    """
    def __init__(self, source: str, destination: str, variables: Dict[str, str], overwrite: bool=False):
        super().__init__(source, destination, overwrite=overwrite)
        self.variables = variables


class SyncConfiguration:
    """
    All synchronisation configurations.
    """
    def __init__(self, files: List[FileSyncConfiguration]=None, subrepos: List[SubrepoSyncConfiguration]=None,
                 templates: List[TemplateSyncConfiguration]=None):
        self.files = files if files is not None else []
        self.subrepos = subrepos if subrepos is not None else []
        self.templates = templates if templates is not None else []

    def get_number_of_synchronisations(self) -> int:
        """
        TODO
        :return:
        """
        return len(self.files) + len(self.subrepos) + len(self.templates)

