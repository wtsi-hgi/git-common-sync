# XXX: I have not worked it out but it appears that this module gets loaded correctly if there is some padding at the
# top!? It is not obvious that the Ansible import is required but I have added it for good measure. Expect issues
# using this module in the future...
# noinspection PyUnresolvedReferences
from ansible.module_utils.basic import AnsibleModule
import os
from coverage import Coverage
from distutils.sysconfig import get_python_lib

_PROJECT_ROOT = os.environ["PROJECT_ROOT"]


def main():
    coverage = Coverage(data_file=f"{_PROJECT_ROOT}/.coverage.ansible", branch=True,
                        include=f"{get_python_lib()}/gitcommonsync*/gitcommonsync/ansible_module.py")
    coverage.start()
    try:
        from gitcommonsync.ansible_module import main as real_main
        real_main()
    finally:
        coverage.stop()
        coverage.save()


if __name__ == "__main__":
    main()
