import hashlib
import os
import shutil
import tarfile
import unittest
from tempfile import mkdtemp, mkstemp
from typing import Tuple
import stat

from checksumdir import dirhash
from git import Repo

from gitcommonsync._repository import GitRepository
from gitcommonsync.models import FileSyncConfiguration
from gitcommonsync.synchronise import synchronise_files
from gitcommonsync.tests._resources.information import EXTERNAL_REPOSITORY_ARCHIVE, EXTERNAL_REPOSITORY_NAME, FILE_1, \
    BRANCH, DIRECTORY_1

NEW_FILE_1 = "new-file.txt"
NEW_DIRECTORY_1 = "new-directory"
CONTENTS = "test contents"


class _TestWithGitRepository(unittest.TestCase):
    """
    Base class for tests involving a Git repository.
    """
    def setUp(self):
        self.temp_directory = mkdtemp()

        with tarfile.open(EXTERNAL_REPOSITORY_ARCHIVE) as archive:
            archive.extractall(path=self.temp_directory)
        external_git_repository = os.path.join(self.temp_directory, EXTERNAL_REPOSITORY_NAME)
        self.external_git_repository = Repo(external_git_repository)

        self.git_repository = GitRepository(external_git_repository, BRANCH)
        self.git_directory = self.git_repository.checkout()

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
    TODO
    """
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
        configurations = [FileSyncConfiguration(source, destination, overwrite=False)]
        synchronised = synchronise_files(self.git_repository, configurations)
        self.assertEqual(configurations, synchronised)
        self.assertEqual(source_md5, get_md5(source))
        self.assertEqual(get_md5(source), get_md5(destination))

    def test_sync_new_directory(self):
        source, source_md5 = self.create_test_directory()
        destination = os.path.join(self.git_directory, NEW_FILE_1)
        configurations = [FileSyncConfiguration(source, destination, overwrite=False)]
        synchronised = synchronise_files(self.git_repository, configurations)
        self.assertEqual(configurations, synchronised)
        self.assertEqual(source_md5, get_md5(source))
        self.assertEqual(get_md5(source), get_md5(destination))

    def test_sync_with_new_intermediate_directories(self):
        source, source_md5 = self.create_test_file()
        destination = os.path.join(self.git_directory, NEW_DIRECTORY_1, NEW_FILE_1)
        configurations = [FileSyncConfiguration(source, destination, overwrite=False)]
        synchronised = synchronise_files(self.git_repository, configurations)
        self.assertEqual(configurations, synchronised)
        self.assertEqual(get_md5(source), get_md5(destination))

    def test_sync_out_of_date_file_when_no_overwrite(self):
        source, source_md5 = self.create_test_file()
        destination = os.path.join(self.git_directory, FILE_1)
        assert source_md5 != get_md5(destination)
        configurations = [FileSyncConfiguration(source, destination, overwrite=False)]
        synchronised = synchronise_files(self.git_repository, configurations)
        self.assertEqual(0, len(synchronised))

    def test_sync_out_of_date_directory_when_no_overwrite(self):
        source, source_md5 = self.create_test_directory()
        destination = os.path.join(self.git_directory, DIRECTORY_1)
        assert source_md5 != get_md5(destination)
        configurations = [FileSyncConfiguration(source, destination, overwrite=False)]
        synchronised = synchronise_files(self.git_repository, configurations)
        self.assertEqual(0, len(synchronised))

    def test_sync_out_of_date_file_when_overwrite(self):
        source, source_md5 = self.create_test_file()
        destination = os.path.join(self.git_directory, FILE_1)
        assert source_md5 != get_md5(destination)
        configurations = [FileSyncConfiguration(source, destination, overwrite=True)]
        synchronised = synchronise_files(self.git_repository, configurations)
        self.assertEqual(configurations, synchronised)
        self.assertEqual(source_md5, get_md5(source))
        self.assertEqual(get_md5(source), get_md5(destination))

    def test_sync_out_of_date_directory_when_overwrite(self):
        source, source_md5 = self.create_test_directory()
        # We want to copy contents of directory, not the directory itself so adding / suffix
        source += os.path.sep
        destination = os.path.join(self.git_directory, DIRECTORY_1)
        assert source_md5 != get_md5(destination)
        configurations = [FileSyncConfiguration(source, destination, overwrite=True)]
        synchronised = synchronise_files(self.git_repository, configurations)
        self.assertEqual(configurations, synchronised)
        self.assertEqual(source_md5, get_md5(source))
        self.assertEqual(get_md5(source), get_md5(destination))

    def test_sync_permissions_change(self):
        destination = os.path.join(self.git_directory, FILE_1)
        source, _ = self.create_test_file()
        shutil.copy(destination, source)
        permissions = 770
        os.chmod(source, permissions)
        assert stat.S_IMODE(os.lstat(source).st_mode) == 770
        configurations = [FileSyncConfiguration(source, destination, overwrite=True)]
        synchronised = synchronise_files(self.git_repository, configurations)
        self.assertEqual(configurations, synchronised)
        self.assertEqual(770, stat.S_IMODE(os.lstat(destination).st_mode))


def get_md5(file_location: str) -> str:
    """
    TODO
    :param file_location:
    :return:
    """
    if os.path.isfile(file_location):
        with open(file_location, "rb") as file:
            content = file.read()
        return hashlib.md5(content).hexdigest()
    else:
        return dirhash(file_location, "md5")
