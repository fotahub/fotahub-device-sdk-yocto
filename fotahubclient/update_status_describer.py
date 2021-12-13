import os

from fotahubclient.json_document_models import UpdateStatuses

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