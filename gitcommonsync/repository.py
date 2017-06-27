import os
import shutil
from tempfile import mkdtemp
from typing import List, Callable, Optional

from git import Repo

from gitcommonsync.models import GitCheckout

DEFAULT_BRANCH = "master"


def requires_checkout(func):
    """
    TODO
    :param func:
    :return:
    """
    def decorated(self: GitRepository, *args, **kwargs) -> Callable:
        if self.checkout_location is not None:
            raise IsADirectoryError(f"Repository already checked out in {self.checkout_location}")
        return func(*args, **kwargs)
    return decorated


class GitRepository:
    """
    TODO
    """
    def __init__(self, remote: str, branch: str):
        self.remote = remote
        self.branch = branch
        self.checkout_location = None

    def tear_down(self):
        if self.checkout_location:
            shutil.rmtree(self.checkout_location)

    def checkout(self) -> str:
        """
        TODO
        :return:
        """
        self.checkout_location = mkdtemp()
        repository = Repo.clone_from(url=self.remote, to_path=self.checkout_location)

        if self.branch not in repository.heads:
            branch_reference = None
            for reference in repository.refs:
                if reference.name == f"origin/{self.branch}":
                    branch_reference = reference
                    break
            if branch_reference is not None:
                raise ValueError(f"Branch {self.branch} not found in remote repository at "
                                 f"{self.remote}")
            commit = repository.commit(self.branch)
            repository.create_head(path=self.branch, commit=commit)
        repository.heads[self.branch].checkout()
        return self.checkout_location

    @requires_checkout
    def push_changes(self, commit_message: str, changed_files: List[str]):
        """
        TODO
        :param commit_message:
        :param changed_files:
        :return:
        """
        if self.checkout_location is None:
            raise NotADirectoryError("Repository has not been checked out into a directory")

        repository = Repo(self.checkout_location)
        index = repository.index
        index.add(changed_files)
        index.commit(commit_message)

        repository.remotes.origin.push()

    @requires_checkout
    def clone_subrepo(self, checkout: GitCheckout, directory: str):
        """
        TODO
        :param checkout:
        :param directory:
        :return:
        """
        if os.path.exists(directory):
            raise ValueError(f"Target directory {directory} already exists")
        # TODO

    @requires_checkout
    def get_subrepo(self, directory: str) -> Optional[GitCheckout]:
        """
        TODO
        :param directory:
        :return:
        """
        if not os.path.exists(directory):
            return None
        # TODO

    @requires_checkout
    def pull_subrepo(self, directory: str, commit: str=None) -> bool:
        """
        TODO
        :param directory:
        :param commit:
        :return: whether the subrepo was updated
        """
        # TODO
