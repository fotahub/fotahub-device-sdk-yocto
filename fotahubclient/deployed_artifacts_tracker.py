import os

from fotahubclient.json_document_models import ArtifactKind, LifecycleState, DeployedArtifacts, DeployedArtifact
from fotahubclient.os_updater import OSUpdater
from fotahubclient.app_updater import AppUpdater

class DeployedArtifactsTracker(object):
 
    def __init__(self, config):
        self.config = config
        self.deployed_artifacts = DeployedArtifacts()

    def __enter__(self):
        if os.path.isfile(self.config.deployed_artifacts_path) and os.path.getsize(self.config.deployed_artifacts_path) > 0:
            self.deployed_artifacts = DeployedArtifacts.load_deployed_artifacts(self.config.deployed_artifacts_path)
        return self 

    def register_os(self, name, deployed_revision, rollback_revision=None):
        self.__register_artifact(name, ArtifactKind.operating_system, deployed_revision, rollback_revision, LifecycleState.running)

    def register_app(self, name, deployed_revision, rollback_revision=None):
        self.__register_artifact(name, ArtifactKind.application, deployed_revision, rollback_revision, LifecycleState.available)

    def register_fw(self, name, deployed_revision, rollback_revision=None):
        self.__register_artifact(name, ArtifactKind.firmware, deployed_revision, rollback_revision, LifecycleState.running)

    def __register_artifact(self, name, kind, deployed_revision, rollback_revision, lifecycle_state):
        deployed_artifact = self.__lookup_deployed_artifact(name, kind)
        if deployed_artifact is not None:
            deployed_artifact.reinit(deployed_revision, rollback_revision, lifecycle_state)
        else:
            self.__append_deployed_artifact(
                DeployedArtifact(
                    name, 
                    kind, 
                    deployed_revision,
                    rollback_revision,
                    lifecycle_state
                )
            )

    def erase_app(self, name):
        self.__erase_artifact(name, ArtifactKind.application)

    def erase_fw(self, name):
        self.__erase_artifact(name, ArtifactKind.firmware)

    def __erase_artifact(self, name, kind):
        deployed_artifact = self.__lookup_deployed_artifact(name, kind)
        if deployed_artifact is not None:
            self.__remove_deployed_artifact(deployed_artifact)

    def record_app_deployed_revision_change(self, name, deployed_revision, updating=True):
        deployed_artifact = self.__lookup_deployed_artifact(name, ArtifactKind.application)
        if deployed_artifact is not None:
            deployed_artifact.amend_revision_info(deployed_revision, updating)
        else:
            raise ValueError("Failed to record revision change for unknown application named '{}'".format(name))

    def record_fw_deployed_revision_change(self, name, deployed_revision, updating=True):
        deployed_artifact = self.__lookup_deployed_artifact(name, ArtifactKind.firmware)
        if deployed_artifact is not None:
            deployed_artifact.amend_revision_info(deployed_revision, updating)
        else:
            raise ValueError("Failed to record revision change for unknown firmware named '{}'".format(name))

    def record_app_lifecycle_status_change(self, name, lifecycle_state=None, status=True, message=None):
        deployed_artifact = self.__lookup_deployed_artifact(name, ArtifactKind.application)
        if deployed_artifact is not None:
            deployed_artifact.amend_lifecycle_info(lifecycle_state, status, message)
        else:
            raise ValueError("Failed to record lifecycle status change for unknown application named '{}'".format(name))

    def __lookup_deployed_artifact(self, name, kind):
        for deployed_artifact in self.deployed_artifacts.deployed_artifacts:
            if deployed_artifact.name == name and deployed_artifact.kind == kind:
                return deployed_artifact
        return None

    def __append_deployed_artifact(self, deployed_artifact):
        self.deployed_artifacts.deployed_artifacts.append(deployed_artifact)

    def __remove_deployed_artifact(self, deployed_artifact):
        self.deployed_artifacts.deployed_artifacts.remove(deployed_artifact)

    def __exit__(self, exc_type, exc_val, exc_tb):
        DeployedArtifacts.save_deployed_artifacts(self.deployed_artifacts, self.config.deployed_artifacts_path)

class DeployedArtifactsDescriber(object):

    def __init__(self, config):
        self.config = config

    def describe_deployed_artifacts(self, artifact_names=[]):
        if os.path.isfile(self.config.deployed_artifacts_path) and os.path.getsize(self.config.deployed_artifacts_path) > 0:
            deployed_artifacts = DeployedArtifacts.load_deployed_artifacts(self.config.deployed_artifacts_path)
            deployed_artifacts.deployed_artifacts.insert(0, self.describe_deployed_os())

            return DeployedArtifacts([
                deployed_artifact for deployed_artifact in deployed_artifacts.deployed_artifacts 
                    if not artifact_names or deployed_artifact.name in artifact_names
            ]).serialize()
        else:
            deployed_artifacts = DeployedArtifacts(
                ([self.describe_deployed_os()] 
                    if not artifact_names or self.config.os_distro_name in artifact_names else []) +
                self.describe_deployed_apps(artifact_names)
            )
            return deployed_artifacts.serialize()

    def describe_deployed_os(self):
        os_updater = OSUpdater(self.config.os_distro_name, self.config.ostree_gpg_verify)
        return DeployedArtifact(
            os_updater.os_distro_name, 
            ArtifactKind.operating_system, 
            os_updater.get_deployed_os_revision(),
            os_updater.get_rollback_os_revision()
        )

    def describe_deployed_apps(self, artifact_names=[]):
        app_updater = AppUpdater(self.config.app_ostree_repo_path, self.config.ostree_gpg_verify)
        return [
            DeployedArtifact(
                name, 
                ArtifactKind.application, 
                app_updater.get_app_deploy_revision(name),
                None
            ) for name in app_updater.list_app_names() 
                if not artifact_names or name in artifact_names
        ]