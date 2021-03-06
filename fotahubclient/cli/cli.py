import argparse
import sys
import os

import fotahubclient.config_loader as config_loader
import fotahubclient.cli.command_interpreter as commands
import fotahubclient.os_updater as os_updater
import fotahubclient.runc_operator as runc_operator
from fotahubclient.cli.help_formatters import CommandHelpFormatter, OptionHelpFormatter
from fotahubclient.cli.help_formatters import set_command_parser_titles
from fotahubclient.app_manager import AppRunMode

class CLI(object):

    def __init__(self):
        
        self.cli_parser = argparse.ArgumentParser(os.path.basename(sys.argv[0]), description='Over-the-air update or roll back operating system or containerized applications on Linux-based IoT edge devices.', formatter_class=CommandHelpFormatter)
        set_command_parser_titles(self.cli_parser)
        self.cli_parser.add_argument('-c', '--config', dest='config_path', default=config_loader.SYSTEM_CONFIG_PATH, help='path to configuration file (optional, defaults to ' + config_loader.SYSTEM_CONFIG_PATH + ')')
        self.cli_parser.add_argument('-v', '--verbose', action='store_true', default=False, help='enable verbose output (optional, disabled by default)')
        self.cli_parser.add_argument('-d', '--debug', action='store_true', default=False, help='enable debug output (optional, disabled by default)')
        self.cli_parser.add_argument('-s', '--stacktrace', action='store_true', default=False, help='enable output of stacktrace for exceptions (optional, disabled by default)')
        cmds = self.cli_parser.add_subparsers(dest='command')

        cmd = cmds.add_parser(commands.UPDATE_OPERATING_SYSTEM_CMD, help='update operating system (involves a reboot)', formatter_class=OptionHelpFormatter)
        set_command_parser_titles(cmd)
        cmd.add_argument('-r', '--revision', required=True, help='operating system revision to update to')
        cmd.add_argument('--max-reboot-failures', default=os_updater.MAX_REBOOT_FAILURES_DEFAULT, help='maximum number of reboot failures before automatically rolling back operating system update (optional, defaults to ' + str(os_updater.MAX_REBOOT_FAILURES_DEFAULT) + ')')
        
        cmd = cmds.add_parser(commands.ROLL_BACK_OPERATING_SYSTEM_CMD, help='roll back operating system to previous revision', formatter_class=OptionHelpFormatter)
        set_command_parser_titles(cmd)

        cmd = cmds.add_parser(commands.FINALIZE_OPERATING_SYSTEM_CHANGE_CMD, help='finalize an operating system update or rollback (after reboot)', formatter_class=OptionHelpFormatter)
        set_command_parser_titles(cmd)

        cmd = cmds.add_parser(commands.DEPLOY_APPLICATIONS_CMD, help='deploy applications and run those configured to be run automatically', formatter_class=OptionHelpFormatter)
        set_command_parser_titles(cmd)

        cmd = cmds.add_parser(commands.CONFIGURE_APPLICATION_CMD, help='configure an application', formatter_class=OptionHelpFormatter)
        set_command_parser_titles(cmd)
        cmd.add_argument('-n', '--name', required=True, help='name of application to configure')
        cmd.add_argument('-m', '--run-mode', required=True, type=AppRunMode, choices=list(AppRunMode), help='mode in which to run application')

        cmd = cmds.add_parser(commands.RUN_APPLICATION_CMD, help='run an application', formatter_class=OptionHelpFormatter)
        set_command_parser_titles(cmd)
        cmd.add_argument('-n', '--name', required=True, help='name of application to run')

        cmd = cmds.add_parser(commands.READ_APPLICATION_LOGS_CMD, help='read the logs of an application', formatter_class=OptionHelpFormatter)
        set_command_parser_titles(cmd)
        cmd.add_argument('-n', '--name', required=True, help='name of application of which to read the logs')
        cmd.add_argument('-l', '--max-lines', default=runc_operator.MAX_LOG_LINES_DEFAULT, help='maximum number of log lines to read (optional, defaults to ' + str(runc_operator.MAX_LOG_LINES_DEFAULT) + ')')

        cmd = cmds.add_parser(commands.HALT_APPLICATION_CMD, help='halt an application', formatter_class=OptionHelpFormatter)
        set_command_parser_titles(cmd)
        cmd.add_argument('-n', '--name', required=True, help='name of application to halt')

        cmd = cmds.add_parser(commands.UPDATE_APPLICATION_CMD, help='update an application', formatter_class=OptionHelpFormatter)
        set_command_parser_titles(cmd)
        cmd.add_argument('-n', '--name', required=True, help='name of application to update')
        cmd.add_argument('-r', '--revision', required=True, help='application revision to update to')

        cmd = cmds.add_parser(commands.ROLL_BACK_APPLICATION_CMD, help='roll back an application to previous revision', formatter_class=OptionHelpFormatter)
        set_command_parser_titles(cmd)
        cmd.add_argument('-n', '--name', required=True, help='name of application to roll back')

        cmd = cmds.add_parser(commands.DELETE_APPLICATION_CMD, help='delete an application', formatter_class=OptionHelpFormatter)
        set_command_parser_titles(cmd)
        cmd.add_argument('-n', '--name', required=True, help='name of application to delete')

        cmd = cmds.add_parser(commands.DESCRIBE_DEPLOYED_ARTIFACTS_CMD, help='retrieve deployed artifacts', formatter_class=CommandHelpFormatter)
        set_command_parser_titles(cmd)
        cmd.add_argument('-n', '--artifact-names', metavar='ARTIFACT_NAME', nargs='*', default=[], help='names of artifacts to consider (optional, defaults to all artifacts)')

        cmd = cmds.add_parser(commands.DESCRIBE_UPDATE_STATUS_CMD, help='retrieve update status', formatter_class=OptionHelpFormatter)
        set_command_parser_titles(cmd)
        cmd.add_argument('-n', '--artifact-names', metavar='ARTIFACT_NAME', nargs='*', default=[], help='names of artifacts to consider (defaults to all artifacts)')
        
    def parse_args(self):

        # Show help when no arguments are supplied
        if len(sys.argv) == 1:
            self.cli_parser.print_help()
            sys.exit(0)

        return self.cli_parser.parse_args()
