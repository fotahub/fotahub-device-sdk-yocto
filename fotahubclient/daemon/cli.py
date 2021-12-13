import argparse
import sys
import os

import fotahubclient.config_loader as config_loader
from fotahubclient.cli.help_formatters import OptionHelpFormatter
from fotahubclient.cli.help_formatters import set_option_parser_titles

class CLI(object):

    def __init__(self):
        
        self.cli_parser = argparse.ArgumentParser(os.path.basename(sys.argv[0]), description='Perform boot-time operations to manage over-the-air updates and rollbacks of operating system or containerized applications on Linux-based IoT edge devices.', formatter_class=OptionHelpFormatter)
        set_option_parser_titles(self.cli_parser)
        self.cli_parser.add_argument('-c', '--config', dest='config_path', default=config_loader.SYSTEM_CONFIG_PATH, help='path to configuration file (optional, defaults to ' + config_loader.SYSTEM_CONFIG_PATH + ')')
        self.cli_parser.add_argument('-v', '--verbose', action='store_true', default=False, help='enable verbose output (optional, disabled by default)')
        self.cli_parser.add_argument('-d', '--debug', action='store_true', default=False, help='enable debug output (optional, disabled by default)')
        self.cli_parser.add_argument('-s', '--stacktrace', action='store_true', default=False, help='enable output of stacktrace for exceptions (optional, disabled by default)')

    def parse_args(self):

        # Show help when no arguments are supplied
        if len(sys.argv) == 1:
            self.cli_parser.print_help()
            sys.exit(0)

        return self.cli_parser.parse_args()
