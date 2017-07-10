import logging
import os
import shutil
from tempfile import TemporaryDirectory
from typing import List, Dict, Callable, Type

import gitsubrepo
from git import Repo

from gitcommonsync._ansible_runner import run_ansible_task, ANSIBLE_RSYNC_MODULE_NAME, ANSIBLE_TEMPLATE_MODULE_NAME
from gitcommonsync._common import is_subdirectory
from gitcommonsync.models import FileSyncConfiguration, SyncConfiguration, SubrepoSyncConfiguration, GitCheckout, \
    TemplateSyncConfiguration
from gitcommonsync._repository import GitRepository

_logger = logging.getLogger(__name__)

FileSyncConfigurationType = Type("FileSyncConfigurationType", bound=FileSyncConfiguration)


# FIXME: This is ~the same model as `SyncConfiguration`
class Synchronised:
    """
    Changes that happened during the synchronisation.
    """
    def __init__(self):
        self.file_synchronisations: List[FileSyncConfiguration] = None
        self.subrepo_synchronisations: List[SubrepoSyncConfiguration] = None
        self.template_synchronisations: List[TemplateSyncConfiguration] = None

    def get_number_of_synchronisations(self) -> int:
        """
        TODO
        :return:
        """
        return len(self.file_synchronisations) + len(self.subrepo_synchronisations) \
               + len(self.template_synchronisations)


# FIXME: Really need to conver this to a class based implementation
def synchronise(repository: GitRepository, configuration: SyncConfiguration, dry_run: bool=False) -> Synchronised:
    """
    Clones, updates and commits to the given repository, according to the given synchronisation configuration.
    :param repository: the git repository
    :param configuration: the synchronisation configuration
    :param dry_run: TODO
    :return: TODO
    """
    repository.checkout()
    changed = Synchronised()
    try:
        changed.subrepo_synchronisations = synchronise_subrepos(repository, configuration.subrepos, dry_run=dry_run)
        changed.file_synchronisations = synchronise_files(repository, configuration.files, dry_run=dry_run)
        changed.template_synchronisations = synchronise_templates(repository, configuration.templates, dry_run=dry_run)
    finally:
        repository.tear_down()
    return changed


# XXX: It would be possible to write an Ansible module for subrepo using this...
def synchronise_subrepos(repository: GitRepository, configurations: List[SubrepoSyncConfiguration],
                         dry_run: bool=False) -> List[SubrepoSyncConfiguration]:
    """
    TODO
    :param repository:
    :param configurations:
    :return:
    """
    synchronised: List[SubrepoSyncConfiguration] = []

    for configuration in configurations:
        destination = os.path.join(repository.checkout_location, configuration.checkout.directory)
        required_checkout = configuration.checkout

        if not is_subdirectory(destination, repository.checkout_location):
            raise ValueError(f"Destination {destination} not inside of repository")

        if os.path.exists(destination):
            force_update = False
            url, branch, commit = gitsubrepo.status(destination)
            current_checkout = GitCheckout(url, branch, required_checkout.directory, commit=commit)
            same_url_and_branch = current_checkout.url == required_checkout.url \
                                  and current_checkout.branch == required_checkout.branch

            if required_checkout.commit is None and same_url_and_branch:
                with TemporaryDirectory() as temp_directory:
                    subrepo_remote = Repo.init(temp_directory)
                    origin = subrepo_remote.create_remote("origin", url)
                    fetch_infos = origin.fetch()
                    for fetch_info in fetch_infos:
                        if fetch_info.name == f"origin/{branch}":
                            required_checkout.commit = fetch_info.commit.hexsha[0:7]

            if current_checkout == required_checkout:
                _logger.info(f"Subrepo at {required_checkout.directory} is synchronised")
            elif not configuration.overwrite:
                _logger.info(f"Subrepo at {required_checkout.directory} is not synchronised but not updating as "
                             f"overwrite=False")
            elif same_url_and_branch:
                _logger.debug(f"Pulling subrepo at {required_checkout.directory} in an attempt to sync")
                # TODO: We could check whether the remote's head is the commit we want before doing this as it might not
                # pull to the correct commit.
                new_commit = gitsubrepo.pull(destination)
                if new_commit == required_checkout.commit:
                    _logger.info(f"Subrepo at {required_checkout.directory}: {commit} => {new_commit}")
                    synchronised.append(configuration)
                else:
                    force_update = True
            else:
                force_update = True

            if force_update:
                message = f"Removing subrepo at {required_checkout.directory} to force update"
                _logger.debug(message)
                shutil.rmtree(destination)
                repository.commit_changes(message, [destination])

        if not os.path.exists(destination):
            new_commit = gitsubrepo.clone(required_checkout.url, destination,
                                          branch=required_checkout.branch, commit=required_checkout.commit)
            assert new_commit != required_checkout.commit
            _logger.debug(f"Checked out subrepo: {required_checkout}")
            synchronised.append(configuration)

    if not dry_run:
        repository.push_changes()

    return synchronised


def synchronise_files(repository: GitRepository, configurations: List[FileSyncConfiguration], dry_run: bool=False) \
        -> List[FileSyncConfiguration]:
    """
    Synchronises files in the given repository, according to the given configuration
    :param repository: the location of the checked out repository
    :param configurations: the file synchronisation configurations
    :return: the synchronisations applied
    """
    return _synchronise_files(
        repository,
        configurations,
        lambda configuration, target: dict(
            module=ANSIBLE_RSYNC_MODULE_NAME,
            args=dict(src=configuration.source, dest=target, recursive=True, delete=True, archive=False, perms=True,
                      links=True, checksum=True)
        ),
        dry_run=dry_run
    )


def synchronise_templates(repository: GitRepository, configurations: List[TemplateSyncConfiguration], dry_run: bool=False) \
        -> List[TemplateSyncConfiguration]:
    """
    TODO
    :param repository: the location of the checked out repository
    :param configurations: the file template synchronisation configurations
    :return: the synchronisations applied
    """
    # FIXME: The loss of type here indicates this should be refactored into a generic class based form
    return _synchronise_files(
        repository,
        configurations,
        lambda configuration, target: dict(
            module=ANSIBLE_TEMPLATE_MODULE_NAME, args=dict(src=configuration.source, dest=target)
        ),
        lambda configuration: configuration.variables,
        dry_run=dry_run
    )


def _synchronise_files(
        repository: GitRepository, configurations: List[FileSyncConfiguration],
        ansible_action_generator: Callable[[FileSyncConfiguration, str], Dict],
        ansible_variables_generator: Callable[[FileSyncConfiguration, str], Dict[str, str]]=lambda configuration: {},
        dry_run: bool=False) \
        -> List[FileSyncConfiguration]:
    """
    TODO.
    :param repository: the location of the checked out repository
    :param configurations: TODO
    :param ansible_action_generator: TODO
    :param ansible_variables_generator: TODO
    :return: the synchronisations applied
    """
    synchronised: List[FileSyncConfigurationType] = []

    for configuration in configurations:
        if not os.path.exists(configuration.source):
            raise FileNotFoundError(configuration.source)

        destination = os.path.join(repository.checkout_location, configuration.destination)
        target = os.path.join(repository.checkout_location, destination)

        if not is_subdirectory(destination, repository.checkout_location):
            raise ValueError(f"Destination {configuration.destination} not inside of repository "
                             f"({os.path.realpath(target)})")

        exists = os.path.exists(target)
        if exists and not configuration.overwrite:
            _logger.info(f"{configuration.source} != {target} (overwrite={configuration.overwrite})")
            continue
        assert os.path.isabs(configuration.source)

        intermediate_directories = os.path.dirname(target)
        if not os.path.exists(intermediate_directories):
            _logger.info(f"Creating intermediate directories: {intermediate_directories}")
            os.makedirs(intermediate_directories)

        result = run_ansible_task(dict(action=ansible_action_generator(configuration, target)),
                                  ansible_variables_generator(configuration))
        if result.is_failed():
            raise RuntimeError(result._result)
        if result.is_changed():
            synchronised.append(configuration)
            _logger.info(f"{configuration.source} => {target} (overwrite={configuration.overwrite})")
        else:
            _logger.info(f"{configuration.source} == {target}")

    if not dry_run:
        repository.push_changes(
            f"Synchronised {len(synchronised)} file{'' if len(synchronised) == 1 else ''}",
            [os.path.join(repository.checkout_location, file_synchronisation.destination)
             for file_synchronisation in synchronised])

    return synchronised