import os
from typing import NamedTuple, List

import yaml


FILES_DIRECTORY_KEY = "files-directory"
FILES_KEY = "files"
FILES_SRC_KEY = "src"
FILES_DEST_KEY = "dest"
FILES_OVERWRITE_KEY = "overwrite"
SUBREPOS_KEY = "subrepos"
SUBREPOS_BRANCH_KEY = "branch"
SUBREPOS_REMOTE_KEY = "remote"
SUBREPOS_OVERWRITE_KEY = "overwrite"


class SubRepoSyncConfiguration:
    """
    TODO
    """
    def __init__(self, remote: str, branch: str, overwrite: bool = False):
        self.remote = remote
        self.branch = branch
        self.overwrite = overwrite


class FileSyncConfiguration:
    """
    TODO
    """
    def __init__(self, source: str, destination: str, overwrite: bool = False):
        self.source = source
        self.destination = destination
        self.overwrite = overwrite


class SyncConfiguration:
    """
    TODO
    """
    def __init__(self, files_directory: str=None, files: List[FileSyncConfiguration]=None,
                 subrepos: List[SubRepoSyncConfiguration]=None):
        self.files_directory = files_directory
        self.files = files if files is not None else []
        self.subrepos = subrepos if subrepos is not None else []


def load(configuration_location: str) -> SyncConfiguration:
    """
    TODO
    :param configuration_location:
    :return:
    """
    with open(configuration_location, "r") as file:
        configuration_as_yml = yaml.load(file)
    configuration = SyncConfiguration()
    configuration.files_directory = configuration_as_yml[FILES_DIRECTORY_KEY] \
        if FILES_DIRECTORY_KEY in configuration_as_yml else None
    if configuration.files_directory is not None and not os.path.isabs(configuration.files_directory):
        configuration.files_directory = os.path.join(
            os.path.dirname(configuration_location), configuration.files_directory)
        assert os.path.isabs(configuration.files_directory)

    for file_as_yml in configuration_as_yml[FILES_KEY]:
        src = file_as_yml[FILES_SRC_KEY]
        if not os.path.isabs(src):
            if configuration.files_directory is None:
                raise ValueError(f"Absolute file source {src} specified without the files directory being set")
            src = os.path.join(configuration.files_directory, src)
            assert os.path.isabs(src)

        configuration.files.append(FileSyncConfiguration(
            source=src,
            destination=file_as_yml[FILES_DEST_KEY],
            overwrite=file_as_yml[FILES_OVERWRITE_KEY]
        ))

    for subrepo_as_yml in configuration_as_yml[SUBREPOS_KEY]:
        configuration.subrepos.append(SubRepoSyncConfiguration(
            remote=subrepo_as_yml[SUBREPOS_REMOTE_KEY],
            branch=subrepo_as_yml[SUBREPOS_BRANCH_KEY],
            overwrite=subrepo_as_yml[SUBREPOS_OVERWRITE_KEY]
        ))

    return configuration




