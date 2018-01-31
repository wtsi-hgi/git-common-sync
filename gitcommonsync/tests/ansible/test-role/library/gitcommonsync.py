# !/usr/bin/env python3
# Given that the module gets run on the "remote" machine, it is necessary to use Coverage here if we want coverage
# results.
#
# Note: the import of `AnsibleModule` is required!
# noinspection PyUnresolvedReferences
from ansible.module_utils.basic import AnsibleModule

import os
import sys
from distutils.sysconfig import get_python_lib

from coverage import Coverage
from uuid import uuid4

_PROJECT_ROOT_ENVIRONMENT_VARIABLE = "PROJECT_ROOT"
_COVERAGE_ENVIRONMENT_VARIABLE = "PYTHON_COVERAGE"


def main():
    coverage_on = os.environ.get(_COVERAGE_ENVIRONMENT_VARIABLE)

    if coverage_on:
        project_root = os.path.normpath(os.environ[_PROJECT_ROOT_ENVIRONMENT_VARIABLE])
        coverage_output_file = f"{project_root}/.coverage.ansible.{uuid4()}"
        coverage = Coverage(data_file=coverage_output_file, branch=True,
                            include=f"{get_python_lib()}/gitcommonsync*/gitcommonsync/ansible_module.py")
        coverage.start()

    sys.path.append(os.environ[_PROJECT_ROOT_ENVIRONMENT_VARIABLE])
    try:
        from gitcommonsync.ansible_module import main as real_main
        real_main()
    finally:
        if coverage_on:
            coverage.stop()
            coverage.save()


if __name__ == "__main__":
    main()
