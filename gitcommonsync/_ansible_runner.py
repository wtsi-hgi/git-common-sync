import json
import os
import subprocess
import sys

import re
import shutil
# from ansible.inventory import Inventory
from typing import Dict, List

# from ansible.vars import VariableManager

ANSIBLE_TEMPLATE_MODULE_NAME = "template"
ANSIBLE_RSYNC_MODULE_NAME = "synchronize"

_ANSIBLE_LOCATION = shutil.which("ansible")
_ANSIBLE_MODULE_FLAG = "-m"
_ANSIBLE_MODULE_ARGUMENTS_FLAG = "-a"
_ANSILBE_INVENTORY_FLAG = "-i"
_ANSIBLE_VARIABLE_FLAG = "-e"
_ANSILBE_CONNECTION_FLAG = "-c"
_ANSIBLE_LOCAL_INVENTORY = "localhost"
_ANSIBLE_LOCAL_CONNECTION = "local"
_ANSIBLE_OUTPUT_ENCODING = "utf-8"
_ANSIBLE_HOST = "localhost"
_ANSIBLE_STDOUT_CALLBACK_ENV_PARAMETER = "ANSIBLE_STDOUT_CALLBACK"
_ANSIBLE_STDOUT_CALLBACK_ONELINE = "oneline"
_ANSIBLE_STDOUT_CALLBACK_JSON_LOG_EXTRACT_PATTERN = re.compile(r".*=> ")
_ANSIBLE_LOAD_CALLBACK_PLUGINS_ENV_PARAMETER = "ANSIBLE_LOAD_CALLBACK_PLUGINS"
_ANSIBLE_LOAD_CALLBACK_PLUGINS_ENABLED = "1"


class AnsibleRuntimeException(RuntimeError):
    """
    Exception raised if Ansible encounters a problem at runtime.
    """
    def __init__(self, output: str, error: str):
        super().__init__(f"Error: {error}; Output: {output}")
        self.output = output
        self.error = error


class AnsibleResult:
    """
    TODO
    """
    @property
    def changed(self) -> bool:
        """
        TODO
        :return:
        """
        return self._log["changed"] == True

    @property
    def command(self) -> str:
        return self._log["cmd"]
    
    @property
    def stdout_lines(self) -> List[str]:
        return self._log["stdout_lines"]

    def __init__(self, log: Dict):
        """
        TODO
        :param log:
        """
        super().__init__()
        self._log = log



def run_ansible(ansible_module: str, ansible_module_arguments: Dict=None, variables: Dict=None,
                ansible_location: str=_ANSIBLE_LOCATION):
    """
    TODO
    :param ansible_module:
    :param ansible_module_arguments:
    :param variables:
    :param ansible_location:
    :return:
    """
    # HOME is required for https://github.com/ansible/ansible/issues/31617
    environment: Dict[str, str] = {variable: os.environ[variable] for variable in ("HOME", "PATH")}
    environment[_ANSIBLE_STDOUT_CALLBACK_ENV_PARAMETER] = _ANSIBLE_STDOUT_CALLBACK_ONELINE
    environment[_ANSIBLE_LOAD_CALLBACK_PLUGINS_ENV_PARAMETER] = _ANSIBLE_LOAD_CALLBACK_PLUGINS_ENABLED

    extra_arguments = []

    if ansible_module_arguments is not None and len(ansible_module_arguments) > 0:
        module_arguments = " ".join([f"{key}={value}" for key, value in ansible_module_arguments.items()])
        extra_arguments += [_ANSIBLE_MODULE_ARGUMENTS_FLAG, module_arguments]

    if variables is not None:
        extra_arguments += [_ANSIBLE_VARIABLE_FLAG, json.dumps(variables)]

    # TODO: Don't gather facts
    process_arguments = [ansible_location, _ANSIBLE_MODULE_FLAG, ansible_module, _ANSILBE_INVENTORY_FLAG,
                         f"{_ANSIBLE_LOCAL_INVENTORY},", _ANSILBE_CONNECTION_FLAG, _ANSIBLE_LOCAL_CONNECTION,
                         _ANSIBLE_VARIABLE_FLAG, f"ansible_python_interpreter={sys.executable}"] \
                         + extra_arguments + [_ANSIBLE_HOST]
    process = subprocess.Popen(process_arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment,
                               encoding="utf-8")
    output, error = process.communicate()

    if process.returncode != 0:
        raise AnsibleRuntimeException(output, error)

    output_json = json.loads(_ANSIBLE_STDOUT_CALLBACK_JSON_LOG_EXTRACT_PATTERN.sub("", output))
    return AnsibleResult(output_json)
