import subprocess
import logging
import shlex

from fotahubclient.os_updater import OSUpdater
from fotahubclient.system_helper import run_hook_command
from fotahubclient.update_status_tracker import UpdateStatusTracker
from fotahubclient.json_document_models import UpdateState

class OSUpdateInitiator(object):

    def __init__(self, config):
        self.logger = logging.getLogger()
        self.config = config

    def initiate_os_update(self, revision, max_reboot_failures):
        with UpdateStatusTracker(self.config) as tracker:
            try:
                updater = OSUpdater(self.config.os_distro_name, self.config.ostree_gpg_verify)
                updater.pull_os_update(revision)
                tracker.record_os_update_status(state=UpdateState.downloaded, revision=revision)

                [success, message] = run_hook_command('OS update verification', self.config.os_update_verification_command, revision)
                if success:
                    tracker.record_os_update_status(state=UpdateState.verified, revision=revision, save_instantly=True)
                    updater.apply_os_update(revision, max_reboot_failures)
                else:
                    raise RuntimeError(message)

            except Exception as err:
                tracker.record_os_update_status(revision=revision, status=False, message=str(err))
                raise err

class OSUpdateReverter(object):

    def __init__(self, config):
        self.logger = logging.getLogger()
        self.config = config

    def revert_os_update(self):
        with UpdateStatusTracker(self.config) as tracker:
            try:
                updater = OSUpdater(self.config.os_distro_name, self.config.ostree_gpg_verify)
                tracker.record_os_update_status(message='Update reverted due to application-level or external request', save_instantly=True)
                updater.revert_os_update()
            except Exception as err:
                tracker.record_os_update_status(status=False, message=str(err))
                raise err

class OSUpdateFinalizer(object):

    def __init__(self, config):
        self.logger = logging.getLogger()
        self.config = config

    def finalize_os_update(self):
        with UpdateStatusTracker(self.config) as tracker:
            try:
                updater = OSUpdater(self.config.os_distro_name, self.config.ostree_gpg_verify)
                self.logger.info("Booted OS revision: {}".format(updater.get_installed_os_revision()))
                
                if updater.is_applying_os_update():
                    tracker.record_os_update_status(state=UpdateState.applied)

                    [success, message] = run_hook_command('OS update self test', self.config.os_update_self_test_command)
                    if success:
                        updater.confirm_os_update()
                        tracker.record_os_update_status(state=UpdateState.confirmed)
                    else:
                        tracker.record_os_update_status(message=message, save_instantly=True)
                        updater.revert_os_update()
                
                elif updater.is_reverting_os_update():
                    tracker.record_os_update_status(state=UpdateState.reverted, revision=updater.get_pending_os_revision())
                    updater.discard_os_update()
                
                else:
                    self.logger.info('No OS update or rollback in progress, nothing to do')
            except Exception as err:
                tracker.record_os_update_status(status=False, message=str(err))
                raise err
