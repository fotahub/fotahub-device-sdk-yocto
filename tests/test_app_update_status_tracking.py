import json
import time
import tempfile

from fotahubclient.config_loader import ConfigLoader
from fotahubclient.json_document_models import UpdateCompletionState
from fotahubclient.update_status_tracker import UpdateStatusTracker

def test_app_update_status__consecutive_updates():
    with tempfile.NamedTemporaryFile() as temp:
        config = ConfigLoader()
        config.update_status_path = temp.name
        
        app_name = 'my-app'
        
        # First app update

        with UpdateStatusTracker(config) as tracker:
            tracker.record_app_update_status(app_name, revision='3fa209348038674d5e701515d3e26746b18c2cbf555044d4f93f8c424e3642d8', completion_state=UpdateCompletionState.initiated)
            tracker.record_app_update_status(app_name, completion_state=UpdateCompletionState.downloaded)
            tracker.record_app_update_status(app_name, completion_state=UpdateCompletionState.verified)
            tracker.record_app_update_status(app_name, completion_state=UpdateCompletionState.applied)
            tracker.record_app_update_status(app_name, completion_state=UpdateCompletionState.confirmed, message='Application update successfully completed')

        temp.seek(0)
        json_data = json.load(temp)
        assert 'UpdateStatuses' in json_data
        assert len(json_data['UpdateStatuses']) == 1
        update_status_data = json_data['UpdateStatuses'][0]
        assert update_status_data['ArtifactName'] == app_name
        assert update_status_data['ArtifactKind'] == 'Application'
        assert update_status_data['Revision'] == '3fa209348038674d5e701515d3e26746b18c2cbf555044d4f93f8c424e3642d8'
        assert type(update_status_data['Timestamp']) == int
        assert update_status_data['Timestamp'] - int(time.time()) < 1
        assert update_status_data['CompletionState'] == 'Confirmed'
        assert type(update_status_data['Status']) == bool
        assert update_status_data['Status'] == True
        assert update_status_data['Message'] == 'Application update successfully completed'

        # Second app update

        with UpdateStatusTracker(config) as tracker:
            tracker.record_app_update_status(app_name, revision='46a89ce4ecbcd0c8f53f34e53c6fd4736ec21019487ee9525933596d2be72fbd', completion_state=UpdateCompletionState.initiated)
            tracker.record_app_update_status(app_name, completion_state=UpdateCompletionState.downloaded)
            tracker.record_app_update_status(app_name, completion_state=UpdateCompletionState.verified)
            tracker.record_app_update_status(app_name, completion_state=UpdateCompletionState.applied)
            tracker.record_app_update_status(app_name, completion_state=UpdateCompletionState.confirmed, message='Application update successfully completed')

        temp.seek(0)
        json_data = json.load(temp)
        assert 'UpdateStatuses' in json_data
        assert len(json_data['UpdateStatuses']) == 1
        update_status_data = json_data['UpdateStatuses'][0]
        assert update_status_data['ArtifactName'] == app_name
        assert update_status_data['ArtifactKind'] == 'Application'
        assert update_status_data['Revision'] == '46a89ce4ecbcd0c8f53f34e53c6fd4736ec21019487ee9525933596d2be72fbd'
        assert type(update_status_data['Timestamp']) == int
        assert update_status_data['Timestamp'] - int(time.time()) < 1
        assert update_status_data['CompletionState'] == 'Confirmed'
        assert type(update_status_data['Status']) == bool
        assert update_status_data['Status'] == True
        assert update_status_data['Message'] == 'Application update successfully completed'

def test_app_update_status__update_rollback():
    with tempfile.NamedTemporaryFile() as temp:
        config = ConfigLoader()
        config.update_status_path = temp.name
        
        app_name = 'my-app'

        # App update
        
        with UpdateStatusTracker(config) as tracker:
            tracker.record_app_update_status(app_name, revision='3fa209348038674d5e701515d3e26746b18c2cbf555044d4f93f8c424e3642d8', completion_state=UpdateCompletionState.initiated)
            tracker.record_app_update_status(app_name, completion_state=UpdateCompletionState.downloaded)
            tracker.record_app_update_status(app_name, completion_state=UpdateCompletionState.verified)
            tracker.record_app_update_status(app_name, completion_state=UpdateCompletionState.applied)
            tracker.record_app_update_status(app_name, completion_state=UpdateCompletionState.confirmed, message='Application update successfully completed')

        temp.seek(0)
        json_data = json.load(temp)
        assert 'UpdateStatuses' in json_data
        assert len(json_data['UpdateStatuses']) == 1
        update_status_data = json_data['UpdateStatuses'][0]
        assert update_status_data['ArtifactName'] == app_name
        assert update_status_data['ArtifactKind'] == 'Application'
        assert update_status_data['Revision'] == '3fa209348038674d5e701515d3e26746b18c2cbf555044d4f93f8c424e3642d8'
        assert type(update_status_data['Timestamp']) == int
        assert update_status_data['Timestamp'] - int(time.time()) < 1
        assert update_status_data['CompletionState'] == 'Confirmed'
        assert type(update_status_data['Status']) == bool
        assert update_status_data['Status'] == True
        assert update_status_data['Message'] == 'Application update successfully completed'

        # App rollback

        with UpdateStatusTracker(config) as tracker:
            tracker.record_app_update_status(app_name, completion_state=UpdateCompletionState.invalidated)
            tracker.record_app_update_status(app_name, completion_state=UpdateCompletionState.rolled_back, message='Update rolled back due to application-level or external request')

        temp.seek(0)
        json_data = json.load(temp)
        assert 'UpdateStatuses' in json_data
        assert len(json_data['UpdateStatuses']) == 1
        update_status_data = json_data['UpdateStatuses'][0]
        assert update_status_data['ArtifactName'] == app_name
        assert update_status_data['ArtifactKind'] == 'Application'
        assert update_status_data['Revision'] == '3fa209348038674d5e701515d3e26746b18c2cbf555044d4f93f8c424e3642d8'
        assert type(update_status_data['Timestamp']) == int
        assert update_status_data['Timestamp'] - int(time.time()) < 1
        assert update_status_data['CompletionState'] == 'RolledBack'
        assert type(update_status_data['Status']) == bool
        assert update_status_data['Status'] == True
        assert update_status_data['Message'] == 'Update rolled back due to application-level or external request'