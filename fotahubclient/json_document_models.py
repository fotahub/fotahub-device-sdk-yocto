from enum import Enum
import json
import os
import time
import logging

from fotahubclient.json_encode_decode import PascalCaseJSONEncoder, PascalCasedObjectArrayJSONDecoder

class ArtifactKind(Enum):
    operating_system = 'OperatingSystem'
    application = 'Application'
    firmware = 'Firmware'

    def __str__(self):
        return self.value

class LifecycleState(Enum):
    available = 'Available'
    ready = 'Ready'
    running = 'Running'
    finished = 'Finished'

    def __str__(self):
        return self.value

    def initiates_new_lifecycle(self, next_state):
        return next_state == LifecycleState.ready
        
class UpdateCompletionState(Enum):
    initiated = 'Initiated'
    downloaded = 'Downloaded'
    verified = 'Verified'
    applied = 'Applied'
    confirmed = 'Confirmed' 
    rolled_back = 'RolledBack'

    def __str__(self):
        return self.value

class DeployedArtifact(object):
    def __init__(self, name, kind, deployed_revision, rollback_revision=None, lifecycle_state=LifecycleState.running, status=True, message=None):
        logging.getLogger().debug("Initializing deployed artifact info: name={}, kind={}, deployed_revision={}, rollback_revision={}, lifecycle_state={}, status={}, message={}".format(name, kind, deployed_revision, rollback_revision, lifecycle_state, status, message))
        self.name = name
        self.kind = kind
        self.deployed_revision = deployed_revision
        self.rollback_revision = rollback_revision
        self.lifecycle_state = lifecycle_state
        self.status = status
        self.message = message

    def reinit(self, deployed_revision, rollback_revision=None, lifecycle_state=LifecycleState.running):
        logging.getLogger().debug("Reinitializing deployed artifact info for '{}': deployed_revision={}, rollback_revision={}, lifecycle_state={}".format(self.name, deployed_revision, rollback_revision, lifecycle_state))
        self.deployed_revision = deployed_revision
        if rollback_revision:
            self.rollback_revision = rollback_revision
        self.lifecycle_state = lifecycle_state
        self.status = True
        self.message = None

    def amend_revision_info(self, deployed_revision, updating=True):
        logging.getLogger().debug("Amending revision info for '{}': deployed_revision={}".format(self.name, deployed_revision))
        if updating:
            self.rollback_revision = self.deployed_revision
            self.deployed_revision = deployed_revision
        else:
            self.deployed_revision = deployed_revision
            self.rollback_revision = None

    def amend_lifecycle_info(self, lifecycle_state=None, status=True, message=None):
        logging.getLogger().debug("Amending lifecycle info for '{}': lifecycle_state={}, status={}, message={}".format(self.name, lifecycle_state, status, message))
        # Keep/store latest non-empty message reported during current lifecycle, reinitialize it otherwise 
        # !! Important Note !! Evaluate current lifecycle state *before* amending it
        if message or (self.lifecycle_state is not None and self.lifecycle_state.initiates_new_lifecycle(lifecycle_state)):
            self.message = message
        # Keep/store latest lifecycle state
        if lifecycle_state is not None:
            self.lifecycle_state = lifecycle_state
        # Store latest status
        self.status = status

class DeployedArtifacts(object):
    def __init__(self, deployed_artifacts=None):
        self.deployed_artifacts = deployed_artifacts if deployed_artifacts is not None else []

    def serialize(self):
        return json.dumps(self, indent=4, cls=PascalCaseJSONEncoder)

    @staticmethod
    def load_deployed_artifacts(path):
        with open(path) as file:
            return json.load(file, cls=DeployedArtifactsJSONDecoder)

    @staticmethod
    def save_deployed_artifacts(deployed_artifacts, path):
        parent = os.path.dirname(path)
        if not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)

        with open(path, 'w+', encoding='utf-8') as file:
            json.dump(deployed_artifacts, file, ensure_ascii=False, indent=4, cls=PascalCaseJSONEncoder)

class DeployedArtifactsJSONDecoder(PascalCasedObjectArrayJSONDecoder):
    def __init__(self):
        super().__init__(DeployedArtifacts, DeployedArtifact, [ArtifactKind, LifecycleState])

class UpdateStatus(object):
    def __init__(self, artifact_name, artifact_kind, revision, timestamp=None, completion_state=UpdateCompletionState.downloaded, status=True, message=None):
        logging.getLogger().debug("Initializing update status: artifact_name={}, artifact_kind={}, revision={}, completion_state={}, status={}, message={}".format(artifact_name, artifact_kind, revision, completion_state, status, message))
        self.artifact_name = artifact_name
        self.artifact_kind = artifact_kind
        self.revision = revision
        self.timestamp = timestamp if timestamp is not None else self.__get_utc_timestamp()
        self.completion_state = completion_state
        self.status = status
        self.message = message

    def reinit(self, revision, completion_state=UpdateCompletionState.downloaded, status=True, message=None):
        logging.getLogger().debug("Reinitializing update status for '{}': revision={}, completion_state={}, status={}, message={}".format(self.artifact_name, revision, completion_state, status, message))
        self.revision = revision
        self.timestamp = self.__get_utc_timestamp()
        self.completion_state = completion_state
        self.status = status
        self.message = message

    def amend(self, revision, completion_state, status=True, message=None):
        logging.getLogger().debug("Amending update status for '{}': revision={}, completion_state={}, status={}, message={}".format(self.artifact_name, revision, completion_state, status, message))
        # Keep first revision reported during current update/rollback cycle 
        if not self.revision:
            self.revision = revision
        # Renew timestamp when rollback starts, keep existime timestamp otherwise
        if self.initiates_rollback_cycle(completion_state):
            self.timestamp = self.__get_utc_timestamp()
        # Keep first non-empty message reported during current update/rollback cycle, reinitialize/reassign it otherwise 
        # !! Important Note !! Evaluate current completion state *before* amending it
        if not self.message or self.initiates_rollback_cycle(completion_state):
            self.message = message
        # Keep/store latest completion state
        if completion_state is not None:
            self.completion_state = completion_state
        # Store latest status
        self.status = status

    def __get_utc_timestamp(self):
        return int(time.time())

    def initiates_rollback_cycle(self, next_state):
        return self.completion_state == UpdateCompletionState.confirmed and next_state == UpdateCompletionState.rolled_back

    def initiates_new_update_cycle(self, next_state):
        if type(self.completion_state) is not UpdateCompletionState:
            return True

        if self.completion_state == UpdateCompletionState.confirmed and next_state != UpdateCompletionState.rolled_back:
            return True
        if self.completion_state == UpdateCompletionState.rolled_back:
            return True
        if not self.status:
            return True
        return False

class UpdateStatuses(object):
    def __init__(self, update_statuses=None):
        self.update_statuses = update_statuses if update_statuses is not None else []

    def serialize(self):
        return json.dumps(self, indent=4, cls=PascalCaseJSONEncoder)

    @staticmethod
    def load_update_statuses(path):
        with open(path) as file:
            return json.load(file, cls=UpdateStatusesJSONDecoder)

    @staticmethod
    def save_update_statuses(update_statuses, path, flush_instantly=False):
        parent = os.path.dirname(path)
        if not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)

        with open(path, 'w+', encoding='utf-8') as file:
            json.dump(update_statuses, file, ensure_ascii=False, indent=4, cls=PascalCaseJSONEncoder)
            
            if flush_instantly:
                # Flush the Python runtime's internal buffers
                file.flush()

                # Synchronize the operating system's buffers with file content on disk
                os.fsync(file.fileno())

class UpdateStatusesJSONDecoder(PascalCasedObjectArrayJSONDecoder):
    def __init__(self):
        super().__init__(UpdateStatuses, UpdateStatus, [ArtifactKind, UpdateCompletionState])