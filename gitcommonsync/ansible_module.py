EXAMPLES = """
- gitcommonsync:
    repository: http://www.example.com/repository.git
    committer_name: Ansible Synchroniser
    committer_email: team@example.com
    key_file: /custom/id_rsa
    files:
      - src: /example/README.md
        dest: README.md
        overwrite: false
      - src: /example/directory/
        dest: config
    templates:
      - src: /example/ansible-groups.sh.j2
        dest: ci/before_scripts.d/start.sh
        variables:
          message: "Hello world"
        overwrite: true
    subrepos:
      - src: http://www.example.com/other-repository.git
        dest: subrepos/other-repository
        branch: master
        overwrite: true
"""

try:
    from gitcommonsync.synchronise import synchronise, Synchronised
    _HAS_DEPENDENCIES = True
except ImportError as e:
    _HAS_DEPENDENCIES = False
    _IMPORT_ERROR = e

import traceback
from typing import Any, Dict, Tuple

from ansible.module_utils.basic import AnsibleModule

from gitcommonsync._repository import GitRepository
from gitcommonsync.models import TemplateSyncConfiguration, FileSyncConfiguration, SubrepoSyncConfiguration, \
    GitCheckout, SyncConfiguration


_REPOSITORY_URL_PROPERTY = "repository"
_REPOSITORY_BRANCH_PROPERTY = "branch"
_REPOSITORY_COMMITTER_NAME_PROPERTY = "committer_name"
_REPOSITORY_COMMITTER_EMAIL_PROPERTY = "committer_email"
_REPOSITORY_KEY_FILE_PROPERTY = "key_file"

_TEMPLATES_PROPERTY = "templates"
_FILES_PROPERTY = "files"
_SUBREPOS_PROPERTY = "subrepos"

_TEMPLATE_SOURCE_PROPERTY = "src"
_TEMPLATE_DESTINATION_PROPERTY = "dest"
_TEMPLATE_OVERWRITE_PROPERTY = "overwrite"
_TEMPLATE_VARIABLES_PROPERTY = "variables"

_FILE_SOURCE_PROPERTY = "src"
_FILE_DESTINATION_PROPERTY = "dest"
_FILE_OVERWRITE_PROPERTY = "overwrite"

_SUBREPO_URL_PROPERTY = "src"
_SUBREPO_BRANCH_PROPERTY = "branch"
_SUBREPO_COMMIT_PROPERTY = "commit"
_SUBREPO_DIRECTORY_PROPERTY = "dest"
_SUBREPO_OVERWRITE_PROPERTY = "overwrite"

_ARGUMENT_SPEC = {
    _REPOSITORY_URL_PROPERTY: dict(required=True, type="str"),
    _REPOSITORY_BRANCH_PROPERTY: dict(required=False, default="master", type="str"),
    _REPOSITORY_COMMITTER_NAME_PROPERTY: dict(required=False, type="str"),
    _REPOSITORY_COMMITTER_EMAIL_PROPERTY: dict(required=False, type="str"),
    _REPOSITORY_KEY_FILE_PROPERTY: dict(required=False, type="str"),
    _TEMPLATES_PROPERTY: dict(required=False, default=[], type="list"),
    _FILES_PROPERTY: dict(required=False, default=[], type="list"),
    _SUBREPOS_PROPERTY: dict(required=False, default=[], type="list")
}


def fail_if_missing_dependencies(module: AnsibleModule):
    """
    Fails if this module is missing a required dependency.
    :param module: TODO
    :return:
    """
    if not _HAS_DEPENDENCIES:
        module.fail_json(msg="A required Python module is not installed: %s" % traceback.format_exception(
            type(_IMPORT_ERROR), _IMPORT_ERROR, _IMPORT_ERROR.__traceback__))


def parse_configuration(arguments: Dict[str, Any]) -> Tuple["GitRepository", "SyncConfiguration"]:
    """
    Parses the configuration defined in Ansible.
    :param arguments: the arguments passed to this module by Ansible
    :return: tuple where the first element is the git repository that is to be synchronised and the seocnd is the
    configuration that defines how it is to be synchronised
    """
    repository_location = arguments[_REPOSITORY_URL_PROPERTY]
    branch = arguments[_REPOSITORY_BRANCH_PROPERTY]
    comitter_name = arguments[_REPOSITORY_COMMITTER_NAME_PROPERTY]
    comitter_email = arguments[_REPOSITORY_COMMITTER_EMAIL_PROPERTY]
    private_key_file = arguments[_REPOSITORY_KEY_FILE_PROPERTY]

    repository = GitRepository(remote=repository_location, branch=branch, private_key_file=private_key_file,
                               committer_name_and_email=(comitter_name, comitter_email))

    sync_configuration = SyncConfiguration()

    sync_configuration.templates = [
        TemplateSyncConfiguration(
            source=configuration[_TEMPLATE_SOURCE_PROPERTY],
            destination=configuration[_TEMPLATE_DESTINATION_PROPERTY],
            overwrite=configuration[_TEMPLATE_OVERWRITE_PROPERTY]
            if _TEMPLATE_OVERWRITE_PROPERTY in configuration else False,
            variables=configuration[_TEMPLATE_VARIABLES_PROPERTY]
        )
        for configuration in arguments[_TEMPLATES_PROPERTY]
    ]

    sync_configuration.files = [
        FileSyncConfiguration(
            source=configuration[_FILE_SOURCE_PROPERTY],
            destination=configuration[_FILE_DESTINATION_PROPERTY],
            overwrite=configuration[_FILE_OVERWRITE_PROPERTY] if _FILE_OVERWRITE_PROPERTY in configuration else False
        )
        for configuration in arguments[_FILES_PROPERTY]
    ]

    sync_configuration.subrepos = [
        SubrepoSyncConfiguration(
            checkout=GitCheckout(
                url=configuration[_SUBREPO_URL_PROPERTY],
                branch=configuration[_SUBREPO_BRANCH_PROPERTY],
                commit=configuration[_SUBREPO_COMMIT_PROPERTY] if _SUBREPO_COMMIT_PROPERTY in configuration else None,
                directory=configuration[_SUBREPO_DIRECTORY_PROPERTY]
            ),
            overwrite=configuration[_SUBREPO_OVERWRITE_PROPERTY]
            if _SUBREPO_OVERWRITE_PROPERTY in configuration else False
        )
        for configuration in arguments[_SUBREPOS_PROPERTY]
    ]

    return repository, sync_configuration


def generate_output_information(synchronised: "Synchronised") -> Dict[str, Any]:
    """
    Generates output information based on what synchronisations were applied.
    :param synchronised: the synchronisations applied
    :return: output in the form of JSON
    """
    return {
        "files": [synchronisation.destination for synchronisation in synchronised.file_synchronisations],
        "templates": [synchronisation.destination for synchronisation in synchronised.template_synchronisations],
        "subrepos": [synchronisation.checkout.directory for synchronisation in synchronised.subrepo_synchronisations]
    }


def main():
    """
    Entrypoint.
    """
    module = AnsibleModule(
        argument_spec=_ARGUMENT_SPEC,
        supports_check_mode=True
    )
    fail_if_missing_dependencies(module)
    repository, sync_configuration = parse_configuration(module.params)

    synchronised = synchronise(repository, sync_configuration, dry_run=module.check_mode)
    # TODO: Consider catchable exceptions
    assert synchronised.get_number_of_synchronisations() >= 0
    assert synchronised.get_number_of_synchronisations() <= sync_configuration.get_number_of_synchronisations()

    module.exit_json(changed=synchronised.get_number_of_synchronisations() > 0,
                     synchronised=generate_output_information(synchronised))


if __name__ == "__main__":
    main()
