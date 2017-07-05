import logging
import os
import shutil
from typing import List

import gitsubrepo

from gitcommonsync._ansible_runner import run_ansible_task
from gitcommonsync._common import is_subdirectory
from gitcommonsync.models import FileSyncConfiguration, SyncConfiguration, SubrepoSyncConfiguration, GitCheckout
from gitcommonsync._repository import GitRepository

_logger = logging.getLogger(__name__)


class Synchronised:
    """
    Changes that happened during the synchronisation.
    """
    def __init__(self):
        self.file_synchronisations: List[FileSyncConfiguration] = None
        self.subrepo_synchronisations: List[SubrepoSyncConfiguration] = None


def synchronise(repository: GitRepository, sync_configuration: SyncConfiguration) -> Synchronised:
    """
    Clones, updates and commits to the given repository, according to the given synchronisation configuration.
    :param repository: the git repository
    :param sync_configuration: the synchronisation configuration
    :return: TODO
    """
    repository.checkout()
    changed = Synchronised()
    try:
        changed.file_synchronisations = synchronise_files(repository, sync_configuration.files)
        changed.subrepo_synchronisations = synchronise_subrepos(repository, sync_configuration.subrepos)
    finally:
        repository.tear_down()

    return changed


def synchronise_files(repository: GitRepository, configurations: List[FileSyncConfiguration]) \
        -> List[FileSyncConfiguration]:
    """
    Synchronises files in the given repository, according to the given configuration
    :param repository: the location of the checked out repository
    :param configurations: the file synchronisation configurations
    :return: the file synchronisations applied
    """
    synchronised: List[FileSyncConfiguration] = []

    for configuration in configurations:
        if not os.path.exists(configuration.source):
            raise FileNotFoundError(configuration.source)

        destination = os.path.join(repository.checkout_location, configuration.destination)
        target = os.path.join(repository.checkout_location, destination)

        if not is_subdirectory(destination, repository.checkout_location):
            raise ValueError(f"Destination {configuration.destination} not inside of repository "
                             f"({os.path.realpath(target)})")

        exists = os.path.exists(target)
        if exists and not configuration.overwrite:
            _logger.info(f"{configuration.source} != {target} (overwrite={configuration.overwrite})")
            continue
        assert os.path.isabs(configuration.source)

        intermediate_directories = os.path.dirname(target)
        if not os.path.exists(intermediate_directories):
            _logger.info(f"Creating intermediate directories: {intermediate_directories}")
            os.makedirs(intermediate_directories)

        result = run_ansible_task(dict(
            action=dict(module="synchronize", args=dict(
                src=configuration.source, dest=target, recursive=True, delete=True)
            )
        ))
        if result.is_failed():
            raise RuntimeError(result._result)
        if result.is_changed():
            synchronised.append(configuration)
            _logger.info(f"{configuration.source} => {target} (overwrite={configuration.overwrite})")
        else:
            _logger.info(f"{configuration.source} == {target}")

    repository.push_changes(
        f"Synchronised {len(synchronised)} file{'' if len(synchronised) == 1 else ''}",
        [os.path.join(repository.checkout_location, file_synchronisation.destination)
         for file_synchronisation in synchronised])

    return synchronised


def synchronise_subrepos(repository: GitRepository, configurations: List[SubrepoSyncConfiguration]) \
        -> List[SubrepoSyncConfiguration]:
    """
    TODO
    :param repository:
    :param configurations:
    :return:
    """
    synchronised: List[SubrepoSyncConfiguration] = []

    for configuration in configurations:
        destination = os.path.join(repository.checkout_location, configuration.checkout.directory)
        required_checkout = configuration.checkout

        if not is_subdirectory(destination, repository.checkout_location):
            raise ValueError(f"Destination {destination} not inside of repository")

        if os.path.exists(destination):
            force_update = False
            url, branch, commit = gitsubrepo.status(destination)
            if required_checkout.commit is None:
                commit = None
            current_checkout = GitCheckout(url, branch, commit, required_checkout.directory)

            if current_checkout == required_checkout:
                _logger.info(f"Subrepo at {required_checkout.directory} is synchronised")

            elif not configuration.overwrite:
                _logger.info(f"Subrepo at {required_checkout.directory} is not synchronised but not updating as "
                             f"overwrite=False")

            elif current_checkout.url == required_checkout.url and current_checkout.branch == required_checkout.branch:
                _logger.debug(f"Pulling subrepo at {required_checkout.directory} in an attempt to sync")
                new_commit = gitsubrepo.pull(destination)
                if new_commit == required_checkout.commit or required_checkout is None:
                    _logger.info(f"Subrepo at {required_checkout.directory}: {commit} => {new_commit}")
                    synchronised.append(configuration)
                else:
                    force_update = True

            else:
                force_update = True

            if force_update:
                message = f"Removing subrepo at {required_checkout.directory} to force update"
                _logger.debug(message)
                shutil.rmtree(destination)
                repository.commit_changes(message, [destination])

        if not os.path.exists(destination):
            new_commit = gitsubrepo.clone(required_checkout.url, destination,
                                          branch=required_checkout.branch, commit=required_checkout.commit)
            assert new_commit != required_checkout.commit
            _logger.debug(f"Checked out subrepo: {required_checkout}")
            synchronised.append(configuration)

    repository.push_changes()

    return synchronised
