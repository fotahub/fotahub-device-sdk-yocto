import logging
import subprocess
import re

UBOOT_SETENV_TOOL = 'fw_setenv'
UBOOT_PRINTENV_TOOL = 'fw_printenv'

class UBootError(Exception):
    pass

class UBootOperator(object):
    
    def __init__(self):
        self.logger = logging.getLogger()

    def set_uboot_env_var(self, name, value=None):
        if value != None:
            self.logger.debug("Setting U-Boot environment variable '{}' to '{}'".format(name, value))
        else:
            self.logger.debug("Deleting U-Boot environment variable '{}'".format(name))

        try:
            cmd = [UBOOT_SETENV_TOOL, name]
            if value != None:
                cmd.append(value)
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as err:
            raise UBootError("Failed to change U-Boot environment variable '{}'".format(name)) from err

    def isset_uboot_env_var(self, name):
        try:
            cmd = [UBOOT_PRINTENV_TOOL]
            process = subprocess.run(cmd, text=True, capture_output=True, check=True)
            return bool(re.search(r'^{}='.format(name), process.stdout, re.MULTILINE))
        except subprocess.CalledProcessError:
            return False
