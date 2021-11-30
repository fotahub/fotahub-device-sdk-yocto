import os

from fotahubclient.json_document_models import ArtifactKind, LifecycleState, InstalledArtifacts, InstalledArtifact
from fotahubclient.os_updater import OSUpdater
from fotahubclient.app_updater import AppUpdater

class InstalledArtifactsTracker(object):
 
    def __init__(self, config):
        self.config = config
        self.installed_artifacts = InstalledArtifacts()

    def __enter__(self):
        if os.path.isfile(self.config.installed_artifacts_path) and os.path.getsize(self.config.installed_artifacts_path) > 0:
            self.installed_artifacts = InstalledArtifacts.load_installed_artifacts(self.config.installed_artifacts_path)
        return self 

    def register_os(self, name, install_revision, rollback_revision=None):
        self.__register_artifact(name, ArtifactKind.OperatingSystem, install_revision, rollback_revision, LifecycleState.running)

    def register_app(self, name, install_revision, rollback_revision=None):
        self.__register_artifact(name, ArtifactKind.Application, install_revision, rollback_revision, LifecycleState.available)

    def register_fw(self, name, install_revision, rollback_revision=None):
        self.__register_artifact(name, ArtifactKind.Firmware, install_revision, rollback_revision, LifecycleState.running)

    def __register_artifact(self, name, kind, install_revision, rollback_revision, lifecycle_state):
        installed_artifact = self.__lookup_installed_artifact(name, kind)
        if installed_artifact is not None:
            installed_artifact.reset(install_revision, rollback_revision, lifecycle_state)
        else:
            self.__append_installed_artifact(
                InstalledArtifact(
                    name, 
                    kind, 
                    install_revision,
                    rollback_revision,
                    lifecycle_state
                )
            )

    def erase_app(self, name):
        self.__erase_artifact(name, ArtifactKind.Application)

    def erase_fw(self, name):
        self.__erase_artifact(name, ArtifactKind.Firmware)

    def __erase_artifact(self, name, kind):
        installed_artifact = self.__lookup_installed_artifact(name, kind)
        if installed_artifact is not None:
            self.__remove_installed_artifact(installed_artifact)

    def record_app_install_revision_change(self, name, install_revision, updating=True):
        installed_artifact = self.__lookup_installed_artifact(name, ArtifactKind.Application)
        if installed_artifact is not None:
            installed_artifact.amend_revision_info(install_revision, updating)
        else:
            raise ValueError("Failed to record revision change for unknown application named '{}'".format(name))

    def record_fw_install_revision_change(self, name, install_revision, updating=True):
        installed_artifact = self.__lookup_installed_artifact(name, ArtifactKind.Firmware)
        if installed_artifact is not None:
            installed_artifact.amend_revision_info(install_revision, updating)
        else:
            raise ValueError("Failed to record revision change for unknown firmware named '{}'".format(name))

    def record_app_lifecycle_status_change(self, name, lifecycle_state=None, status=True, message=None):
        installed_artifact = self.__lookup_installed_artifact(name, ArtifactKind.Application)
        if installed_artifact is not None:
            installed_artifact.amend_lifecycle_info(lifecycle_state, status, message)
        else:
            raise ValueError("Failed to record lifecycle status change for unknown application named '{}'".format(name))

    def __lookup_installed_artifact(self, name, kind):
        for installed_artifact in self.installed_artifacts.installed_artifacts:
            if installed_artifact.name == name and installed_artifact.kind == kind:
                return installed_artifact
        return None

    def __append_installed_artifact(self, installed_artifact):
        self.installed_artifacts.installed_artifacts.append(installed_artifact)

    def __remove_installed_artifact(self, installed_artifact):
        self.installed_artifacts.installed_artifacts.remove(installed_artifact)

    def __exit__(self, exc_type, exc_val, exc_tb):
        InstalledArtifacts.save_installed_artifacts(self.installed_artifacts, self.config.installed_artifacts_path)

class InstalledArtifactsDescriber(object):

    def __init__(self, config):
        self.config = config

    def describe_installed_artifacts(self, artifact_names=[]):
        if os.path.isfile(self.config.installed_artifacts_path) and os.path.getsize(self.config.installed_artifacts_path) > 0:
            installed_artifacts = InstalledArtifacts.load_installed_artifacts(self.config.installed_artifacts_path)
            installed_artifacts.installed_artifacts.insert(0, self.describe_installed_os())

            return InstalledArtifacts([
                installed_artifact for installed_artifact in installed_artifacts.installed_artifacts 
                    if not artifact_names or installed_artifact.name in artifact_names
            ]).serialize()
        else:
            installed_artifacts = InstalledArtifacts(
                ([self.describe_installed_os()] 
                    if not artifact_names or self.config.os_distro_name in artifact_names else []) +
                self.describe_installed_apps(artifact_names)
            )
            return installed_artifacts.serialize()

    def describe_installed_os(self):
        os_updater = OSUpdater(self.config.os_distro_name, self.config.ostree_gpg_verify)
        return InstalledArtifact(
            os_updater.os_distro_name, 
            ArtifactKind.OperatingSystem, 
            os_updater.get_installed_os_revision(),
            os_updater.get_rollback_os_revision()
        )

    def describe_installed_apps(self, artifact_names=[]):
        app_updater = AppUpdater(self.config.app_ostree_repo_path, self.config.ostree_gpg_verify)
        return [
            InstalledArtifact(
                name, 
                ArtifactKind.Application, 
                app_updater.get_app_deploy_revision(name),
                None
            ) for name in app_updater.list_app_names() 
                if not artifact_names or name in artifact_names
        ]