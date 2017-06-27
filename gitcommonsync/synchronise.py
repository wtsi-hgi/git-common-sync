import logging
import os
import shutil
from time import sleep
from typing import List

from gitcommonsync._ansible_runner import run_ansible_task
from gitcommonsync.models import FileSyncConfiguration, SyncConfiguration, SubrepoSyncConfiguration
from gitcommonsync.repository import GitRepository

_logger = logging.getLogger(__name__)


class Synchronised:
    """
    Changes that happened during the synchronisation.
    """
    def __init__(self, synchronised_: List[FileSyncConfiguration]=None):
        self.file_synchronisations = synchronised_ if synchronised_ is not None else []


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
        changed.file_synchronisations = synchronise_files(repository_location, sync_configuration.files_directory)

        commit_message = f"Synchronised files from the \"{sync_configuration.name}\" configuration"
        git_repository.push_changes(commit_message, [os.path.join(repository_location, file_synchronisation.destination)
                                                     for file_synchronisation in changed.file_synchronisations])
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

        if ".." in os.path.relpath(destination, repository_location):
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


def synchronise_subrepos(repository_location: str, subrepo_sync_configurations: List[SubrepoSyncConfiguration]) \
        -> List[SubrepoSyncConfiguration]:
    """
    TODO
    :param repository_location:
    :param subrepo_sync_configurations:
    :return:
    """
    synchronised_subrepos: List[SubrepoSyncConfiguration] = []

    for subrepo_sync_configuration in subrepo_sync_configurations:
        destination = os.path.join(repository_location, subrepo_sync_configuration.destination)

        if ".." in os.path.relpath(destination, repository_location):
            raise ValueError(f"Destination {destination} not inside of repository")

        if os.path.exists(destination):
            pass




    return synchronised_subrepos


