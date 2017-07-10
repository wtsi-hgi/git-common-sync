import json
import os
import shutil
import stat
import tarfile
import unittest
from pathlib import Path
from tempfile import mkdtemp, mkstemp
from typing import Tuple, Dict

import gitsubrepo
from git import Repo
from gitsubrepo.exceptions import NotAGitSubrepoException

from gitcommonsync._ansible_runner import run_ansible_task, ANSIBLE_TEMPLATE_MODULE_NAME
from gitcommonsync._repository import GitRepository
from gitcommonsync.models import FileSyncConfiguration, SubrepoSyncConfiguration, GitCheckout, TemplateSyncConfiguration
from gitcommonsync.synchronise import synchronise_files, synchronise_subrepos, synchronise_templates
from gitcommonsync.tests._common import get_md5
from gitcommonsync.tests._resources.information import EXTERNAL_REPOSITORY_ARCHIVE, EXTERNAL_REPOSITORY_NAME, FILE_1, \
    BRANCH, DIRECTORY_1, GIT_MASTER_BRANCH, GIT_MASTER_HEAD_COMMIT, GIT_MASTER_OLD_COMMIT, GIT_DEVELOP_BRANCH

NEW_FILE_1 = "new-file.txt"
NEW_DIRECTORY_1 = "new-directory"
CONTENTS = "test contents"
TEMPLATE_VARIABLES = {
    "foo": "123",
    "bar": "abc"
}
TEMPLATE = {parameter: "{{ %s }}" % parameter for parameter in TEMPLATE_VARIABLES.keys()}
GITHUB_TEST_REPOSITORY = "https://github.com/colin-nolan/test-repository.git"


class _TestWithGitRepository(unittest.TestCase):
    """
    Base class for tests involving a Git repository.
    """
    def setUp(self):
        self.temp_directory = mkdtemp()

        with tarfile.open(EXTERNAL_REPOSITORY_ARCHIVE) as archive:
            archive.extractall(path=self.temp_directory)
        self.external_git_repository_location = os.path.join(self.temp_directory, EXTERNAL_REPOSITORY_NAME)
        self.external_git_repository = Repo(self.external_git_repository_location)

        self.git_repository = GitRepository(self.external_git_repository_location, BRANCH)
        self.git_directory = self.git_repository.checkout(parent_directory=self.temp_directory)
        self.external_git_repository_md5 = get_md5(self.git_directory)

    def tearDown(self):
        shutil.rmtree(self.temp_directory)

    def create_test_file(self, contents=CONTENTS, directory: str=None) -> Tuple[str, str]:
        directory = directory if directory is not None else self.temp_directory
        _, location = mkstemp(dir=directory)
        with open(location, "w") as file:
            file.write(contents)
        return location, get_md5(location)

    def create_test_directory(self, contains_n_files: int=3) -> Tuple[str, str]:
        location = mkdtemp(dir=self.temp_directory)
        for _ in range(contains_n_files):
            self.create_test_file(directory=location)
        return location, get_md5(location)


class TestSynchroniseFiles(_TestWithGitRepository):
    """
    Tests for `synchronise_files`.
    """
    def _synchronise_and_assert(self, configuration: FileSyncConfiguration, expect_sync: bool=True):
        """
        TODO
        :param configuration:
        :param expect_sync:
        :return:
        """
        source_md5 = get_md5(configuration.source)
        destination_original_md5 = get_md5(configuration.destination)
        synchronised = synchronise_files(self.git_repository, [configuration])

        if expect_sync:
            self.assertEqual([configuration], synchronised)
            self.assertEqual(get_md5(configuration.source), get_md5(configuration.destination))
        else:
            self.assertEqual(0, len(synchronised))
            self.assertEqual(destination_original_md5, get_md5(configuration.destination))
        self.assertEqual(source_md5, get_md5(configuration.source))
        self.assertFalse(Repo(self.git_directory).is_dirty())

    def test_sync_non_existent_file(self):
        source = os.path.join(self.temp_directory, "does-not-exist")
        destination = os.path.join(self.git_directory, FILE_1)
        configuration = [FileSyncConfiguration(source, destination)]
        self.assertRaises(FileNotFoundError, synchronise_files, self.git_repository, configuration)

    def test_sync_to_outside_repository(self):
        source, _ = self.create_test_file()
        destination = os.path.join(self.git_directory, "..", FILE_1)
        configuration = [FileSyncConfiguration(source, destination)]
        self.assertRaises(ValueError, synchronise_files, self.git_repository, configuration)

    def test_sync_when_repository_not_checked_out(self):
        self.git_repository.checkout_location = None
        self.assertRaises(NotADirectoryError, synchronise_files, self.git_repository, [])

    def test_sync_up_to_date_file(self):
        destination = os.path.join(self.git_directory, FILE_1)
        source, _ = self.create_test_file()
        shutil.copy(destination, source)
        configuration = [FileSyncConfiguration(source, destination, overwrite=True)]
        synchronised = synchronise_files(self.git_repository, configuration)
        self.assertEqual(0, len(synchronised))

    def test_sync_up_to_date_directory(self):
        source = os.path.join(self.temp_directory, DIRECTORY_1) + os.path.sep
        destination = os.path.join(self.git_directory, DIRECTORY_1)
        shutil.copytree(destination, source)
        configuration = [FileSyncConfiguration(source, destination, overwrite=True)]
        synchronised = synchronise_files(self.git_repository, configuration)
        self.assertEqual(0, len(synchronised))

    def test_sync_new_file(self):
        source, source_md5 = self.create_test_file()
        destination = os.path.join(self.git_directory, NEW_FILE_1)
        self._synchronise_and_assert(FileSyncConfiguration(source, destination, overwrite=False))

    def test_sync_new_directory(self):
        source, source_md5 = self.create_test_directory()
        destination = os.path.join(self.git_directory, NEW_DIRECTORY_1)
        self._synchronise_and_assert(FileSyncConfiguration(source, destination, overwrite=False))

    def test_sync_with_new_intermediate_directories(self):
        source, source_md5 = self.create_test_file()
        destination = os.path.join(self.git_directory, NEW_DIRECTORY_1, NEW_FILE_1)
        self._synchronise_and_assert(FileSyncConfiguration(source, destination, overwrite=False))

    def test_sync_out_of_date_file_when_no_overwrite(self):
        source, source_md5 = self.create_test_file()
        destination = os.path.join(self.git_directory, FILE_1)
        assert source_md5 != get_md5(destination)
        self._synchronise_and_assert(FileSyncConfiguration(source, destination, overwrite=False), expect_sync=False)

    def test_sync_out_of_date_directory_when_no_overwrite(self):
        source, source_md5 = self.create_test_directory()
        destination = os.path.join(self.git_directory, DIRECTORY_1)
        assert source_md5 != get_md5(destination)
        self._synchronise_and_assert(FileSyncConfiguration(source, destination, overwrite=False), expect_sync=False)

    def test_sync_out_of_date_file_when_overwrite(self):
        source, source_md5 = self.create_test_file()
        destination = os.path.join(self.git_directory, FILE_1)
        assert source_md5 != get_md5(destination)
        self._synchronise_and_assert(FileSyncConfiguration(source, destination, overwrite=True))

    def test_sync_out_of_date_directory_when_overwrite(self):
        source, source_md5 = self.create_test_directory()
        # We want to copy contents of directory, not the directory itself so adding / suffix
        source += os.path.sep
        destination = os.path.join(self.git_directory, DIRECTORY_1)
        assert source_md5 != get_md5(destination)
        self._synchronise_and_assert(FileSyncConfiguration(source, destination, overwrite=True))

    def test_sync_permissions_change(self):
        destination = os.path.join(self.git_directory, FILE_1)
        source, _ = self.create_test_file()
        shutil.copy(destination, source)
        permissions = 770
        os.chmod(source, permissions)
        assert stat.S_IMODE(os.lstat(source).st_mode) == 770
        self._synchronise_and_assert(FileSyncConfiguration(source, destination, overwrite=True))
        self.assertEqual(770, stat.S_IMODE(os.lstat(destination).st_mode))


class TestSynchroniseSubrepos(_TestWithGitRepository):
    """
    Tests for `synchronise_subrepos`.
    """
    def setUp(self):
        super().setUp()
        self.git_checkout = GitCheckout(self.external_git_repository_location, GIT_MASTER_BRANCH, NEW_DIRECTORY_1)
        self.git_subrepo_directory = os.path.join(self.git_directory, self.git_checkout.directory)

    def test_sync_onto_existing_non_subrepo_directory(self):
        configurations = [SubrepoSyncConfiguration(self.git_checkout)]
        os.makedirs(self.git_subrepo_directory)
        self.assertRaises(NotAGitSubrepoException, synchronise_subrepos, self.git_repository, configurations)

    def test_sync_to_directory_outside_repository(self):
        self.git_checkout.directory = self.external_git_repository_location
        configurations = [SubrepoSyncConfiguration(self.git_checkout)]
        self.assertRaises(ValueError, synchronise_subrepos, self.git_repository, configurations)

    def test_sync_new_subrepo(self):
        self.git_checkout.commit = GIT_MASTER_HEAD_COMMIT
        configurations = [SubrepoSyncConfiguration(self.git_checkout)]
        synchronised = synchronise_subrepos(self.git_repository, configurations)
        self.assertEqual(configurations, synchronised)
        self.assertEqual(self.external_git_repository_md5, get_md5(self.git_subrepo_directory))
        self.assertEqual(self.git_checkout.commit[0:7], gitsubrepo.status(self.git_subrepo_directory)[2])

    def test_sync_up_to_date_subrepo(self):
        gitsubrepo.clone(self.git_checkout.url, self.git_subrepo_directory, branch=self.git_checkout.branch)
        configurations = [SubrepoSyncConfiguration(self.git_checkout, overwrite=True)]
        synchronised = synchronise_subrepos(self.git_repository, configurations)
        self.assertEqual([], synchronised)

    def test_sync_new_subrepo_from_github(self):
        self.git_checkout.url = GITHUB_TEST_REPOSITORY
        gitsubrepo.clone(self.git_checkout.url, self.git_subrepo_directory, branch=self.git_checkout.branch)
        configurations = [SubrepoSyncConfiguration(self.git_checkout)]
        synchronised = synchronise_subrepos(self.git_repository, configurations)
        self.assertEqual([], synchronised)

    def test_sync_out_of_date_subrepo_no_override(self):
        gitsubrepo.clone(self.git_checkout.url, self.git_subrepo_directory, branch=self.git_checkout.branch,
              commit=GIT_MASTER_OLD_COMMIT)
        configurations = [SubrepoSyncConfiguration(self.git_checkout, overwrite=False)]
        synchronised = synchronise_subrepos(self.git_repository, configurations)
        self.assertEqual([], synchronised)
        self.assertEqual(GIT_MASTER_OLD_COMMIT[0:7], gitsubrepo.status(self.git_subrepo_directory)[2])

    def test_sync_out_of_date_subrepo_with_override(self):
        gitsubrepo.clone(self.git_checkout.url, self.git_subrepo_directory, branch=GIT_MASTER_BRANCH)
        self.git_repository.push_changes()

        updated_repository = GitRepository(self.external_git_repository_location, GIT_MASTER_BRANCH)
        updated_repository_location = updated_repository.checkout(parent_directory=self.create_test_directory()[0])
        Path(os.path.join(updated_repository_location, NEW_FILE_1)).touch()
        updated_repository.push_changes("Updated", [os.path.join(updated_repository_location, NEW_FILE_1)])
        Repo(self.git_repository.checkout_location).remotes.origin.pull()

        configurations = [SubrepoSyncConfiguration(self.git_checkout, overwrite=True)]
        synchronised = synchronise_subrepos(self.git_repository, configurations)
        self.assertEqual(configurations, synchronised)
        self.assertTrue(os.path.exists(os.path.join(self.git_subrepo_directory, NEW_FILE_1)))

    def test_sync_out_of_date_subrepo_to_intermediate_commit(self):
        self.git_checkout.commit = GIT_MASTER_HEAD_COMMIT
        gitsubrepo.clone(self.git_checkout.url, self.git_subrepo_directory, branch=GIT_MASTER_BRANCH)
        # Push the clone commit
        self.git_repository.push_changes()
        configurations = [SubrepoSyncConfiguration(self.git_checkout, overwrite=True)]
        synchronised = synchronise_subrepos(self.git_repository, configurations)
        self.assertEqual(configurations, synchronised)
        self.assertEqual(self.git_checkout.commit[0:7], gitsubrepo.status(self.git_subrepo_directory)[2])

    def test_sync_subrepo_to_different_branch(self):
        gitsubrepo.clone(self.git_checkout.url, self.git_subrepo_directory, branch=GIT_DEVELOP_BRANCH)
        configurations = [SubrepoSyncConfiguration(self.git_checkout, overwrite=True)]
        synchronised = synchronise_subrepos(self.git_repository, configurations)
        self.assertEqual(configurations, synchronised)
        url, branch, commit = gitsubrepo.status(self.git_subrepo_directory)
        self.assertEqual(GIT_MASTER_HEAD_COMMIT[0:7], commit)
        self.assertEqual(GIT_MASTER_BRANCH, branch)


class TestSynchroniseTemplates(_TestWithGitRepository):
    """
    Tests for `synchronise_templates`.
    """
    def setUp(self):
        super().setUp()
        self.template_source, _ = self.create_test_file(contents=json.dumps(TEMPLATE))
        self.template_destination = os.path.join(self.git_directory, NEW_FILE_1)

    def test_sync_template_with_incomplete_variables(self):
        configurations = [TemplateSyncConfiguration(self.template_source, self.template_destination, variables={})]
        self.assertRaises(RuntimeError, synchronise_templates, self.git_repository, configurations)

    def test_sync_new_template(self):
        configurations = [TemplateSyncConfiguration(
            self.template_source, self.template_destination, variables=TEMPLATE_VARIABLES)]
        synchronised = synchronise_templates(self.git_repository, configurations)
        self.assertEqual(configurations, synchronised)
        self.assertTrue(os.path.exists(self.template_destination))
        with open(self.template_destination, "r") as file:
            self.assertEqual(TEMPLATE_VARIABLES, json.load(file))

    def test_sync_up_to_date_template(self):
        self._write_template()
        configurations = [TemplateSyncConfiguration(
            self.template_source, self.template_destination, variables=TEMPLATE_VARIABLES, overwrite=True)]
        synchronised = synchronise_templates(self.git_repository, configurations)
        self.assertEqual([], synchronised)

    def test_sync_out_of_date_date_template_without_overwrite(self):
        self._write_template()
        altered_variables = {key: f"{value}-2" for key, value in TEMPLATE_VARIABLES.items()}
        configurations = [TemplateSyncConfiguration(
            self.template_source, self.template_destination, variables=altered_variables, overwrite=False)]
        synchronised = synchronise_templates(self.git_repository, configurations)
        self.assertEqual([], synchronised)

    def test_sync_out_of_date_date_template_with_overwrite(self):
        self._write_template()
        altered_variables = {key: f"{value}-2" for key, value in TEMPLATE_VARIABLES.items()}
        configurations = [TemplateSyncConfiguration(
            self.template_source, self.template_destination, variables=altered_variables, overwrite=True)]
        synchronised = synchronise_templates(self.git_repository, configurations)
        self.assertEqual(configurations, synchronised)
        with open(self.template_destination, "r") as file:
            self.assertEqual(altered_variables, json.load(file))

    def _write_template(self, template_variables: Dict[str, str]=TEMPLATE_VARIABLES):
        """
        Writes the given template variables to template being used in this test setup.
        :param template_variables: variables to populate the template with
        """
        run_ansible_task(
            dict(action=dict(module=ANSIBLE_TEMPLATE_MODULE_NAME,
                             args=dict(src=self.template_source, dest=self.template_destination))),
            template_variables
        )
