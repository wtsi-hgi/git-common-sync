import os
from tempfile import TemporaryDirectory

from git import Repo


def is_subdirectory(subdirectory: str, directory: str) -> bool:
    """
    Whether the first given directory is a subdirectory of the second given directory.
    :param subdirectory: the directory that may be a subdirectory of the other
    :param directory: the directory that may contain the subdirectory
    :return: whether the subdirectory is a subdirectory of the directory
    """
    return ".." not in os.path.relpath(subdirectory, directory)


def get_head_commit(url: str, branch: str) -> str:
    """
    TODO
    :param branch:
    :return:
    """
    with TemporaryDirectory() as temp_directory:
        subrepo_remote = Repo.init(temp_directory)
        origin = subrepo_remote.create_remote("origin", url)
        fetch_infos = origin.fetch()
        for fetch_info in fetch_infos:
            if fetch_info.name == f"origin/{branch}":
                return fetch_info.commit.hexsha[0:7]