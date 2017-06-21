from typing import NamedTuple, Dict

from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.executor.task_result import TaskResult
from ansible.inventory import Inventory
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import Play
from ansible.plugins.callback import CallbackBase
from ansible.vars import VariableManager


class AnsibleRuntimeException(RuntimeError):
    """
    Exception raised if Ansible encounters a problem at runtime.
    """


class _ResultCallback(CallbackBase):
    """
    Ansible playbook callback handler.
    """
    def __init__(self):
        super().__init__()
        self.result = None

    def v2_runner_on_ok(self, result, **kwargs):
        self.result = result

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self.result = result


class PlaybookOptions(NamedTuple):
    """
    Ansible playbook options.
    """
    connection: str = "local"
    module_path: str = None
    forks: int = 100
    become: bool = False
    become_method: str = None
    become_user: str = None
    check: bool = False


def run(task: Dict, playbook_options: PlaybookOptions=PlaybookOptions()) -> TaskResult:
    """
    Run the given description of an Ansible task with the given options.
    :param task: the task to run, represented in a JSON dictionary. e.g.
    ```
    dict(action=dict(module="file", args=dict(path="/testing", state="directory"), register="testing_created")
    ```
    :param playbook_options: options to use when running Ansible playbook
    :return: the results of running the task
    """
    variable_manager = VariableManager()
    loader = DataLoader()
    results_callback = _ResultCallback()

    inventory = Inventory(loader=loader, variable_manager=variable_manager, host_list=None)
    variable_manager.set_inventory(inventory)

    play_source = dict(
        hosts="localhost",
        gather_facts="no",
        tasks=[task]
    )
    play = Play().load(play_source, variable_manager=variable_manager, loader=loader)

    task_queue_manager = None
    try:
        task_queue_manager = TaskQueueManager(
            inventory=inventory,
            variable_manager=variable_manager,
            loader=loader,
            options=playbook_options,
            passwords=dict(),
            stdout_callback=results_callback
        )
        task_queue_manager.run(play)
    finally:
        if task_queue_manager is not None:
            task_queue_manager.cleanup()

    return results_callback.result
