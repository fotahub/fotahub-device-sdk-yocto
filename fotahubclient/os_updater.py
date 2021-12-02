import logging
import subprocess

import gi
gi.require_version("OSTree", "1.0")
from gi.repository import OSTree, GLib

import fotahubclient.common_constants as constants
from fotahubclient.ostree_repo import OSTreeRepo, OSTreeError
from fotahubclient.uboot_operator import UBootOperator
from fotahubclient.system_helper import reboot_system

OSTREE_SYSTEM_REPOSITORY_PATH = '/ostree/repo'

UBOOT_FLAG_APPLYING_OS_UPDATE = 'applying_os_update'
UBOOT_FLAG_ROLLING_BACK_OS_UPDATE = 'rolling_back_os_update'
UBOOT_VAR_OS_UPDATE_REBOOT_FAILURE_CREDIT = 'os_update_reboot_failure_credit'

MAX_REBOOT_FAILURES_DEFAULT = 3

class OSUpdater(object):

    def __init__(self, os_distro_name, ostree_gpg_verify):
        self.logger = logging.getLogger()

        self.os_distro_name = os_distro_name
        self.ostree_gpg_verify = ostree_gpg_verify

        [sysroot, repo] = self.__open_ostree_repo()
        self.sysroot = sysroot
        self.ostree_repo = OSTreeRepo(repo)
        self.ostree_repo.add_ostree_remote(constants.FOTAHUB_OSTREE_REMOTE_NAME, constants.FOTAHUB_OSTREE_REMOTE_URL, self.ostree_gpg_verify)

        self.uboot = UBootOperator()
    
    def __open_ostree_repo(self):
        try:
            sysroot = OSTree.Sysroot.new_default()
            
            self.logger.debug("Opening OS OSTree repo located at '{}'".format(OSTREE_SYSTEM_REPOSITORY_PATH))
            sysroot.load(None)
            sysroot.cleanup(None)
            [_, repo] = sysroot.get_repo()

            return [sysroot, repo]
        except GLib.Error as err:
            raise OSTreeError('Failed to open OS OSTree repo') from err

    def get_deployed_os_revision(self):
        deploy = self.sysroot.get_booted_deployment()
        return deploy.get_csum() if deploy is not None else None

    def has_pending_os_revision(self):
        return self.get_pending_os_revision()

    def get_pending_os_revision(self):
        [pending, _] = self.sysroot.query_deployments_for(None)
        return pending.get_csum() if pending is not None else None
        
    def has_rollback_os_revision(self):
        return self.get_rollback_os_revision()

    def get_rollback_os_revision(self):
        [_, rollback] = self.sysroot.query_deployments_for(None)
        return rollback.get_csum() if rollback is not None else None

    def pull_os_update(self, revision):
        self.logger.info("Pulling OS revision '{}'".format(revision))
        
        self.ostree_repo.pull_ostree_revision(constants.FOTAHUB_OSTREE_REMOTE_NAME, self.os_distro_name, revision, constants.OSTREE_PULL_DEPTH)

    def __stage_os_update(self, revision):
        self.logger.info("Staging OS revision '{}'".format(revision))
        if self.has_pending_os_revision():
            raise OSTreeError("Cannot stage any new OS update when some other OS update is still pending")

        try:
            booted_deployment = self.sysroot.get_booted_deployment()
            if booted_deployment is None:
                raise OSTreeError("Currently running system has not been provisioned through OSTree")

            osname = booted_deployment.get_osname()
            origin = booted_deployment.get_origin()
            checksum = self.ostree_repo.resolve_ostree_revision(None, revision)

            [result, _] = self.sysroot.stage_tree(osname, checksum, origin, booted_deployment, None, None)
            if not result:
                raise OSTreeError("Failed to stage OS revision '{}'".format(revision))
        except GLib.Error as err:
            raise OSTreeError("Failed to stage OS revision '{}'".format(revision)) from err

    def apply_os_update(self, revision, max_reboot_failures):
        self.logger.info("Applying OS update to revision {}".format(revision))
        if self.is_applying_os_update():
            raise OSTreeError("Cannot apply any new OS update when the some other OS update is still about to be applied")
        if self.is_rolling_back_os_update():
            raise OSTreeError("Cannot apply any new OS update when the some other OS update is still about to rolled back")
        if revision == self.get_deployed_os_revision():
            raise OSTreeError("Cannot update OS towards the same revision that is already in use")
            
        self.__stage_os_update(revision)

        self.uboot.set_uboot_env_var(UBOOT_FLAG_APPLYING_OS_UPDATE, '1')
        self.uboot.set_uboot_env_var(UBOOT_VAR_OS_UPDATE_REBOOT_FAILURE_CREDIT, str(max_reboot_failures))

        reboot_system()

    def is_applying_os_update(self):
        return self.uboot.isset_uboot_env_var(UBOOT_FLAG_APPLYING_OS_UPDATE)

    def confirm_os_update(self):
        self.logger.info("Confirming OS update")
        if not self.is_applying_os_update():
            raise OSTreeError("Cannot confirm OS update before any such has been applied")

        self.uboot.set_uboot_env_var(UBOOT_FLAG_APPLYING_OS_UPDATE)
        self.uboot.set_uboot_env_var(UBOOT_VAR_OS_UPDATE_REBOOT_FAILURE_CREDIT)

    def roll_back_os_update(self):
        self.logger.info("Rolling back latest OS update")
        if not self.has_rollback_os_revision():
            raise OSTreeError("Cannot roll_back OS update before any such has been deployed")

        self.uboot.set_uboot_env_var(UBOOT_FLAG_APPLYING_OS_UPDATE)
        self.uboot.set_uboot_env_var(UBOOT_VAR_OS_UPDATE_REBOOT_FAILURE_CREDIT)
        self.uboot.set_uboot_env_var(UBOOT_FLAG_ROLLING_BACK_OS_UPDATE, '1')

        reboot_system()

    def is_rolling_back_os_update(self):
        return self.uboot.isset_uboot_env_var(UBOOT_FLAG_ROLLING_BACK_OS_UPDATE)

    def discard_os_update(self):
        self.logger.info("Discarding roll_backed OS update")
        if not self.is_rolling_back_os_update():
            raise OSTreeError("Cannot discard OS update before any such has been roll_backed")
        
        self.uboot.set_uboot_env_var(UBOOT_FLAG_ROLLING_BACK_OS_UPDATE)

        try:
            if self.has_pending_os_revision():                    
                # 0 is the index of the pending deployment
                # TODO Reimplement this behavior using OSTree API (see https://github.com/ostreedev/ostree/blob/8cb5d920c4b89d17c196f30f2c59fcbd4c762a17/src/ostree/ot-admin-builtin-undeploy.c#L59)
                subprocess.run(["ostree", "admin", "undeploy", "0"], check=True)
        except subprocess.CalledProcessError as err:
            raise OSTreeError("Failed to discard roll_backed OS update") from err
