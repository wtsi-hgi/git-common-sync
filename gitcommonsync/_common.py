import os


def is_subdirectory(subdirectory: str, directory: str) -> bool:
    """
    Whether the first given directory is a subdirectory of the second given directory.
    :param subdirectory: the directory that may be a subdirectory of the other
    :param directory: the directory that may contain the subdirectory
    :return: whether the subdirectory is a subdirectory of the directory
    """
    return ".." not in os.path.relpath(subdirectory, directory)
