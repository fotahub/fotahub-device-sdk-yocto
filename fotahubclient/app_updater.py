import os
import logging
import subprocess
from types import resolve_bases
from fotahubclient.system_helper import chown_tree

import gi
gi.require_version("OSTree", "1.0")
from gi.repository import OSTree, GLib, Gio

import fotahubclient.common_constants as constants
from fotahubclient.ostree_repo import OSTreeRepo, OSTreeError

APP_INSTALLED_MARKER_FILE_NAME = 'installed'
APP_AUTOSTART_MARKER_FILE_NAME = 'auto.start'
APP_SERVICE_MANIFEST_FILE_NAME = 'systemd.service'

APP_UID = 1000
APP_GID = 1000

class AppUpdater(object):

    def __init__(self, ostree_repo_path, ostree_gpg_verify, app_install_root):
        self.logger = logging.getLogger()

        self.app_install_root = app_install_root

        repo = self.__open_ostree_repo(ostree_repo_path)
        self.ostree_repo = OSTreeRepo(repo)
        self.ostree_repo.add_ostree_remote(constants.FOTAHUB_OSTREE_REMOTE_NAME, constants.FOTAHUB_OSTREE_REMOTE_URL, ostree_gpg_verify)

    def __open_ostree_repo(self, repo_path):
        try:
            repo = OSTree.Repo.new(Gio.File.new_for_path(repo_path))
            if os.path.exists(repo_path):
                self.logger.info("Opening application OSTree repo located at '{}'".format(repo_path))
                repo.open(None)
            else:
                self.logger.info("Creating and opening new application OSTree repo located at '{}'".format(repo_path))
                repo.create(OSTree.RepoMode.BARE_USER_ONLY, None)
            return repo
        except GLib.Error as err:
            raise OSTreeError('Failed to open application OSTree repo') from err

    def list_app_names(self):
        return [ref.split(':')[1] if ':' in ref else ref for ref in self.ostree_repo.list_ostree_refs()]

    def resolve_installed_revision(self, app_name):
        return self.ostree_repo.resolve_ostree_revision(constants.FOTAHUB_OSTREE_REMOTE_NAME, app_name)

    def to_app_install_path(self, app_name):
        return self.app_install_root + '/' + app_name

    def to_app_service_manifest_path(self, app_name):
        return self.to_app_install_path(app_name) + '/' + APP_SERVICE_MANIFEST_FILE_NAME

    def is_app_installed(self, app_name):
        return os.path.isfile(self.to_app_install_path(app_name) + '/' + APP_INSTALLED_MARKER_FILE_NAME)

    def is_app_autostart(self, app_name):
        return os.path.isfile(self.to_app_install_path(app_name) + '/' + APP_AUTOSTART_MARKER_FILE_NAME)

    def install_app(self, app_name):
        if not self.is_app_installed(app_name):
            self.logger.info("Installing '{}' application".format(app_name))
            
            self.checkout_app(app_name, None)
            chown_tree(self.to_app_install_path(app_name), APP_UID, APP_GID)

    #########################
    def set_current_revision(self, app_name, rev):
        """
        This method writes rev into a json file containing the current working rev for the containers.
        :param string app_name: Name of the container.
        :param string rev: Revision to write in json file.
        :raises FileNotFoundError: Exception raised if json file needs to be created.
        """
        try:
            with open(PATH_CURRENT_REVISIONS, "r") as f:
                current_revs = json.load(f)
            current_revs.update({app_name: rev})
            with open(PATH_CURRENT_REVISIONS, "w") as f:
                json.dump(current_revs, f, indent=4)
        except FileNotFoundError:
            with open(PATH_CURRENT_REVISIONS, "w") as f:
                current_revs = {app_name: rev}
                json.dump(current_revs, f, indent=4)

    def get_previous_rev(self, app_name):
        """
        This method returns the previous working revision of a notify container.
        :param string app_name: Name of the container.
        :returns: - The rev sha for app_name
                  - None if the container isn't found
        :raises KeyError: Execution raised if container associated with app_name doesn't exist.
        :raises FileNotFoundError: Execution raised if no file with previous rev exists.
        """
        try:
            with open(PATH_CURRENT_REVISIONS, "r") as f:
                current_revs = json.load(f)
            return current_revs[app_name]
        except (FileNotFoundError, KeyError):
            return None

    def handle_container(self, app_name, autostart, autoremove):
        """
        This method will handle the container execution or deletion based on the autostart
        and autoremove arguments.
        :param string app_name: Name of the container.
        :param int autostart: set to 1 if the container should be automatically started, 0 otherwise
        :param int autoremove: if set to 1, the container's directory will be deleted
        :returns: - True if the relevant container started correctly
                  - False otherwise
        """
        try:
            if autoremove == 1:
                self.logger.info("Remove the directory: {}".format(self.to_app_install_path(app_name)))
                shutil.rmtree(self.to_app_install_path(app_name))
            else:
                service = self.systemd.ListUnitsByNames([app_name + '.service'])
                if service[0][2] == 'not-found':
                    self.logger.info("First installation of the container {} on the "
                                    "system, we create and start the service".format(app_name))
                    if os.path.isfile(self.to_app_install_path(app_name) + '/' + APP_AUTOSTART_MARKER_FILE_NAME):
                        self.start_unit(app_name)
                else:
                    if autostart == 1:
                        if not os.path.isfile(self.to_app_install_path(app_name) + '/' + APP_AUTOSTART_MARKER_FILE_NAME):
                            open(self.to_app_install_path(app_name) + '/' + APP_AUTOSTART_MARKER_FILE_NAME, 'a').close()
                        self.start_unit(app_name)
                    else:
                        if os.path.isfile(self.to_app_install_path(app_name) + '/' + APP_AUTOSTART_MARKER_FILE_NAME):
                            os.remove(self.to_app_install_path(app_name) + '/' + APP_AUTOSTART_MARKER_FILE_NAME)
        except Exception as e:
            self.logger.error("UpdateTest :: Handling {} failed ({})".format(app_name, e))
            return False
        return True

    def checkout_app(self, app_name, rev_number):
        """
        This method checks out a container into its corresponding folder, to a given commit revision.
        Before that, it stops the container using systemd, if found.
        :param string app_name: Name of the container.
        :param string rev_number: Commit revision.
        """
        service = self.systemd.ListUnitsByNames([app_name + '.service'])
        if service[0][2] != 'not-found':
            self.logger.info("Stop the container {}".format(app_name))
            self.stop_unit(app_name)

        res = True
        rootfs_fd = None
        try:
            options = OSTree.RepoCheckoutAtOptions()
            options.overwrite_mode = OSTree.RepoCheckoutOverwriteMode.UNION_IDENTICAL
            options.process_whiteouts = True
            options.bareuseronly_dirs = True
            options.no_copy_fallback = True
            options.mode = OSTree.RepoCheckoutMode.USER

            self.logger.info("Getting rev from repo:{}".format(app_name + ':' + app_name))

            if rev_number is None:
                rev = self.repo_containers.resolve_rev(app_name + ':' + app_name, False)[1]
            else:
                rev = rev_number
            self.logger.info("Rev value:{}".format(rev))
            if os.path.isdir(self.to_app_install_path(app_name)):
                shutil.rmtree(self.to_app_install_path(app_name))
            os.mkdir(self.to_app_install_path(app_name))
            self.logger.info("Create directory {}/{}".format(self.app_install_root, app_name))
            rootfs_fd = os.open(self.to_app_install_path(app_name), os.O_DIRECTORY)
            res = self.repo_containers.checkout_at(options, rootfs_fd, self.to_app_install_path(app_name), rev)
            open(self.to_app_install_path(app_name) + '/' + APP_INSTALLED_MARKER_FILE_NAME, 'a').close()

        except GLib.Error as e:
            self.logger.error("Checking out {} failed ({})".format(app_name, str(e)))
            raise
        if rootfs_fd is not None:
            os.close(rootfs_fd)
        if not res:
            raise Exception("Checking out {} failed (returned False)")

    def update_container(self, app_name, rev_number, autostart, autoremove, notify=None, timeout=None):
        """
        Wrapper method to execute the different steps of a container update.
        :param string app_name: Name of the container.
        :param string rev_number: Commit revision.
        :param int autostart: set to 1 if the container should be automatically started, 0 otherwise
        :param int autoremove: if set to 1, the container's directory will be deleted
        :param int action_id: Unique identifier of an Hawkbit update.
        :param int notify: Set to 1 if the container is a notify container.
        :param int timeout: Timeout value of the communication socket.
        """
        try:
            self.init_container_remote(app_name)
            self.pull_ostree_ref(True, rev_number, app_name)
            self.checkout_app(app_name, rev_number)
            chown_tree(self.to_app_install_path(app_name), APP_UID, APP_GID)
            if (autostart == 1) and (notify == 1) and (autoremove != 1):
                feedback_thread = self.create_and_start_feedback_thread(app_name, rev_number, autostart, autoremove, timeout)
                self.feedbackThreads.append(feedback_thread)
            self.create_unit(app_name)
        except Exception as e:
            self.logger.error("Updating {} failed ({})".format(app_name, e))
            return False
        return True

    def rollback_container(self, app_name, autostart, autoremove):
        """
        This method Rollbacks the container, if possible, and returns a message that will
        be sent to the server.
        :param string app_name: Name of the container.
        :param int autostart: Autostart variable of the container, used for rollbacking.
        :param int autoremove: Autoremove of the container, used for rollbacking.
        :returns: End of the message that will be sent, which depends on the status of the rollback (performed or not)
        :rtype: string
        """

        end_msg = ""
        previous_rev = self.get_previous_rev(app_name)

        if previous_rev is None:
            end_msg = "\nFirst installation of the container, cannot rollback."
        else:
            res = self.update_container(app_name, previous_rev, autostart, autoremove)
            self.systemd.Reload()
            res &= self.handle_container(app_name, autostart, autoremove)
            if res:
                end_msg = "\nContainer has rollbacked."
            else:
                end_msg = "\nContainer has failed to rollback."

        return end_msg
