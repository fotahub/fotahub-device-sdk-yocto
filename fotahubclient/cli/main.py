import sys
import logging
import traceback

from fotahubclient.cli.cli import CLI
from fotahubclient.config_loader import ConfigLoader
from fotahubclient.cli.command_interpreter import CommandInterpreter
import fotahubclient.common_constants as constants
from fotahubclient.system_helper import join_exception_messages

def main():
    config = None
    try:
        cli = CLI()
        args = cli.parse_args()
        
        config = ConfigLoader(config_path=args.config_path, verbose=args.verbose, stacktrace=args.stacktrace)
        config.load()

        log_level = logging.INFO if config.verbose else logging.WARNING
        logging.basicConfig(stream=sys.stdout, level=log_level, format=constants.LOG_MESSAGE_FORMAT, datefmt=constants.LOG_DATE_FORMAT)

        command_interpreter = CommandInterpreter(config)
        command_interpreter.run(args)
    except Exception as err:
        if config is not None and config.stacktrace:
            print(''.join(traceback.format_exception(type(err), err, err.__traceback__)), file=sys.stderr)
        else:
            print('ERROR: ' + join_exception_messages(err), file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()