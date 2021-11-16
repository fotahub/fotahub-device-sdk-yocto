import sys
import logging
import traceback

from fotahubclient.daemon.cli import CLI
from fotahubclient.config_loader import ConfigLoader
import fotahubclient.common_constants as constants
from fotahubclient.os_update_agents import OSUpdateFinalizer
from fotahubclient.app_manager import AppManager

def run(config):
    logging.getLogger().debug('Finalizing OS update or rollback in case any such has just happened')
    # finalizer = OSUpdateFinalizer(config)
    # finalizer.finalize_os_update()

    logging.getLogger().debug('Installing and launching applications')
    # manager = AppManager(config)
    # manager.install_and_launch_apps()

def main():
    config = None
    try:
        cli = CLI()
        args = cli.parse_args()
        
        config = ConfigLoader(config_path=args.config_path, verbose=args.verbose, stacktrace=args.stacktrace)
        config.load()

        log_level = logging.INFO if config.verbose else logging.WARNING
        logging.basicConfig(stream=sys.stdout, level=log_level, format=constants.LOG_MESSAGE_FORMAT, datefmt=constants.LOG_DATE_FORMAT)

        run(config)
    except Exception as err:
        if config is not None and config.stacktrace:
            print(''.join(traceback.format_exception(type(err), err, err.__traceback__)), file=sys.stderr)
        else:
            print('ERROR: ' + str(err), file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()