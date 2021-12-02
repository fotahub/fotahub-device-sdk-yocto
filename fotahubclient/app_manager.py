import os
import shutil
import logging

from fotahubclient.app_updater import AppUpdater
from fotahubclient.json_document_models import LifecycleState, UpdateState
from fotahubclient.runc_operator import RunCOperator
from fotahubclient.deployed_artifacts_tracker import DeployedArtifactsTracker
from fotahubclient.update_status_tracker import UpdateStatusTracker
import fotahubclient.common_constants as constants
from fotahubclient.system_helper import touch

class AppManager(object):
    
    def __init__(self, config):
        self.logger = logging.getLogger()
        self.config = config

        self.runc = RunCOperator()
        self.updater = AppUpdater(self.config.app_ostree_repo_path, self.config.ostree_gpg_verify)

    def __to_app_deploy_path(self, name):
            return self.config.app_deploy_root + '/' + name

    def __is_app_deployed(self, name):
        return os.path.isdir(self.__to_app_deploy_path(name))

    def __is_run_app_automatically(self, name):
        return os.path.isfile(self.__to_app_deploy_path(name) + '/' + constants.APP_AUTORUN_MARKER_FILE_NAME)

    def __set_run_app_automatically(self, name, automatic):
        marker_file = self.__to_app_deploy_path(name) + '/' + constants.APP_AUTORUN_MARKER_FILE_NAME
        if automatic:
            if not os.path.isfile(marker_file):
                touch(marker_file)
        else:
            if os.path.isfile(marker_file):
                os.remove(marker_file)

    def __deploy_app_revision(self, name, revision):
        self.logger.info("Deploying '{}' application revision '{}'".format(name, revision))
        self.updater.checkout_app_revision(name, revision, self.__to_app_deploy_path(name))

    def __apply_app_update(self, name, revision):
        self.logger.info("Applying '{}' application update to revision '{}'".format(name, revision))
        self.updater.checkout_app_revision(name, revision, self.__to_app_deploy_path(name))

    def __delete_app(self, name):
        if self.__is_app_deployed(name):
            self.__halt_app(name)

            self.logger.info("Deleting '{}' application".format(name))
            shutil.rmtree(self.__to_app_deploy_path(name))

    def __run_app(self, name):
        if self.__is_app_deployed(name):
            self.logger.info("Running '{}' application".format(name))
            self.runc.run_container(name, self.__to_app_deploy_path(name))

    def __halt_app(self, name):
        if self.__is_app_deployed(name):
            self.logger.info("Halting '{}' application".format(name))
            self.runc.delete_container(name)

    def configure_app(self, name, run_automatically=True):
        self.__set_run_app_automatically(name, run_automatically)

    def deploy_and_run_apps(self):
        with DeployedArtifactsTracker(self.config) as tracker:
            names = self.updater.list_app_names()

            deploy_err = False
            for name in names:
                revision = self.updater.get_app_deploy_revision(name)
                tracker.register_app(name, revision)
                try:
                    self.__deploy_app_revision(name, revision)
                    tracker.record_app_lifecycle_status_change(name, lifecycle_state=LifecycleState.ready)

                    if self.__is_run_app_automatically(name):
                        self.__run_app(name)
                        tracker.record_app_lifecycle_status_change(name, lifecycle_state=LifecycleState.running)
                except Exception as err:
                    tracker.record_app_lifecycle_status_change(name, status=False, message=str(err))
                    deploy_err = True
        
        if deploy_err:
            raise RuntimeError("Failed to deploy or run one or several applications (run 'fotahub describe-deployed-artifacts' to get more details)") 

    def run_app(self, name):
        with DeployedArtifactsTracker(self.config) as deploy_tracker:
            try:
                self.__run_app(name)
                deploy_tracker.record_app_lifecycle_status_change(name, lifecycle_state=LifecycleState.running)
            except Exception as err:
                deploy_tracker.record_app_lifecycle_status_change(name, status=False, message=str(err))
                raise RuntimeError("Failed to run '{}' application".format(name)) from err

    def halt_app(self, name):
        with DeployedArtifactsTracker(self.config) as deploy_tracker:
            try:
                self.__halt_app(name)
                deploy_tracker.record_app_lifecycle_status_change(name, lifecycle_state=LifecycleState.ready)
            except Exception as err:
                deploy_tracker.record_app_lifecycle_status_change(name, status=False, message=str(err))
                raise RuntimeError("Failed to halt '{}' application".format(name)) from err

    def update_app(self, name, revision):
        with DeployedArtifactsTracker(self.config) as deploy_tracker:
            with UpdateStatusTracker(self.config) as update_tracker:
                self.logger.info("Updating '{}' application to revision '{}'".format(name, revision))
                try:
                    self.__halt_app(name)
                    deploy_tracker.record_app_lifecycle_status_change(name, lifecycle_state=LifecycleState.ready)

                    self.updater.pull_app_update(name, revision)
                    update_tracker.record_app_update_status(name, state=UpdateState.downloaded, revision=revision)

                    # TODO Implement checksum/signature verification
                    update_tracker.record_app_update_status(name, state=UpdateState.verified)
                    
                    self.__apply_app_update(name, revision)
                    deploy_tracker.record_app_deployed_revision_change(name, revision, updating=True)
                    update_tracker.record_app_update_status(name, state=UpdateState.applied)

                    if self.__is_run_app_automatically(name):
                        self.__run_app(name)
                        deploy_tracker.record_app_lifecycle_status_change(name, lifecycle_state=LifecycleState.running)

                    # TODO Implement app self testing and roll back app if the same fails 
                    update_tracker.record_app_update_status(name, state=UpdateState.confirmed, message='Application update successfully completed')
                except Exception as err:
                    deploy_tracker.record_app_lifecycle_status_change(name, status=False, message=str(err))
                    update_tracker.record_app_update_status(name, revision=revision, status=False, message=str(err))
                    raise RuntimeError("Failed to update '{}' application".format(name)) from err

    def roll_back_app(self, name):
        revision = self.updater.get_app_rollback_revision(name, self.config.deployed_artifacts_path)
        if not revision:
             raise RuntimeError("Cannot roll back update for '{}' application before any such has been deployed".format(name))
        
        with DeployedArtifactsTracker(self.config) as deploy_tracker:
            with UpdateStatusTracker(self.config) as update_tracker:
                self.logger.info("Rolling back '{}' application to revision '{}'".format(name, revision))
                try:
                    self.__halt_app(name)
                    deploy_tracker.record_app_lifecycle_status_change(name, lifecycle_state=LifecycleState.ready)

                    self.__deploy_app_revision(name, revision)
                    deploy_tracker.record_app_deployed_revision_change(name, revision, updating=False)

                    if self.__is_run_app_automatically(name):
                        self.__run_app(name)
                        deploy_tracker.record_app_lifecycle_status_change(name, lifecycle_state=LifecycleState.running)

                    update_tracker.record_app_update_status(name, state=UpdateState.rolled_back, message='Update roll backed due to application-level or external request')
                except Exception as err:
                    deploy_tracker.record_app_lifecycle_status_change(name, status=False, message=str(err))
                    update_tracker.record_app_update_status(name, revision=revision, status=False, message=str(err))
                    raise RuntimeError("Failed to roll back '{}' application".format(name)) from err

    def delete_app(self, name):
        with DeployedArtifactsTracker(self.config) as tracker:
            try:
                self.__delete_app(name)
                tracker.erase_app(name)
            except Exception as err:
                tracker.record_app_lifecycle_status_change(name, status=False, message=str(err))
                raise RuntimeError("Failed to delete '{}' application") from err