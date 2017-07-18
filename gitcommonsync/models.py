from abc import ABCMeta
from typing import List, Dict

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

#
# class MultiSynchronisation(Synchronisation):
#     """
#     All synchronisation configurations.
#     """
#     def __init__(self, files: List[FileSynchronisation]=None, subrepos: List[SubrepoSynchronisation]=None,
#                  templates: List[TemplateSynchronisation]=None):
#         self.files = files if files is not None else []
#         self.subrepos = subrepos if subrepos is not None else []
#         self.templates = templates if templates is not None else []
#
#     def get_number_of_synchronisations(self) -> int:
#         """
#         TODO
#         :return:
#         """
#         return len(self.files) + len(self.subrepos) + len(self.templates)
#
