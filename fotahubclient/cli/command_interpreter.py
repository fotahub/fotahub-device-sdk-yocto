import logging

from fotahubclient.os_update_manager import OSUpdateManager
from fotahubclient.app_manager import AppManager
from fotahubclient.update_status_describer import UpdateStatusDescriber
from fotahubclient.deployed_artifacts_describer import DeployedArtifactsDescriber

UPDATE_OPERATING_SYSTEM_CMD = 'update-operating-system'
ROLL_BACK_OPERATING_SYSTEM_CMD = 'roll-back-operating-system'
FINALIZE_OPERATING_SYSTEM_CHANGE_CMD = 'finalize-operating-system-change'
DEPLOY_APPLICATIONS_CMD = 'deploy-applications'
CONFIGURE_APPLICATION_CMD = 'configure-application'
RUN_APPLICATION_CMD = 'run-application'
READ_APPLICATION_LOGS_CMD = 'read-application-logs'
HALT_APPLICATION_CMD = 'halt-application'
UPDATE_APPLICATION_CMD = 'update-application'
ROLL_BACK_APPLICATION_CMD = 'roll-back-application'
DELETE_APPLICATION_CMD = 'delete-application'
DESCRIBE_DEPLOYED_ARTIFACTS_CMD = 'describe-deployed-artifacts'
DESCRIBE_UPDATE_STATUS_CMD = 'describe-update-status'

class CommandInterpreter(object):

    def __init__(self, config):
        self.logger = logging.getLogger()
        self.config = config

    def run(self, args):
        if args.command == UPDATE_OPERATING_SYSTEM_CMD:
            self.update_operating_system(args.revision, args.max_reboot_failures)
        elif args.command == ROLL_BACK_OPERATING_SYSTEM_CMD:
            self.roll_back_operating_system()
        elif args.command == FINALIZE_OPERATING_SYSTEM_CHANGE_CMD:
            self.finalize_operating_system_change()
        elif args.command == DEPLOY_APPLICATIONS_CMD:
            self.deploy_applications()
        elif args.command == CONFIGURE_APPLICATION_CMD:
            self.configure_application(args.name, args.run_mode)
        elif args.command == RUN_APPLICATION_CMD:
            self.run_application(args.name)
        elif args.command == READ_APPLICATION_LOGS_CMD:
            self.read_application_logs(args.name, args.max_lines)
        elif args.command == HALT_APPLICATION_CMD:
            self.halt_application(args.name)
        elif args.command == UPDATE_APPLICATION_CMD:
            self.update_application(args.name, args.revision)
        elif args.command == ROLL_BACK_APPLICATION_CMD:
            self.roll_back_application(args.name)
        elif args.command == DELETE_APPLICATION_CMD:
            self.delete_application(args.name)
        elif args.command == DESCRIBE_DEPLOYED_ARTIFACTS_CMD:
            self.describe_deployed_artifacts(args.artifact_names)
        elif args.command == DESCRIBE_UPDATE_STATUS_CMD:
            self.describe_update_status(args.artifact_names)

    def update_operating_system(self, revision, max_reboot_failures):
        self.logger.debug("Initiating OS update to revision '{}'".format(revision))

        manager = OSUpdateManager(self.config)
        manager.initiate_os_update(revision, max_reboot_failures)

    def roll_back_operating_system(self):
        self.logger.debug('Rolling back OS to previous revision')

        manager = OSUpdateManager(self.config)
        manager.roll_back_os_update()

    def finalize_operating_system_change(self):
        self.logger.debug('Finalizing OS update or rollback in case any such has just happened')

        manager = OSUpdateManager(self.config)
        manager.finalize_os_update()

    def deploy_applications(self):
        self.logger.debug('Deploying applications and running those configured to be run automatically')
        
        manager = AppManager(self.config)
        manager.deploy_and_run_apps()

    def configure_application(self, name, run_mode):
        self.logger.debug('Configuring ' + name + ' application')
        
        manager = AppManager(self.config)
        manager.configure_app(name, run_mode)

    def run_application(self, name):
        self.logger.debug('Running ' + name + ' application')
        
        manager = AppManager(self.config)
        message = manager.run_app(name)
        if message:
            print(message)

    def read_application_logs(self, name, max_lines):
        self.logger.debug('Reading ' + name + ' application logs')
        
        manager = AppManager(self.config)
        logs = manager.read_app_logs(name, max_lines)
        if logs:
            print(logs)

    def halt_application(self, name):
        self.logger.debug('Halting ' + name + ' application')
        
        manager = AppManager(self.config)
        manager.halt_app(name)

    def update_application(self, name, revision):
        self.logger.debug("Updating ' + name + ' application to revision '{}'".format(revision))
        
        manager = AppManager(self.config)
        manager.update_app(name, revision)

    def roll_back_application(self, name):
        self.logger.debug('Rolling back ' + name + ' application to previous revision ')
        
        manager = AppManager(self.config)
        manager.roll_back_app(name)

    def delete_application(self, name):
        self.logger.debug('Deleting ' + name + ' application')
        
        manager = AppManager(self.config)
        manager.delete_app(name)

    def describe_deployed_artifacts(self, artifact_names=[]):
        self.logger.debug('Retrieving deployed artifacts')

        describer = DeployedArtifactsDescriber(self.config)
        print(describer.describe_deployed_artifacts(artifact_names))

    def describe_update_status(self, artifact_names=[]):
        self.logger.debug('Retrieving update status')

        describer = UpdateStatusDescriber(self.config)
        print(describer.describe_update_status(artifact_names))
