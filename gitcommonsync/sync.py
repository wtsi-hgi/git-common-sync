import filecmp
import os
import re
import shutil
from typing import Set
from tempfile import mkdtemp
from time import sleep

import logging

import dirsync

from gitcommonsync.configuration import SyncConfiguration, FileSyncConfiguration
from gitcommonsync.repository import GitConfiguration, checkout

_logger = logging.getLogger(__name__)


def synchronise(configuration: SyncConfiguration, git_configuration: GitConfiguration):
    """
    TODO
    :param configuration:
    :return:
    """
    repo_location = checkout(git_configuration)
    applied_file_syncs: Set[FileSyncConfiguration] = set()

    for file in configuration.files:
        dest = os.path.join(repo_location, file.dest)
        target = os.path.join(repo_location, dest)

        if ".." in os.path.relpath(dest, repo_location):
            raise ValueError(f"Destination not inside of repository: {target}")

        exists = os.path.exists(target)
        if exists and not file.override:
            _logger.info(f"Not overwriting {target} with {file.src}")
            continue
        assert os.path.isabs(file.src)

        if os.path.isfile(file.src) and not filecmp.cmp(file.src, target, shallow=False):
            shutil.copy(file.src, target)
            applied_file_syncs.add(file)
        else:
            # FIXME: Check if different
            # TODO: This is a very crude way to mirror files!
            if os.path.exists(target):
                shutil.rmtree(target)
            shutil.copytree(file.src, target)


        _logger.info(f"Copied {file.src} => {target} (overwrite={exists})")

    print(repo_location)
    sleep(1000)


