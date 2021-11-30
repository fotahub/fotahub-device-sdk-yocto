import os
import logging
import shutil

import gi
gi.require_version("OSTree", "1.0")
from gi.repository import OSTree, GLib, Gio

import fotahubclient.common_constants as constants
from fotahubclient.ostree_repo import OSTreeRepo, OSTreeError
from fotahubclient.json_document_models import ArtifactKind, InstalledArtifacts
from fotahubclient.system_helper import chowntree

class AppUpdater(object):

    def __init__(self, ostree_repo_path, ostree_gpg_verify):
        self.logger = logging.getLogger()

        repo = self.__open_ostree_repo(ostree_repo_path)
        self.ostree_repo = OSTreeRepo(repo)
        self.ostree_repo.add_ostree_remote(constants.FOTAHUB_OSTREE_REMOTE_NAME, constants.FOTAHUB_OSTREE_REMOTE_URL, ostree_gpg_verify)

    def __open_ostree_repo(self, repo_path):
        try:
            repo = OSTree.Repo.new(Gio.File.new_for_path(repo_path))
            if os.path.exists(repo_path):
                self.logger.debug("Opening application OSTree repo located at '{}'".format(repo_path))
                repo.open(None)
            else:
                self.logger.debug("Creating and opening new application OSTree repo located at '{}'".format(repo_path))
                repo.create(OSTree.RepoMode.BARE_USER_ONLY, None)
            return repo
        except GLib.Error as err:
            raise OSTreeError('Failed to open application OSTree repo') from err

    def list_app_names(self):
        return [ref.split(':')[1] if ':' in ref else ref for ref in self.ostree_repo.list_ostree_refs()]

    def get_app_deploy_revision(self, name):
        return self.ostree_repo.resolve_ostree_revision(constants.FOTAHUB_OSTREE_REMOTE_NAME, name)

    def get_app_rollback_revision(self, name, installed_artifacts_path):
        if os.path.isfile(installed_artifacts_path) and os.path.getsize(installed_artifacts_path) > 0:
            installed_artifacts = InstalledArtifacts.load_installed_artifacts(installed_artifacts_path)
            rollback_versions = [installed_artifact.rollback_revision for installed_artifact in installed_artifacts.installed_artifacts 
                if installed_artifact.name == name and installed_artifact.kind == ArtifactKind.Application]
            return rollback_versions[0] if rollback_versions else None
        else:
            return None

    def pull_app_update(self, name, revision):
        self.logger.info("Pulling '{}' application revision '{}'".format(name, revision))

        self.ostree_repo.pull_ostree_revision(constants.FOTAHUB_OSTREE_REMOTE_NAME, name, revision, constants.OSTREE_PULL_DEPTH)

    def checkout_app_revision(self, name, revision, checkout_path):
        self.logger.info("Checking out '{}' application revision '{}'".format(name, revision))

        try:
            if os.path.isdir(checkout_path):
                shutil.rmtree(checkout_path)
            os.mkdir(checkout_path)

            self.ostree_repo.checkout_at(revision, checkout_path)

            chowntree(checkout_path, constants.APP_UID, constants.APP_GID)
        except GLib.Error as err:
            raise OSTreeError("Failed to check out '{}' application revision '{}'".format(name, revision)) from err
