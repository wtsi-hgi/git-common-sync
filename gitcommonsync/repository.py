from tempfile import mkdtemp
from typing import NamedTuple

from git import Repo

DEFAULT_BRANCH = "master"


class GitConfiguration:
    """
    TODO
    """
    def __init__(self, remote: str, branch: str):
        self.remote = remote
        self.branch = branch


def checkout(git_configuration: GitConfiguration) -> str:
    """
    TODO
    :param remote:
    :param branch:
    :return:
    """
    temp_directory = mkdtemp()
    repository = Repo.clone_from(url=git_configuration.remote, to_path=temp_directory)

    if git_configuration.branch not in repository.heads:
        branch_reference = None
        for reference in repository.refs:
            if reference.name == f"origin/{git_configuration.branch}":
                branch_reference = reference
                break
        if branch_reference is not None:
            raise ValueError(f"Branch {git_configuration.branch} not found in remote repository at "
                             f"{git_configuration.remote}")
        commit = repository.commit(git_configuration.branch)
        repository.create_head(path=git_configuration.branch, commit=commit)
    repository.heads[git_configuration.branch].checkout()
    return temp_directory



