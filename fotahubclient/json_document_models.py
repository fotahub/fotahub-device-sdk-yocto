from enum import Enum
import json
import os

from fotahubclient.json_encode_decode import PascalCaseJSONEncoder, PascalCasedObjectArrayJSONDecoder

class ArtifactKind(Enum):
    OperatingSystem = 1
    Application = 2
    Firmware = 3

class LifecycleState(Enum):
    available = 1
    ready = 2
    running = 3
    finished = 4

class UpdateState(Enum):
    downloaded = 1
    verified = 2
    applied = 3
    confirmed = 4 
    rolled_back = 5

    def is_final(self, next_state):
        return self == UpdateState.confirmed and next_state != UpdateState.rolled_back or self == UpdateState.rolled_back

class DeployedArtifact(object):
    def __init__(self, name, kind, deployed_revision, rollback_revision=None, lifecycle_state=LifecycleState.running, status=True, message=None):
        self.name = name
        self.kind = kind
        self.deployed_revision = deployed_revision
        self.rollback_revision = rollback_revision
        self.lifecycle_state = lifecycle_state
        self.status = status
        self.message = message

    def reinit(self, deployed_revision, rollback_revision=None, lifecycle_state=LifecycleState.running):
        self.deployed_revision = deployed_revision
        if rollback_revision:
            self.rollback_revision = rollback_revision
        self.lifecycle_state = lifecycle_state
        self.status = True
        self.message = None

    def amend_revision_info(self, deployed_revision, updating=True):
        if updating:
            self.rollback_revision = self.deployed_revision
            self.deployed_revision = deployed_revision
        else:
            self.deployed_revision = deployed_revision
            self.rollback_revision = None

    def amend_lifecycle_info(self, lifecycle_state=None, status=True, message=None):
        if lifecycle_state is not None:
            self.lifecycle_state = lifecycle_state
        self.status = status
        if not self.message:
            self.message = message

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
    def __init__(self, artifact_name, artifact_kind, revision, deploy_timestamp, state=UpdateState.downloaded, status=True, message=None):
        self.artifact_name = artifact_name
        self.artifact_kind = artifact_kind
        self.revision = revision
        self.deploy_timestamp = deploy_timestamp
        self.state = state
        self.status = status
        self.message = message

    def reinit(self, revision, deploy_timestamp, state=UpdateState.downloaded, status=True, message=None):
        self.revision = revision
        self.deploy_timestamp = deploy_timestamp
        self.state = state
        self.status = status
        self.message = message

    def amend(self, revision, state, status=True, message=None):
        if not self.revision:
            self.revision = revision
        if state is not None:
            self.state = state
        self.status = status
        if not self.message:
            self.message = message

    def is_final(self, next_state):
        return (self.state and self.state.is_final(next_state)) or not self.status

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
        super().__init__(UpdateStatuses, UpdateStatus, [ArtifactKind, UpdateState])