import logging
import os
import shutil
from time import sleep
from typing import List

import gitsubrepo

from gitcommonsync._ansible_runner import run_ansible_task
from gitcommonsync.models import FileSyncConfiguration, SyncConfiguration, SubrepoSyncConfiguration, GitCheckout
from gitcommonsync.repository import GitRepository

_logger = logging.getLogger(__name__)


class Synchronised:
    """
    Changes that happened during the synchronisation.
    """
    def __init__(self):
        self.file_synchronisations: List[FileSyncConfiguration] = None
        self.subrepo_synchronisations: List[SubrepoSyncConfiguration] = None


def synchronise(git_repository: GitRepository, sync_configuration: SyncConfiguration) -> Synchronised:
    """
    Clones, updates and commits to the given repository, according to the given synchronisation configuration.
    :param git_repository: the git repository
    :param sync_configuration: the synchronisation configuration
    :return: TODO
    """
    repository_location = git_repository.checkout()
    changed = Synchronised()
    try:
        changed.file_synchronisations = synchronise_files(repository_location, sync_configuration.files)
        git_repository.push_changes(
            f"Synchronised files from the \"{sync_configuration.name}\" configuration",
            [os.path.join(repository_location, file_synchronisation.destination)
             for file_synchronisation in changed.file_synchronisations])

        changed.subrepo_synchronisations = synchronise_subrepos(git_repository, sync_configuration.subrepos)
        git_repository.push_changes()
    finally:
        git_repository.tear_down()

    return changed


def synchronise_files(repository_location: str, file_sync_configuration: List[FileSyncConfiguration]) \
        -> List[FileSyncConfiguration]:
    """
    Synchronises files in the given repository, according to the given configuration
    :param repository_location: the location of the checked out repository
    :param file_sync_configuration: the file synchronisation configurations
    :return: the file synchronisations applied
    """
    synchronised_files: List[FileSyncConfiguration] = []

    for file_synchronisation in file_sync_configuration:
        destination = os.path.join(repository_location, file_synchronisation.destination)
        target = os.path.join(repository_location, destination)

        if not _is_subdirectory(destination, repository_location):
            raise ValueError(f"Destination {file_synchronisation.destination} not inside of repository "
                             f"({os.path.realpath(target)})")

        exists = os.path.exists(target)
        if exists and not file_synchronisation.overwrite:
            _logger.info(f"{file_synchronisation.source} != {target} (overwrite={file_synchronisation.overwrite})")
            continue
        assert os.path.isabs(file_synchronisation.source)

        intermediate_directories = os.path.dirname(target)
        if not os.path.exists(intermediate_directories):
            _logger.info(f"Creating intermediate directories: {intermediate_directories}")
            os.makedirs(intermediate_directories)

        result = run_ansible_task(dict(
            action=dict(module="copy", args=dict(src=file_synchronisation.source, dest=target))
        ))
        if result.is_failed():
            raise RuntimeError(result._result)
        if result.is_changed():
            synchronised_files.append(file_synchronisation)
            _logger.info(f"{file_synchronisation.source} => {target} (overwrite={file_synchronisation.overwrite})")
        else:
            _logger.info(f"{file_synchronisation.source} == {target}")

    return synchronised_files


def synchronise_subrepos(git_repository: GitRepository, subrepo_sync_configurations: List[SubrepoSyncConfiguration]) \
        -> List[SubrepoSyncConfiguration]:
    """
    TODO
    :param git_repository:
    :param subrepo_sync_configurations:
    :return:
    """
    synchronised_subrepos: List[SubrepoSyncConfiguration] = []

    for subrepo_sync_configuration in subrepo_sync_configurations:
        destination = os.path.join(git_repository.checkout_location, subrepo_sync_configuration.checkout.directory)
        required_checkout = subrepo_sync_configuration.checkout

        if not _is_subdirectory(destination, git_repository.checkout_location):
            raise ValueError(f"Destination {destination} not inside of repository")

        if os.path.exists(destination):
            force_update = False
            url, branch, commit = gitsubrepo.status(destination)
            current_checkout = GitCheckout(url, branch, commit, required_checkout.directory)

            if current_checkout == required_checkout:
                _logger.info(f"Subrepo at {required_checkout.directory} is synchronised")

            elif not subrepo_sync_configuration.overwrite:
                _logger.info(f"Subrepo at {required_checkout.directory} is not synchronised but not updating as "
                             f"overwrite=False")

            elif current_checkout.url == required_checkout.url and current_checkout.branch == required_checkout.branch:
                _logger.debug(f"Pulling subrepo at {required_checkout.directory} in an attempt to sync")
                new_commit = gitsubrepo.pull(destination)
                if new_commit == subrepo_sync_configuration.checkout.commit:
                    _logger.info(f"Subrepo at {required_checkout.directory}: {commit} => {new_commit}")
                    synchronised_subrepos.append(subrepo_sync_configuration)
                else:
                    force_update = True

            else:
                force_update = True

            if force_update:
                message = "Removing subrepo at {required_checkout.directory} to force update"
                _logger.debug(f"Removing subrepo at {required_checkout.directory} to force update")
                shutil.rmtree(destination)
                git_repository.commit_changes(message, [destination])

        if not os.path.exists(destination):
            new_commit = gitsubrepo.clone(required_checkout.url, destination,
                                          branch=required_checkout.branch, commit=required_checkout.commit)
            assert new_commit != required_checkout.commit
            _logger.debug(f"Checked out subrepo: {required_checkout}")
            synchronised_subrepos.append(subrepo_sync_configuration)

    return synchronised_subrepos


def _is_subdirectory(subdirectory: str, directory: str) -> bool:
    """
    TODO
    :param subdirectory: 
    :param directory: 
    :return: 
    """
    return not ".." in os.path.relpath(subdirectory, directory)