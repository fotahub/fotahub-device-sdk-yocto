import os
import shutil
import logging
from enum import Enum

from fotahubclient.app_updater import AppUpdater
from fotahubclient.json_document_models import LifecycleState, UpdateCompletionState
from fotahubclient.runc_operator import RunCOperator
from fotahubclient.deployed_artifacts_tracker import DeployedArtifactsTracker
from fotahubclient.update_status_tracker import UpdateStatusTracker
import fotahubclient.common_constants as constants
from fotahubclient.system_helper import touch
from fotahubclient.runc_operator import RunCOperator, ContainerState

class AppUpdateError(Exception):
    pass

def container_state_to_lifecycle_state(container_state, none_equivalent):
    if container_state is ContainerState.created:
        return LifecycleState.ready
    elif container_state is ContainerState.running:
        return LifecycleState.running
    elif container_state is ContainerState.stopped:
        return LifecycleState.finished
    elif container_state is None:
        return none_equivalent
    else:
        raise ValueError("Unknown container state: {}".format(container_state))

class AppRunMode(Enum):
    automatic = 'automatic'
    manual = 'manual'

    def __str__(self):
        return self.value

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

    def __run_app(self, name):
        if not self.__is_app_deployed(name):
            raise ValueError("Application '{}' not found".format(name))

        self.logger.info("Running '{}' application".format(name))
        [container_state, message] = self.runc.run_container(name, self.__to_app_deploy_path(name))
        return [container_state_to_lifecycle_state(container_state, LifecycleState.ready), message]

    def __get_app_lifecycle_state(self, name):
        if not self.__is_app_deployed(name):
            raise ValueError("Application '{}' not found".format(name))

        self.logger.info("Retrieving '{}' application lifecycle state".format(name))
        container_state = self.runc.get_container_state(name)
        return container_state_to_lifecycle_state(container_state, LifecycleState.ready)

    def __read_app_logs(self, name, max_lines):
        if not self.__is_app_deployed(name):
            raise ValueError("Application '{}' not found".format(name))

        self.logger.info("Reading '{}' application logs".format(name))
        return self.runc.read_container_logs(self.__to_app_deploy_path(name), max_lines)

    def __halt_app(self, name):
        if not self.__is_app_deployed(name):
            raise ValueError("Application '{}' not found".format(name))

        self.logger.info("Halting '{}' application".format(name))
        self.runc.delete_container(name)

    def __delete_app(self, name):
        self.__halt_app(name)

        self.logger.info("Deleting '{}' application".format(name))
        shutil.rmtree(self.__to_app_deploy_path(name))

    def deploy_and_run_apps(self):
        with DeployedArtifactsTracker(self.config) as tracker:
            names = self.updater.list_app_names()

            deploy_err = False
            if names:
                self.logger.info("Deploying and launching applications")
            for name in names:
                revision = self.updater.get_app_deploy_revision(name)
                tracker.register_app(name, revision)
                try:
                    self.__deploy_app_revision(name, revision)
                    tracker.record_app_lifecycle_status_change(name, lifecycle_state=LifecycleState.ready)

                    if self.__is_run_app_automatically(name):
                        [lifecycle_state, message] = self.__run_app(name)
                        tracker.record_app_lifecycle_status_change(name, lifecycle_state=lifecycle_state, message=message)
                except Exception as err:
                    tracker.record_app_lifecycle_status_change(name, status=False, message=str(err))
                    deploy_err = True
        
        if deploy_err:
            raise AppUpdateError("Failed to deploy or run one or several applications (run 'fotahub describe-deployed-artifacts' to get more details)") 

    def configure_app(self, name, run_mode=AppRunMode.automatic):
        self.__set_run_app_automatically(name, run_mode == AppRunMode.automatic)

    def run_app(self, name):
        with DeployedArtifactsTracker(self.config) as deploy_tracker:
            try:
                [lifecycle_state, message] = self.__run_app(name)
                deploy_tracker.record_app_lifecycle_status_change(name, lifecycle_state=lifecycle_state, message=message)
                return message
            except Exception as err:
                deploy_tracker.record_app_lifecycle_status_change(name, status=False, message=str(err))
                raise AppUpdateError("Failed to run '{}' application".format(name)) from err

    def get_app_lifecycle_state(self, name):
        return self.__get_app_lifecycle_state(name)

    def read_app_logs(self, name, max_lines):
        return self.__read_app_logs(name, max_lines)

    def halt_app(self, name):
        with DeployedArtifactsTracker(self.config) as deploy_tracker:
            try:
                self.__halt_app(name)
                deploy_tracker.record_app_lifecycle_status_change(name, lifecycle_state=LifecycleState.ready)
            except Exception as err:
                deploy_tracker.record_app_lifecycle_status_change(name, status=False, message=str(err))
                raise AppUpdateError("Failed to halt '{}' application".format(name)) from err

    def update_app(self, name, revision):
        with DeployedArtifactsTracker(self.config) as deploy_tracker:
            with UpdateStatusTracker(self.config) as update_tracker:
                self.logger.info("Updating '{}' application to revision '{}'".format(name, revision))
                try:
                    update_tracker.record_app_update_status(name, revision=revision, completion_state=UpdateCompletionState.initiated)
                    
                    self.__halt_app(name)
                    deploy_tracker.record_app_lifecycle_status_change(name, lifecycle_state=LifecycleState.ready)
                    
                    self.updater.pull_app_update(name, revision)
                    update_tracker.record_app_update_status(name, completion_state=UpdateCompletionState.downloaded)

                    # TODO Implement checksum/signature verification
                    update_tracker.record_app_update_status(name, completion_state=UpdateCompletionState.verified)
                    
                    self.__apply_app_update(name, revision)
                    deploy_tracker.record_app_deployed_revision_change(name, revision, updating=True)
                    update_tracker.record_app_update_status(name, completion_state=UpdateCompletionState.applied)

                    if self.__is_run_app_automatically(name):
                        [lifecycle_state, message] = self.__run_app(name)
                        deploy_tracker.record_app_lifecycle_status_change(name, lifecycle_state=lifecycle_state, message=message)

                    # TODO Implement app self testing and roll back app if the same fails 
                    update_tracker.record_app_update_status(name, completion_state=UpdateCompletionState.confirmed, message='Application update successfully completed')
                except Exception as err:
                    deploy_tracker.record_app_lifecycle_status_change(name, status=False, message=str(err))
                    update_tracker.record_app_update_status(name, status=False, message=str(err))
                    raise AppUpdateError("Failed to update '{}' application".format(name)) from err

    def roll_back_app(self, name):
        revision = self.updater.get_app_rollback_revision(name, self.config.deployed_artifacts_path)
        if not revision:
             raise AppUpdateError("Cannot roll back update for '{}' application before any such has been deployed".format(name))
        
        with DeployedArtifactsTracker(self.config) as deploy_tracker:
            with UpdateStatusTracker(self.config) as update_tracker:
                self.logger.info("Rolling back '{}' application to revision '{}'".format(name, revision))
                try:
                    self.__halt_app(name)
                    deploy_tracker.record_app_lifecycle_status_change(name, lifecycle_state=LifecycleState.ready)

                    self.__deploy_app_revision(name, revision)
                    deploy_tracker.record_app_deployed_revision_change(name, revision, updating=False)

                    if self.__is_run_app_automatically(name):
                        [lifecycle_state, message] = self.__run_app(name)
                        deploy_tracker.record_app_lifecycle_status_change(name, lifecycle_state=lifecycle_state, message=message)

                    update_tracker.record_app_update_status(name, completion_state=UpdateCompletionState.rolled_back, message='Update rolled back due to application-level or external request')
                except Exception as err:
                    deploy_tracker.record_app_lifecycle_status_change(name, status=False, message=str(err))
                    update_tracker.record_app_update_status(name, status=False, message=str(err))
                    raise AppUpdateError("Failed to roll back '{}' application".format(name)) from err

    def delete_app(self, name):
        with DeployedArtifactsTracker(self.config) as tracker:
            try:
                self.__delete_app(name)
                tracker.erase_app(name)
            except Exception as err:
                tracker.record_app_lifecycle_status_change(name, status=False, message=str(err))
                raise AppUpdateError("Failed to delete '{}' application") from err