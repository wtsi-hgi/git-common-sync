import shutil
from tempfile import mkdtemp
from typing import List

from git import Repo

DEFAULT_BRANCH = "master"


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
        if self.checkout_location is not None:
            raise IsADirectoryError(f"Repository already checked out in {self.checkout_location}")

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
