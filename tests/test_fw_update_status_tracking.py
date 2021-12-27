import json
import time
import tempfile

from fotahubclient.config_loader import ConfigLoader
from fotahubclient.json_document_models import UpdateCompletionState
from fotahubclient.update_status_tracker import UpdateStatusTracker

def test_fw_update_status__update_initiation():
    with tempfile.NamedTemporaryFile() as temp:
        config = ConfigLoader()
        config.update_status_path = temp.name
        
        fw_name = 'my-firmware'
        fw_version = '1.0.0'
        
        with UpdateStatusTracker(config) as tracker:
            tracker.record_fw_update_status(fw_name, revision=fw_version, completion_state=UpdateCompletionState.initiated)

        temp.seek(0)
        json_data = json.load(temp)
        assert 'UpdateStatuses' in json_data
        assert len(json_data['UpdateStatuses']) == 1
        update_status_data = json_data['UpdateStatuses'][0]
        assert update_status_data['ArtifactName'] == fw_name
        assert update_status_data['ArtifactKind'] == 'Firmware'
        assert update_status_data['Revision'] == fw_version
        assert type(update_status_data['Timestamp']) == int
        assert update_status_data['Timestamp'] - int(time.time()) < 1
        assert update_status_data['CompletionState'] == 'Initiated'
        assert type(update_status_data['Status']) == bool
        assert update_status_data['Status'] == True
        assert update_status_data['Message'] == ''