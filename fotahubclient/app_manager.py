import os
import logging

from fotahubclient.app_updater import AppUpdater
from fotahubclient.systemd_operator import SystemDOperator

class AppManager(object):

    def __init__(self, config):
        self.logger = logging.getLogger()
        self.config = config

    def install_and_launch_apps(self):
        updater = AppUpdater(self.config.app_ostree_repo_path, self.config.ostree_gpg_verify, self.config.app_install_root)
        systemd = SystemDOperator()

        app_names = self.list_app_names()

        install_err = False
        for app_name in app_names:
            try:
                updater.install_app(app_name)
                systemd.create_unit(app_name, updater.to_app_service_manifest_path(app_name))
            except Exception:
                install_err = True

        systemd.reload()

        for app_name in app_names:
            try:
                if updater.is_app_autostart(app_name):
                    systemd.start_unit(app_name)
            except Exception:
                install_err = True
        
        if install_err:
            raise RuntimeError("Failed to install or launch one or several applications (run 'fotahub describe-installed-artifacts' to get more details)") 