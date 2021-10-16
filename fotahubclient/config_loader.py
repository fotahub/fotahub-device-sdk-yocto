import os
import configparser
from configparser import ConfigParser

UPDATE_STATUS_PATH_DEFAULT = '/var/log/fotahub/updatestatus.json'

SYSTEM_CONFIG_PATH = '/etc/fotahub/fotahub.config'
USER_CONFIG_FILE_NAME = '.fotahub'

class ConfigLoader(object):
    
    def __init__(self, config_path=SYSTEM_CONFIG_PATH, update_status_path=None, verbose=False, stacktrace=False):
        self.config_path = config_path
        self.update_status_path = update_status_path
        
        self.gpg_verify = False
        
        self.verbose = verbose
        self.stacktrace = stacktrace

        self.os_distro_name = None
        self.os_update_verification_command = None
        self.os_update_self_test_command = None

    def load(self):
        user_config_path = os.path.expanduser("~") + '/' + USER_CONFIG_FILE_NAME
        if os.path.isfile(user_config_path):
            self.config_path = user_config_path
        if not os.path.isfile(self.config_path):
            raise FileNotFoundError("No FotaHub client configuration file found in any of the following locations:\n{}\n{}".format(user_config_path, self.config_path))

        try:
            config = ConfigParser()
            config.read(self.config_path)

            if config.getboolean('General', 'GPGVerify', fallback=False):
                self.gpg_verify = True

            if self.update_status_path is None:
                self.update_status_path = config.get('General', 'UpdatesStatusPath', fallback=UPDATE_STATUS_PATH_DEFAULT)

            if config.getboolean('General', 'Verbose', fallback=False):
                self.verbose = True
            if config.getboolean('General', 'Stacktrace', fallback=False):
                self.stacktrace = True

            self.os_distro_name = config.get('OS', 'OSDistroName', fallback='os')
            self.os_update_verification_command = config.get('OS', 'OSUpdateVerificationCommand', fallback=None)
            self.os_update_self_test_command = config.get('OS', 'OSUpdateSelfTestCommand', fallback=None)

            self.app_ostree_home = config.get('App', 'AppOSTreeHome')
        except configparser.NoSectionError as err:
            raise ValueError("No '{}' section in FotaHub configuration file {}".format(err.section, self.config_path))
        except configparser.NoOptionError as err:
            raise ValueError("Mandatory '{}' option missing in '{}' section of FotaHub configuration file {}".format(err.option, err.section, self.config_path))
