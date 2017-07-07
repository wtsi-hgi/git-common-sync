import os
import shutil
from tempfile import mkdtemp
from typing import List, Callable

from git import Repo, GitCommandError

DEFAULT_BRANCH = "master"


def requires_checkout(func):
    """
    TODO
    :param func:
    :return:
    """
    def decorated(self: "GitRepository", *args, **kwargs) -> Callable:
        if self.checkout_location is None:
            raise NotADirectoryError("Repository must be checked out")
        return func(self, *args, **kwargs)
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

    def checkout(self, parent_directory: str=None) -> str:
        """
        TODO
        :param parent_directory: TODO
        :return:
        """
        if self.checkout_location is not None:
            raise IsADirectoryError(f"Repository already checked out in {self.checkout_location}")

        self.checkout_location = mkdtemp(dir=parent_directory)
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
    def push_changes(self, commit_message: str=None, changed_files: List[str]=None):
        """
        TODO
        :param commit_message:
        :param changed_files:
        :return:
        """
        if changed_files is not None:
            self.commit_changes(commit_message, changed_files)
        repository = Repo(self.checkout_location)
        repository.remotes.origin.push()

    @requires_checkout
    def commit_changes(self, commit_message: str, changed_files: List[str]):
        """
        TODO
        :param commit_message:
        :param changed_files:
        :return:
        """
        if len(changed_files) > 0:
            repository = Repo(self.checkout_location)
            try:
                repository.git.config("user.name")
                repository.git.config("user.email")
            except GitCommandError as e:
                raise RuntimeError(
                    "`git config --global user.name` and `git config --global user.email` must be set") from e

            added = {changed_file for changed_file in changed_files if os.path.exists(changed_file)}
            removed = set(changed_files) - added

            index = repository.index
            if len(added) > 0:
                index.add(added)
            if len(removed) > 0:
                index.remove(removed, r=True)
            index.commit(commit_message)
