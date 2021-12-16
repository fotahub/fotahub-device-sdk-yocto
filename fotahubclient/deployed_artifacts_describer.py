import os

from fotahubclient.json_document_models import ArtifactKind, LifecycleState, DeployedArtifacts, DeployedArtifact
from fotahubclient.os_updater import OSUpdater
from fotahubclient.app_manager import AppManager

class DeployedArtifactsDescriber(object):

    def __init__(self, config):
        self.config = config
        self.app_manager = AppManager(self.config)

    def describe_deployed_artifacts(self, artifact_names=[]):
        if os.path.isfile(self.config.deployed_artifacts_path) and os.path.getsize(self.config.deployed_artifacts_path) > 0:
            deployed_artifacts = DeployedArtifacts.load_deployed_artifacts(self.config.deployed_artifacts_path)
            
            for deployed_artifact in deployed_artifacts.deployed_artifacts:
                if deployed_artifact.kind == ArtifactKind.application:
                    deployed_artifact.lifecycle_state = self.app_manager.get_app_lifecycle_state(deployed_artifact.name)
                    
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
            os_updater.get_rollback_os_revision(),
            LifecycleState.running
        )

    def describe_deployed_apps(self, artifact_names=[]):
        return [
            DeployedArtifact(
                name, 
                ArtifactKind.application, 
                self.app_manager.updater.get_app_deploy_revision(name),
                None,
                self.app_manager.get_app_lifecycle_state(name)
            ) for name in self.app_manager.updater.list_app_names() 
                if not artifact_names or name in artifact_names
        ]