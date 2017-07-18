import logging
import os
import shutil
from abc import ABCMeta, abstractmethod
from tempfile import TemporaryDirectory
from typing import List, Dict, Callable, Type, TypeVar, Generic, Tuple

import gitsubrepo
from git import Repo

from gitcommonsync._ansible_runner import ANSIBLE_RSYNC_MODULE_NAME, ANSIBLE_TEMPLATE_MODULE_NAME, \
    run_ansible
from gitcommonsync._common import is_subdirectory, get_head_commit
from gitcommonsync._repository import GitRepository
from gitcommonsync.models import FileSyncConfiguration, SyncConfiguration, SubrepoSyncConfiguration, GitCheckout, \
    TemplateSyncConfiguration

_logger = logging.getLogger(__name__)

Synchronisable = TypeVar("Synchronisable", bound=SyncConfiguration)
FileBasedSynchronisable = TypeVar("FileBasedSynchronisable", bound=FileSyncConfiguration)


# # FIXME: This is ~the same model as `SyncConfiguration`
# class Synchronised:
#     """
#     Changes that happened during the synchronisation.
#     """
#     def __init__(self):
#         self.file_synchronisations: List[FileSyncConfiguration] = None
#         self.subrepo_synchronisations: List[SubrepoSyncConfiguration] = None
#         self.template_synchronisations: List[TemplateSyncConfiguration] = None
#
#     def get_number_of_synchronisations(self) -> int:
#         """
#         TODO
#         :return:
#         """
#         return len(self.file_synchronisations) + len(self.subrepo_synchronisations) \
#                + len(self.template_synchronisations)



# def synchronise(repository: GitRepository, configuration: SyncConfiguration, dry_run: bool=False) \
#         -> Synchronised:
#     """
#     Clones, updates and commits to the given repository, according to the given synchronisation configuration.
#     :param repository: the git repository
#     :param configuration: the synchronisation configuration
#     :param dry_run: does not push changes back if set to True
#     :return: the synchronisations applied
#     """
#     repository.checkout()
#     changed = Synchronised()
#     try:
#         changed.subrepo_synchronisations = synchronise_subrepos(repository, configuration.subrepos, dry_run=dry_run)
#         changed.file_synchronisations = synchronise_files(repository, configuration.files, dry_run=dry_run)
#         changed.template_synchronisations = synchronise_templates(repository, configuration.templates, dry_run=dry_run)
#     finally:
#         repository.tear_down()
#     return changed
#




class Synchroniser(Generic[Synchronisable], metaclass=ABCMeta):
    """
    TODO
    """
    @abstractmethod
    def _synchronise(self, configuration: Synchronisable) -> Tuple[bool, str]:
        """
        TODO
        :param configuration:
        :return:
        """

    def __init__(self, repository: GitRepository):
        """
        TODO
        :param repository:
        :param dry_run:
        """
        self.repository = repository

    def synchronise(self, configurations: List[Synchronisable], dry_run: bool=False) -> List[Synchronisable]:
        """
        TODO
        :return:
        """
        synchronised: List[Synchronisable] = []
        for configuration in configurations:
            self._prepare_for_synchronise(configuration)
            was_synchronised, reason = self._synchronise(configuration)
            # TODO: Do something useful with the reasons
            if was_synchronised:
                synchronised.append(configuration)

        if len(synchronised) > 0 and not dry_run:
            self.repository.push()

        return synchronised

    def _prepare_for_synchronise(self, configuration: Synchronisable):
        """
        TODO
        :param configuration:
        :return:
        """
        destination = os.path.join(self.repository.checkout_location, configuration.destination)
        target = os.path.join(self.repository.checkout_location, destination)

        if not is_subdirectory(destination, self.repository.checkout_location):
            raise ValueError(f"Destination {configuration.destination} not inside of repository "
                             f"({os.path.realpath(target)})")

        intermediate_directories = os.path.dirname(target)
        if not os.path.exists(intermediate_directories):
            _logger.info(f"Creating intermediate directories: {intermediate_directories}")
            os.makedirs(intermediate_directories)


class SubrepoSynchroniser(Synchroniser[SubrepoSyncConfiguration]):
    """
    TODO
    """
    def _synchronise(self, configuration: SubrepoSyncConfiguration) -> Tuple[bool, str]:
        destination = os.path.join(self.repository.checkout_location, configuration.destination)
        required_checkout = configuration.checkout
        force_update = False

        if os.path.exists(destination):
            url, branch, commit = gitsubrepo.status(destination)
            current_checkout = GitCheckout(url, branch, required_checkout.directory, commit=commit)
            same_url_and_branch = current_checkout.url == required_checkout.url \
                                  and current_checkout.branch == required_checkout.branch

            if required_checkout.commit is None and same_url_and_branch:
                required_checkout.commit = get_head_commit(url, branch)

            if current_checkout == required_checkout:
                return False, f"Subrepo at {required_checkout.directory} is synchronised"
            elif not configuration.overwrite:
                return False, f"Subrepo at {required_checkout.directory} is not synchronised but not updating as " \
                              f"overwrite=False"
            elif same_url_and_branch:
                _logger.debug(f"Pulling subrepo at {required_checkout.directory} in an attempt to sync")
                # TODO: We could check whether the remote's head is the commit we want before doing this as it might not
                # pull to the correct commit
                new_commit = gitsubrepo.pull(destination)
                if new_commit == required_checkout.commit:
                    return True, f"Subrepo at {required_checkout.directory}: {commit} => {new_commit}"
                else:
                    force_update = True
            else:
                force_update = True

            if force_update:
                message = f"Removing subrepo at {required_checkout.directory} to force update"
                _logger.debug(message)
                shutil.rmtree(destination)
                self.repository.commit(message, [destination])

        assert not os.path.exists(destination)
        new_commit = gitsubrepo.clone(required_checkout.url, destination,
                                      branch=required_checkout.branch, commit=required_checkout.commit)
        assert new_commit != required_checkout.commit
        return True, f"Checked out subrepo: {required_checkout} (forced updated={force_update})"


class FileBasedSynchroniser(Generic[FileBasedSynchronisable], Synchroniser[FileBasedSynchronisable], metaclass=ABCMeta):
    """
    TODO
    """
    @abstractmethod
    def _synchronise_file(self, configuration: FileSyncConfiguration) -> Tuple[bool, str]:
        """
        Synchronises a file as defined by the given configuration.
        :param configuration: the synchronisation configuration
        :return: tuple whether the first element is a boolean that indicates if the file was synchronised and the second
        is a human readable string detailing the reason for the choice to synchronise or not
        """

    def _prepare_for_synchronise(self, configuration: FileSyncConfiguration):
        if not os.path.exists(configuration.source):
            raise FileNotFoundError(configuration.source)
        if not os.path.isabs(configuration.source):
            raise ValueError(f"Sources cannot be relative: {configuration.source}")
        return super()._prepare_for_synchronise(configuration)

    def _synchronise(self, configuration: FileSyncConfiguration) -> Tuple[bool, str]:
        destination = os.path.join(self.repository.checkout_location, configuration.destination)
        target = os.path.join(self.repository.checkout_location, destination)

        if os.path.exists(target) and not configuration.overwrite:
            return False, f"{configuration.source} != {target} (overwrite={configuration.overwrite})"

        was_synchronised, reason = self._synchronise_file(configuration)
        if was_synchronised:
            self.repository.commit(f"Synchronised {configuration.source}.", )

        return was_synchronised, reason


class _AnsibleFileBasedSynchroniser(Generic[Synchronisable], FileBasedSynchroniser[Synchronisable], metaclass=ABCMeta):
    """
    TODO
    """
    def __init__(
            self, repository: GitRepository,
            ansible_action_generator: Callable[[FileSyncConfiguration, str], Dict],
            ansible_variables_generator: Callable[[FileSyncConfiguration], Dict[str, str]]=lambda configuration: {}):
        """
        Constructor.
        :param repository: see `Synchroniser.__init__`
        :param ansible_action_generator: generator of the action which Ansible is to perform in the form of a dictionary
        that the Ansible library can use. The first argument given is the synchronisation configuration and the second
        is the synchronisation target location
        :param ansible_variables_generator: generator of variables to be passed to Ansible, where the argument given is
        the synchronisation configuration and the return is dictionary where keys are variable names and values of the
        variable values
        """
        super().__init__(repository)
        self.ansible_action_generator = ansible_action_generator
        self.ansible_variables_generator = ansible_variables_generator

    def _synchronise_file(self, configuration: FileSyncConfiguration) -> Tuple[bool, str]:
        destination = os.path.join(self.repository.checkout_location, configuration.destination)
        target = os.path.join(self.repository.checkout_location, destination)

        results = run_ansible(tasks=[dict(action=self.ansible_action_generator(configuration, target))],
                              variables=self.ansible_variables_generator(configuration))
        assert len(results) <= 1
        if results[0].is_failed():
            raise RuntimeError(results[0]._result)
        if results[0].is_changed():
            return True, f"{configuration.source} => {target} (overwrite={configuration.overwrite})"
        else:
            return False, f"{configuration.source} == {target}"


class FileSynchroniser(_AnsibleFileBasedSynchroniser[FileSyncConfiguration]):
    """
    TODO
    """
    _ANSIBLE_ACTION_GENERATOR = lambda configuration, target: dict(
        module=ANSIBLE_RSYNC_MODULE_NAME,
        args=dict(src=configuration.source, dest=target, recursive=True, delete=True, archive=False, perms=True,
                  links=True, checksum=True)
    )

    def __init__(self, repository: GitRepository):
        super().__init__(repository, FileSynchroniser._ANSIBLE_ACTION_GENERATOR)


class TemplateSynchroniser(_AnsibleFileBasedSynchroniser[TemplateSyncConfiguration]):
    """
    TODO
    """
    _ANSIBLE_ACTION_GENERATOR = lambda configuration, target: dict(module=ANSIBLE_TEMPLATE_MODULE_NAME,
                                                                   args=dict(src=configuration.source, dest=target))
    _ANSIBLE_VARIABLES_GENERATOR = lambda configuration: configuration.variables

    def __init__(self, repository: GitRepository):
        super().__init__(repository, TemplateSynchroniser._ANSIBLE_ACTION_GENERATOR,
                         TemplateSynchroniser._ANSIBLE_VARIABLES_GENERATOR)
