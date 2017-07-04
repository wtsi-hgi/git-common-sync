import os
import shutil
import tarfile
import tempfile
import unittest
from pathlib import Path

from git import Repo

from gitcommonsync._repository import GitRepository
from gitcommonsync.models import FileSyncConfiguration
from gitcommonsync.synchronise import synchronise_files
from gitcommonsync.tests._resources.information import EXTERNAL_REPOSITORY_ARCHIVE, EXTERNAL_REPOSITORY_NAME, FILE_1, \
    BRANCH, DIRECTORY_1

NEW_FILE_1 = "new-file.txt"


class _TestWithGitRepository(unittest.TestCase):
    """
    Base class for tests involving a Git repository.
    """
    def setUp(self):
        self.temp_directory = tempfile.mkdtemp()

        with tarfile.open(EXTERNAL_REPOSITORY_ARCHIVE) as archive:
            archive.extractall(path=self.temp_directory)
        external_git_repository = os.path.join(self.temp_directory, EXTERNAL_REPOSITORY_NAME)
        self.external_git_repository = Repo(external_git_repository)

        self.git_repository = GitRepository(external_git_repository, BRANCH)
        self.git_directory = self.git_repository.checkout()

    def tearDown(self):
        shutil.rmtree(self.temp_directory)


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
        source = os.path.join(self.temp_directory, FILE_1)
        destination = os.path.join(self.git_directory, "..", FILE_1)
        configuration = [FileSyncConfiguration(source, destination)]
        self.assertRaises(ValueError, synchronise_files, self.git_repository, configuration)

    def test_sync_when_repository_not_checked_out(self):
        self.git_repository.checkout_location = None
        self.assertRaises(NotADirectoryError, synchronise_files, self.git_repository, [])

    def test_sync_up_to_date_file(self):
        source = os.path.join(self.temp_directory, FILE_1)
        destination = os.path.join(self.git_directory, FILE_1)
        shutil.copy(destination, source)
        configuration = [FileSyncConfiguration(source, destination, overwrite=True)]
        synchronised = synchronise_files(self.git_repository, configuration)
        self.assertEqual(0, len(synchronised))

    def test_sync_up_to_date_directory(self):
        source = os.path.join(self.temp_directory, DIRECTORY_1)
        destination = os.path.join(self.git_directory, DIRECTORY_1)
        shutil.copytree(destination, source)
        configuration = [FileSyncConfiguration(source, destination, overwrite=True)]
        synchronised = synchronise_files(self.git_repository, configuration)
        self.assertEqual(0, len(synchronised))

    def test_sync_news_file(self):
        source = os.path.join(self.temp_directory, NEW_FILE_1)
        Path(source).touch()
        destination = os.path.join(self.git_directory, NEW_FILE_1)
        configuration = [FileSyncConfiguration(source, destination, overwrite=False)]
        synchronised = synchronise_files(self.git_repository, configuration)
        self.assertEqual(1, len(synchronised))
