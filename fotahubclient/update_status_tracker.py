import os
import time

from fotahubclient.json_document_models import ArtifactKind, UpdateStatuses, UpdateStatus

class UpdateStatusTracker(object):

    def __init__(self, config):
        self.config = config
        self.update_statuses = UpdateStatuses()

    def __enter__(self):
        if os.path.isfile(self.config.update_status_path) and os.path.getsize(self.config.update_status_path) > 0:
            self.update_statuses = UpdateStatuses.load_update_statuses(self.config.update_status_path)
        return self 

    def record_os_update_status(self, state=None, revision=None, status=True, message=None, save_instantly=False):
        self.__record_update_status(self.config.os_distro_name, ArtifactKind.OperatingSystem, state, revision, status, message)
        if save_instantly:
            UpdateStatuses.save_update_statuses(self.update_statuses, self.config.update_status_path, True)

    def record_app_update_status(self, name, state=None, revision=None, status=True, message=None):
        self.__record_update_status(name, ArtifactKind.Application, state, revision, status, message)

    def record_fw_update_status(self, name, state=None, revision=None, status=True, message=None):
        self.__record_update_status(name, ArtifactKind.Firmware, state, revision, status, message)

    def __record_update_status(self, artifact_name, artifact_kind, state, revision, status, message):
        update_status = self.__lookup_update_status(artifact_name, artifact_kind)
        if update_status is not None:
            if not update_status.is_final(state):
                update_status.amend(
                    revision, 
                    state,
                    status,
                    message)
            else:
                update_status.reinit(
                    revision, 
                    self.__get_utc_timestamp(),
                    state,
                    status,
                    message)
        else:
            self.__append_update_status(
                UpdateStatus(
                    artifact_name, 
                    artifact_kind, 
                    revision,
                    self.__get_utc_timestamp(),
                    state,
                    status,
                    message
                )
            )
    
    def __get_utc_timestamp(self):
        return int(time.time())

    def __lookup_update_status(self, artifact_name, artifact_kind):
        for update_status in self.update_statuses.update_statuses:
            print('artifact_name = ' + update_status.artifact_name + ' <=> ' + artifact_name)
            print('artifact_kind = ' + str(update_status.artifact_kind) + ' <=> = ' + str(artifact_kind))
            if update_status.artifact_name == artifact_name and update_status.artifact_kind == artifact_kind:
                return update_status
        return None

    def __append_update_status(self, update_status):
        self.update_statuses.update_statuses.append(update_status)

    def __exit__(self, exc_type, exc_val, exc_tb):
        UpdateStatuses.save_update_statuses(self.update_statuses, self.config.update_status_path)

class UpdateStatusDescriber(object):

    def __init__(self, config):
        self.config = config

    def describe_update_status(self, artifact_names=[]):
        if os.path.isfile(self.config.update_status_path) and os.path.getsize(self.config.update_status_path) > 0:
            update_statuses = UpdateStatuses.load_update_statuses(self.config.update_status_path)
            return UpdateStatuses([
                update_status for update_status in update_statuses.update_statuses 
                    if not artifact_names or update_status.artifact_name in artifact_names
            ]).serialize()
        else:
            return UpdateStatuses().serialize()