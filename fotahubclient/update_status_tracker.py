import os

from fotahubclient.json_document_models import ArtifactKind, UpdateStatuses, UpdateStatus

class UpdateStatusTracker(object):

    def __init__(self, config):
        self.config = config
        self.update_statuses = UpdateStatuses()

    def __enter__(self):
        if os.path.isfile(self.config.update_status_path) and os.path.getsize(self.config.update_status_path) > 0:
            self.update_statuses = UpdateStatuses.load_update_statuses(self.config.update_status_path)
        return self 

    def record_os_update_status(self, revision=None, completion_state=None, status=True, message=None, save_instantly=False):
        self.__record_update_status(self.config.os_distro_name, ArtifactKind.operating_system, revision, completion_state, status, message)
        if save_instantly:
            UpdateStatuses.save_update_statuses(self.update_statuses, self.config.update_status_path, True)

    def record_app_update_status(self, name, revision=None, completion_state=None, status=True, message=None):
        self.__record_update_status(name, ArtifactKind.application, revision, completion_state, status, message)

    def record_fw_update_status(self, name, revision=None, completion_state=None, status=True, message=None):
        self.__record_update_status(name, ArtifactKind.firmware, revision, completion_state, status, message)

    def __record_update_status(self, artifact_name, artifact_kind, revision, completion_state, status, message):
        update_status = self.__lookup_update_status(artifact_name, artifact_kind)
        if update_status is not None:
            if not update_status.initiates_new_update_cycle(completion_state):
                update_status.amend(
                    revision, 
                    completion_state,
                    status,
                    message)
            else:
                update_status.reinit(
                    revision, 
                    completion_state,
                    status,
                    message)
        else:
            self.__append_update_status(
                UpdateStatus(
                    artifact_name, 
                    artifact_kind, 
                    revision,
                    None,
                    completion_state,
                    status,
                    message
                )
            )

    def get_os_update_revision(self):
        update_status = self.__lookup_update_status(self.config.os_distro_name, ArtifactKind.operating_system)
        return update_status.revision if update_status is not None else None
    
    def __lookup_update_status(self, artifact_name, artifact_kind):
        for update_status in self.update_statuses.update_statuses:
            if update_status.artifact_name == artifact_name and update_status.artifact_kind == artifact_kind:
                return update_status
        return None

    def __append_update_status(self, update_status):
        self.update_statuses.update_statuses.append(update_status)

    def __exit__(self, exc_type, exc_val, exc_tb):
        UpdateStatuses.save_update_statuses(self.update_statuses, self.config.update_status_path)
