from functools import update_wrapper
import json
from fotahubclient.app_updater import AppUpdater

from fotahubclient.json_object_types import ArtifactKind
from fotahubclient.json_object_types import InstalledArtifacts
from fotahubclient.json_object_types import InstalledArtifactInfo
from fotahubclient.json_encode_decode import PascalCaseJSONEncoder
from fotahubclient.os_updater import OSUpdater

class InstalledArtifactsDescriber(object):

    def __init__(self, config):
        self.config = config

    def describe(self, artifact_names=[]):
        installed_artifacts = InstalledArtifacts(
            ([self.describe_installed_os()] if not artifact_names or self.config.os_distro_name in artifact_names else []) +
            self.describe_installed_apps(artifact_names)
        )
        return json.dumps(installed_artifacts, indent=4, cls=PascalCaseJSONEncoder)

    def describe_installed_os(self):
        os_updater = OSUpdater(self.config.os_distro_name, self.config.gpg_verify)
        return InstalledArtifactInfo(
            os_updater.os_distro_name, 
            ArtifactKind.OperatingSystem, 
            os_updater.get_installed_os_revision(),
            os_updater.get_rollback_os_revision()
        )

    def describe_installed_apps(self, artifact_names=[]):
        app_updater = AppUpdater(self.config.app_ostree_home, self.config.gpg_verify)
        return [
            InstalledArtifactInfo(
                name, 
                ArtifactKind.Application, 
                app_updater.resolve_installed_revision(name)
                # TODO Add rollback revision
            ) 
            for name in app_updater.list_app_names() if not artifact_names or name in artifact_names]