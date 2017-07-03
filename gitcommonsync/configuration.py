import os

import yaml

from gitcommonsync.models import SubrepoSyncConfiguration, FileSyncConfiguration, SyncConfiguration, GitCheckout

NAME_KEY = "name"
FILES_DIRECTORY_KEY = "files-directory"
FILES_KEY = "files"
FILES_SRC_KEY = "src"
FILES_DEST_KEY = "dest"
FILES_OVERWRITE_KEY = "overwrite"
SUBREPOS_KEY = "subrepos"
SUBREPOS_BRANCH_KEY = "branch"
SUBREPOS_REMOTE_KEY = "remote"
SUBREPOS_COMMIT_KEY = "commit"
SUBREPOS_DEST_KEY = "dest"
SUBREPOS_OVERWRITE_KEY = "overwrite"


def load_from_yml(yml_configuration_location: str) -> SyncConfiguration:
    """
    TODO
    :param yml_configuration_location:
    :return:
    """
    with open(yml_configuration_location, "r") as file:
        configuration_as_yml = yaml.load(file)

    configuration = SyncConfiguration()
    configuration.name = configuration_as_yml[NAME_KEY]
    files_directory = configuration_as_yml[FILES_DIRECTORY_KEY] \
        if FILES_DIRECTORY_KEY in configuration_as_yml else None

    if files_directory is not None and not os.path.isabs(files_directory):
        files_directory = os.path.join(
            os.path.dirname(yml_configuration_location), files_directory)
        assert os.path.isabs(files_directory)

    for file_as_yml in configuration_as_yml[FILES_KEY]:
        src = file_as_yml[FILES_SRC_KEY]
        if not os.path.isabs(src):
            if files_directory is None:
                raise ValueError(f"Absolute file source {src} specified without the files directory being set")
            src = os.path.join(files_directory, src)
            assert os.path.isabs(src)

        configuration.files.append(FileSyncConfiguration(
            source=src,
            destination=file_as_yml[FILES_DEST_KEY],
            overwrite=file_as_yml[FILES_OVERWRITE_KEY]
        ))

    for subrepo_as_yml in configuration_as_yml[SUBREPOS_KEY]:
        configuration.subrepos.append(SubrepoSyncConfiguration(
            checkout=GitCheckout(
                url=subrepo_as_yml[SUBREPOS_REMOTE_KEY],
                branch=subrepo_as_yml[SUBREPOS_BRANCH_KEY],
                commit=subrepo_as_yml[SUBREPOS_COMMIT_KEY] if SUBREPOS_COMMIT_KEY in subrepo_as_yml else None,
                directory=subrepo_as_yml[SUBREPOS_DEST_KEY]
            ),
            overwrite=subrepo_as_yml[SUBREPOS_OVERWRITE_KEY]
        ))

    return configuration
