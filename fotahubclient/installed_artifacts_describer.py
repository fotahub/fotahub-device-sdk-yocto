from fotahubclient.json_document_models import ArtifactKind, InstalledArtifacts, InstalledArtifact
from fotahubclient.os_updater import OSUpdater
from fotahubclient.app_updater import AppUpdater

class InstalledArtifactsDescriber(object):

    def __init__(self, config):
        self.config = config

    def describe_installed_artifacts(self, artifact_names=[]):
        installed_artifacts = InstalledArtifacts(
            ([self.describe_installed_os()] if not artifact_names or self.config.os_distro_name in artifact_names else []) +
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
                app_updater.resolve_installed_revision(name)
                # TODO Add rollback revision
            ) 
            for name in app_updater.list_app_names() if not artifact_names or name in artifact_names]