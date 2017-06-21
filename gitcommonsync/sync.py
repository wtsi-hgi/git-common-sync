import logging
import os
import shutil
from typing import Set, List

from gitcommonsync._ansible_runner import run_ansible_task
from gitcommonsync.configuration import SyncConfiguration, FileSyncConfiguration
from gitcommonsync.repository import GitRepository, checkout

_logger = logging.getLogger(__name__)


class Changed:
    """
    TODO
    """
    def __init__(self, files: List[str]=None):
        self.files = files if files is not None else []


def synchronise(git_repository: GitRepository, sync_configuration: SyncConfiguration) -> Changed:
    """
    Clones, updates and commits to the given repository, according to the given synchronisation configuration.
    :param git_repository: the git repository
    :param sync_configuration: the synchronisation configuration
    :return:
    """
    repo_location = checkout(git_repository)
    changed = Changed()
    changed.files = synchronise_files(repo_location, sync_configuration)

    shutil.rmtree(repo_location)

    print(changed.files)
    return changed

def synchronise_files(repo_location: str, sync_configuration: SyncConfiguration) -> List[str]:
    """
    Synchronises files in the given repository, according to the given configuration
    :param repo_location: the location of the checked out repository
    :param sync_configurations: the synchronisation configuration
    :return:
    """
    changed_files: List[str] = []

    for file in sync_configuration.files:
        destination = os.path.join(repo_location, file.destination)
        target = os.path.join(repo_location, destination)

        if ".." in os.path.relpath(destination, repo_location):
            raise ValueError(f"Destination not inside of repository: {target}")

        exists = os.path.exists(target)
        if exists and not file.overwrite:
            _logger.info(f"{file.source} != {target} (overwrite={exists})")
            continue
        assert os.path.isabs(file.source)

        result = run_ansible_task(dict(
            action=dict(module="copy", args=dict(src=file.source, dest=target))
        ))
        if result.is_failed():
            raise RuntimeError(result)
        if result.is_changed():
            changed_files.append(file.source)
            _logger.info(f"{file.source} => {target} (overwrite={exists})")
        else:
            _logger.info(f"{file.source} == {target}")

    return changed_files

