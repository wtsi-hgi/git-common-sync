from abc import ABCMeta
from typing import Dict

from gitcommonsync._git import GitCheckout


class Synchronisation(metaclass=ABCMeta):
    """
    TOOD
    """


class SubrepoSynchronisation(Synchronisation):
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

    def __init__(self, checkout: GitCheckout =None, overwrite: bool=False):
        self.checkout = checkout
        self.overwrite = overwrite


# TODO: Extract shared superclass for this and `TemplateSynchronisation`
class FileSynchronisation(Synchronisation):
    """
    File synchronisation configuration.
    """
    def __init__(self, source: str, destination: str, overwrite: bool=False):
        self.source = source
        self.destination = destination
        self.overwrite = overwrite


class TemplateSynchronisation(FileSynchronisation):
    """
    Template synchronisation configuration.
    """
    def __init__(self, source: str, destination: str, variables: Dict[str, str], overwrite: bool=False):
        super().__init__(source, destination, overwrite=overwrite)
        self.variables = variables
