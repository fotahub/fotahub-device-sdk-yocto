import os
import shutil
import logging

from fotahubclient.app_updater import AppUpdater
from fotahubclient.json_document_models import LifecycleState, UpdateState
from fotahubclient.runc_operator import RunCOperator
from fotahubclient.installed_artifacts_tracker import InstalledArtifactsTracker
from fotahubclient.update_status_tracker import UpdateStatusTracker
import fotahubclient.common_constants as constants
from fotahubclient.system_helper import touch

class AppManager(object):
    
    def __init__(self, config):
        self.logger = logging.getLogger()
        self.config = config

        self.runc = RunCOperator()
        self.updater = AppUpdater(self.config.app_ostree_repo_path, self.config.ostree_gpg_verify)

    def __to_app_install_path(self, name):
            return self.config.app_install_root + '/' + name

    def __is_app_installed(self, name):
        return os.path.isdir(self.__to_app_install_path(name))

    def __is_app_launched_automatically(self, name):
        return os.path.isfile(self.__to_app_install_path(name) + '/' + constants.APP_AUTOLAUNCH_MARKER_FILE_NAME)

    def __set_launch_app_automatically(self, name, automatic):
        marker_file = self.__to_app_install_path(name) + '/' + constants.APP_AUTOLAUNCH_MARKER_FILE_NAME
        if automatic:
            if not os.path.isfile(marker_file):
                touch(marker_file)
        else:
            if os.path.isfile(marker_file):
                os.remove(marker_file)

    def __deploy_app_revision(self, name, revision):
        self.logger.info("(Re-)deploying '{}' application revision '{}'".format(name, revision))
        self.updater.checkout_app_revision(name, revision, self.__to_app_install_path(name))

    def __apply_app_update(self, name, revision):
        self.logger.info("Applying '{}' application update to revision '{}'".format(name, revision))
        self.updater.checkout_app_revision(name, revision, self.__to_app_install_path(name))

    def __delete_app(self, name):
        if self.__is_app_installed(name):
            self.__halt_app(name)

            self.logger.info("Deleting '{}' application".format(name))
            shutil.rmtree(self.__to_app_install_path(name))

    def __launch_app(self, name):
        if self.__is_app_installed(name):
            self.logger.info("Launching '{}' application".format(name))
            self.runc.run_container(name)

    def __halt_app(self, name):
        if self.__is_app_installed(name):
            self.logger.info("Halting '{}' application".format(name))
            self.runc.delete_container(name)

    def install_and_launch_apps(self):
        with InstalledArtifactsTracker(self.config) as tracker:
            names = self.updater.list_app_names()

            install_err = False
            for name in names:
                tracker.register_app(name, self.updater.get_app_install_revision(name))
                try:
                    revision = self.updater.get_app_install_revision(name)
                    self.__deploy_app_revision(name, revision)
                    tracker.record_app_lifecycle_status_change(name, lifecycle_state=LifecycleState.ready)

                    if self.__is_app_launched_automatically(name):
                        self.__launch_app(name)
                        tracker.record_app_lifecycle_status_change(name, lifecycle_state=LifecycleState.running)
                except Exception as err:
                    tracker.record_app_lifecycle_status_change(name, status=False, message=str(err))
                    install_err = True
        
        if install_err:
            raise RuntimeError("Failed to install or launch one or several applications (run 'fotahub describe-installed-artifacts' to get more details)") 

    def configure_app(self, name, launch_automatically=True):
        self.__set_launch_app_automatically(name, launch_automatically)

    def update_app(self, name, revision):
        with InstalledArtifactsTracker(self.config) as install_tracker:
            with UpdateStatusTracker(self.config) as update_tracker:
                self.logger.info("Updating '{}' application to revision '{}'".format(name, revision))
                try:
                    self.__halt_app(name)
                    install_tracker.record_app_lifecycle_status_change(name, lifecycle_state=LifecycleState.ready)

                    self.updater.pull_app_update(name, revision)
                    update_tracker.record_app_update_status(name, state=UpdateState.downloaded, revision=revision)

                    # TODO Implement checksum/signature verification
                    update_tracker.record_app_update_status(name, state=UpdateState.verified)
                    
                    self.__apply_app_update(name, revision)
                    install_tracker.record_app_install_revision_change(name, revision, updating=True)
                    update_tracker.record_app_update_status(name, state=UpdateState.applied)

                    if self.__is_app_launched_automatically(name):
                        self.__launch_app(name)
                        install_tracker.record_app_lifecycle_status_change(name, lifecycle_state=LifecycleState.running)

                    # TODO Implement app self testing and revert app if the same fails 
                    update_tracker.record_app_update_status(name, state=UpdateState.confirmed, message='Application update successfully completed')
                except Exception as err:
                    install_tracker.record_app_lifecycle_status_change(name, status=False, message=str(err))
                    update_tracker.record_app_update_status(name, revision=revision, status=False, message=str(err))
                    raise RuntimeError("Failed to update '{}' application".format(name)) from err

    def revert_app(self, name):
        revision = self.updater.get_app_rollback_revision(name, self.config.installed_artifacts_path)
        if revision is None:
             raise RuntimeError("Cannot revert update for '{}' application before any such has been installed".format(name))
        
        with InstalledArtifactsTracker(self.config) as install_tracker:
            with UpdateStatusTracker(self.config) as update_tracker:
                self.logger.info("Reverting '{}' application to revision '{}'".format(name, revision))
                try:
                    self.__halt_app(name)
                    install_tracker.record_app_lifecycle_status_change(name, lifecycle_state=LifecycleState.ready)

                    self.__deploy_app_revision(name, revision)
                    install_tracker.record_app_install_revision_change(name, revision, updating=False)

                    if self.__is_app_launched_automatically(name):
                        self.__launch_app(name)
                        install_tracker.record_app_lifecycle_status_change(name, lifecycle_state=LifecycleState.running)

                    update_tracker.record_app_update_status(name, state=UpdateState.reverted, message='Update reverted due to application-level or external request')
                except Exception as err:
                    install_tracker.record_app_lifecycle_status_change(name, status=False, message=str(err))
                    update_tracker.record_app_update_status(name, revision=revision, status=False, message=str(err))
                    raise RuntimeError("Failed to revert '{}' application".format(name)) from err

    def delete_app(self, name):
        with InstalledArtifactsTracker(self.config) as tracker:
            try:
                self.__delete_app(name)
                tracker.erase_app(name)
            except Exception as err:
                tracker.record_app_lifecycle_status_change(name, status=False, message=str(err))
                raise RuntimeError("Failed to delete '{}' application") from err