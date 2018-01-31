import os
import shutil
import subprocess
import unittest
import sys
from copy import copy

_SCRIPT_LOCATION = os.path.dirname(os.path.realpath(__file__))
_PROJECT_ROOT = os.path.join(_SCRIPT_LOCATION, "../..")
_ANSIBLE_TEST_PLAYBOOK_LOCATION = os.path.join(_SCRIPT_LOCATION, "ansible/site.yml")
_ANSIBLE_PLAYBOOK_BINARY = shutil.which("ansible-playbook")


class TestAnsibleModule(unittest.TestCase):
    """
    Tests runner of the Ansible tests.
    """
    def test_ansible_execution(self):
        environment = copy(os.environ)
        environment["PROJECT_ROOT"] = _PROJECT_ROOT

        subprocess.check_call([_ANSIBLE_PLAYBOOK_BINARY, "-i", "localhost,", "-c", "local", "-e",
                               f"ansible_python_interpreter={sys.executable}", _ANSIBLE_TEST_PLAYBOOK_LOCATION],
                              env=environment)


if __name__ == "__main__":
    unittest.main()
