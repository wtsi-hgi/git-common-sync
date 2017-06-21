from tempfile import mkdtemp

from git import Repo

DEFAULT_BRANCH = "master"


class GitRepository:
    """
    TODO
    """
    def __init__(self, remote: str, branch: str):
        self.remote = remote
        self.branch = branch


def checkout(git_repository: GitRepository) -> str:
    """
    TODO
    :param remote:
    :param branch:
    :return:
    """
    temp_directory = mkdtemp()
    repository = Repo.clone_from(url=git_repository.remote, to_path=temp_directory)

    if git_repository.branch not in repository.heads:
        branch_reference = None
        for reference in repository.refs:
            if reference.name == f"origin/{git_repository.branch}":
                branch_reference = reference
                break
        if branch_reference is not None:
            raise ValueError(f"Branch {git_repository.branch} not found in remote repository at "
                             f"{git_repository.remote}")
        commit = repository.commit(git_repository.branch)
        repository.create_head(path=git_repository.branch, commit=commit)
    repository.heads[git_repository.branch].checkout()
    return temp_directory



