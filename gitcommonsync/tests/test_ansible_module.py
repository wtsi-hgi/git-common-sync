import unittest

from gitcommonsync._ansible_runner import run_ansible


class TestAnsibleModule(unittest.TestCase):
    """
    TODO
    """
    def test_ansible_execution(self):
        results = run_ansible(roles=["ansible"])
        for result in results:
            with self.subTest(task=result.task_name):
                self.assertFalse(result.is_failed(), result._result)


if __name__ == "__main__":
    unittest.main()
