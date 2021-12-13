import sys
import logging
import traceback

from fotahubclient.daemon.cli import CLI
from fotahubclient.config_loader import ConfigLoader
import fotahubclient.common_constants as constants
from fotahubclient.os_update_manager import OSUpdateManager
from fotahubclient.app_manager import AppManager
from fotahubclient.system_helper import join_exception_messages

def run(config):
    logging.getLogger().debug('Finalizing OS update or rollback in case any such has just happened')
    manager = OSUpdateManager(config)
    manager.finalize_os_update()

    logging.getLogger().debug('Deploying applications and running those configured to be run automatically')
    manager = AppManager(config)
    manager.deploy_and_run_apps()

def main():
    config = None
    try:
        cli = CLI()
        args = cli.parse_args()
        
        config = ConfigLoader(config_path=args.config_path, verbose=args.verbose, debug=args.debug, stacktrace=args.stacktrace)
        config.load()

        logging.basicConfig(stream=sys.stdout, level=config.log_level, format=constants.LOG_MESSAGE_FORMAT, datefmt=constants.LOG_DATE_FORMAT)

        run(config)
    except Exception as err:
        if config is not None and config.stacktrace:
            print(''.join(traceback.format_exception(type(err), err, err.__traceback__)), file=sys.stderr)
        else:
            print('ERROR: ' + join_exception_messages(err), file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()