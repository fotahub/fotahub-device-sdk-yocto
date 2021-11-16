import logging
import shutil

from pydbus import SystemBus

SYSTEMD_UNIT_MANIFEST_NAME_PATTERN = '{}.service'
SYSTEMD_UNIT_MANIFEST_PATH_PATTERN = '/etc/systemd/system/' + SYSTEMD_UNIT_MANIFEST_NAME_PATTERN

class SystemDOperator(object):
    
    def __init__(self):
        self.logger = logging.getLogger()

        self.systemd = SystemBus().get('.systemd1')

    def list_units(self, service_name):
        return self.systemd.ListUnitsByNames([SYSTEMD_UNIT_MANIFEST_NAME_PATTERN.format(service_name)])

    def has_unit(self, service_name):
        return self.list_units(service_name)[0][2] != 'not-found'
    
    def create_unit(self, service_name, service_manifest_path):
        self.logger.debug("Intstalling '{}' service as per '{}' manifest as systemd unit".format(service_name, service_manifest_path))
        shutil.copy(service_manifest_path, SYSTEMD_UNIT_MANIFEST_PATH_PATTERN.format(service_name))

    def start_unit(self, service_name, enable_only=False):
        self.logger.debug("Starting '{}' service".format(service_name))
        self.systemd.EnableUnitFiles([SYSTEMD_UNIT_MANIFEST_NAME_PATTERN.format(service_name)], False, False)
        if not enable_only:
            self.systemd.StartUnit(SYSTEMD_UNIT_MANIFEST_NAME_PATTERN.format(service_name), "replace")

    def stop_unit(self, service_name):
        self.logger.debug("Stopping '{}' service".format(service_name))
        self.systemd.StopUnit(SYSTEMD_UNIT_MANIFEST_NAME_PATTERN.format(service_name), 'replace')
        self.systemd.DisableUnitFiles([SYSTEMD_UNIT_MANIFEST_NAME_PATTERN.format(service_name)], False)

    def reload(self):
        self.systemd.Reload()