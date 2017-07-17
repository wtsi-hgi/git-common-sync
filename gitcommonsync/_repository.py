import os
import shutil
from tempfile import mkdtemp
from typing import List, Callable, Tuple

from git import Repo, GitCommandError, IndexFile, Actor

DEFAULT_BRANCH = "master"


def requires_checkout(func):
    """
    Enforces the given `GitRepository` method only executes if the repository has been checked out.
    :param func: function of `GitRepository`
    :return: decorated method that raises `NotADirectoryError` if called when the repository has not been checked out
    """
    def decorated(self: "GitRepository", *args, **kwargs) -> Callable:
        if self.checkout_location is None:
            raise NotADirectoryError("Repository must be checked out")
        return func(self, *args, **kwargs)
    return decorated


class GitRepository:
    """
    Wrapper to simplify basic operations on a specific branch of a repository mirrored from a remote.
    """
    _REQUIRED_CONFIGS = ["user.name", "user.email"]

    def __init__(self, remote: str, branch: str, *, checkout_location: str=None,
                 committer_name_and_email: Tuple[str, str]=None):
        """
        Constructor.
        :param remote: url of the remote which this repository tracks
        :param branch: the branch on the remote that is to be checked out
        :param checkout_location: optional location in which the repository has already being checked out
        :param committer_name_and_email: the commit author to use, where the first element is the author's name and the
        second is the author's email address. If not defined, it will be attempted to get the author from the global
        configuration
        """
        self.remote = remote
        self.branch = branch
        self.checkout_location = checkout_location
        self.committer_name = committer_name_and_email[0] if committer_name_and_email is not None else None
        self.committer_email = committer_name_and_email[1] if committer_name_and_email is not None else None

    def tear_down(self):
        """
        Tears down any repository files on the local machine.
        """
        if self.checkout_location:
            shutil.rmtree(self.checkout_location)

    def checkout(self, parent_directory: str=None) -> str:
        """
        Checks out the repository into the given parent directory or temporary directory if not given.
        :param parent_directory: optional parent directory in which the repository is checked out into (in a
        sub-directory)
        :return: the checkout directory
        """
        if self.checkout_location is not None:
            raise IsADirectoryError(f"Repository already checked out in {self.checkout_location}")

        self.checkout_location = mkdtemp(dir=parent_directory)
        repository = Repo.clone_from(url=self.remote, to_path=self.checkout_location)

        repository.heads[self.branch].checkout()
        return self.checkout_location

    @requires_checkout
    def push_changes(self, commit_message: str=None, changed_files: List[str]=None):
        """
        Commits then pushes changes to the repository.
        :param commit_message: see `commit_changes`
        :param changed_files: see `commit_changes`
        """
        self.commit_changes(commit_message, changed_files)
        repository = Repo(self.checkout_location)
        repository.remotes.origin.push()

    @requires_checkout
    def commit_changes(self, commit_message: str, changed_files: List[str]=None):
        """
        Commits changes to the repository.
        :param commit_message: the message to associate to the commit
        :param changed_files: the specific files to commit. If left as `None`, all files will be committed
        """
        if changed_files is None or len(changed_files) > 0:
            repository = Repo(self.checkout_location)

            index = repository.index
            if changed_files is not None:
                added = {changed_file for changed_file in changed_files if os.path.exists(changed_file)}
                removed = set(changed_files) - added
                if len(added) > 0:
                    index.add(added)
                if len(removed) > 0:
                    index.remove(removed, r=True)
            else:
                repository.git.add(A=True)

            if len(repository.index.diff(repository.head.commit)) > 0:
                self._commit(index, commit_message)

    def _commit(self, index: IndexFile, commit_message: str):
        """
        Commits the changes to the given index with the given commit message.
        :param index: the repository index with changes to commit
        :param commit_message: the message to associate with the commit
        """
        if self.committer_name is not None and self.committer_email is not None:
            author = Actor(self.committer_name, self.committer_email)
        else:
            for config in GitRepository._REQUIRED_CONFIGS:
                try:
                    index.repo.git.config(config)
                except GitCommandError as e:
                    raise RuntimeError(f"`git config --global {config}` must be set") from e
            author = None
        index.commit(commit_message, author=author)
