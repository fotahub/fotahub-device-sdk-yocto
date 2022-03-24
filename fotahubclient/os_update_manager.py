import logging

from fotahubclient.os_updater import OSUpdater
from fotahubclient.system_helper import run_command
from fotahubclient.update_status_tracker import UpdateStatusTracker
from fotahubclient.json_document_models import UpdateCompletionState
from fotahubclient.system_helper import reboot_system

class OSUpdateError(Exception):
    pass

class OSUpdateManager(object):

    def __init__(self, config):
        self.logger = logging.getLogger()
        self.config = config
        
        self.updater = OSUpdater(self.config.os_distro_name, self.config.ostree_gpg_verify)

    def initiate_os_update(self, revision, max_reboot_failures):
        with UpdateStatusTracker(self.config) as tracker:
            try:
                tracker.record_os_update_status(revision=revision, completion_state=UpdateCompletionState.initiated)

                self.updater.pull_os_update(revision)
                tracker.record_os_update_status(completion_state=UpdateCompletionState.downloaded)

                [success, message] = run_command('OS update verification', self.config.os_update_verification_command, revision)
                if success:
                    tracker.record_os_update_status(completion_state=UpdateCompletionState.verified, save_instantly=True)
                    self.updater.apply_os_update(revision, max_reboot_failures)
                    reboot_system(self.config.os_reboot_options)
                else:
                    raise OSUpdateError(message)

            except Exception as err:
                tracker.record_os_update_status(status=False, message=str(err))
                raise err

    def roll_back_os_update(self):
        with UpdateStatusTracker(self.config) as tracker:
            try:
                tracker.record_os_update_status(completion_state=UpdateCompletionState.invalidated, save_instantly=True)
                self.updater.roll_back_os_update()
                reboot_system(self.config.os_reboot_options)
            except Exception as err:
                tracker.record_os_update_status(status=False, message=str(err))
                raise err

    def finalize_os_update(self):
        with UpdateStatusTracker(self.config) as tracker:
            try:
                deployed_revision = self.updater.get_deployed_os_revision()
                update_revision = tracker.get_os_update_revision()
                self.logger.info("Booted OS revision: {}".format(deployed_revision))
                
                if self.updater.is_applying_os_update():
                    if deployed_revision == update_revision:
                        tracker.record_os_update_status(completion_state=UpdateCompletionState.applied)
                    else:
                        self.updater.discard_os_update()
                        raise OSUpdateError("Failed to apply OS revision '{}'".format(update_revision))

                    [success, message] = run_command('OS update self test', self.config.os_update_self_test_command)
                    if success:
                        self.updater.confirm_os_update()
                        tracker.record_os_update_status(completion_state=UpdateCompletionState.confirmed, message='OS update successfully completed')
                    else:
                        tracker.record_os_update_status(message=message, save_instantly=True)
                        self.updater.roll_back_os_update()
                        reboot_system(self.config.os_reboot_options)
                
                elif self.updater.is_rolling_back_os_update():
                    if deployed_revision != update_revision:
                        self.updater.discard_os_update()
                        tracker.record_os_update_status(completion_state=UpdateCompletionState.rolled_back, message='Update rolled back due to application-level or external request')
                    else:
                        self.updater.discard_os_update()
                        raise OSUpdateError("Failed to roll back OS revision '{}'".format(update_revision))
                
                else:
                    self.logger.info('No OS update or rollback in progress, nothing to do')
            except Exception as err:
                tracker.record_os_update_status(status=False, message=str(err))
                raise err
