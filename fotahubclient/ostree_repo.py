import os
import logging

import gi
gi.require_version("OSTree", "1.0")
from gi.repository import OSTree, GLib

class OSTreeError(Exception):
    pass

class OSTreeRepo(object):

    def __init__(self, repo):
        self.logger = logging.getLogger()
        
        self.ostree_repo = repo

    def has_ostree_remote(self, name):
        return name in self.ostree_repo.remote_list()

    def add_ostree_remote(self, name, url, gpg_verify, force=False):
        if not self.has_ostree_remote(name) or force:
            self.logger.debug("Adding remote '{}' for {} to local OSTree repo".format(name, url))

            try:
                opts = GLib.Variant(
                    'a{sv}', 
                    {
                        'gpg-verify': GLib.Variant('b', gpg_verify)
                    }
                )
                self.ostree_repo.remote_add(name, url, opts, None)
            except GLib.Error as err:
                raise OSTreeError("Failed to add remote '{}' to local OSTree repo".format(name)) from err

    def list_ostree_refs(self):
        [_, refs] = self.ostree_repo.list_refs(None, None)
        return refs

    def resolve_ostree_revision(self, remote_name, ref):
        [_, revision] = self.ostree_repo.resolve_rev(remote_name + ':' + ref if remote_name else ref, False)
        return revision

    def pull_ostree_revision(self, remote_name, branch_name, revision, depth):
        self.logger.debug("Pulling revision '{}' from '{}' branch at OSTree remote '{}'".format(revision, branch_name, remote_name))

        try:
            progress = OSTree.AsyncProgress.new()
            progress.connect(
                'changed', OSTree.Repo.pull_default_console_progress_changed, None)

            opts = GLib.Variant(
                'a{sv}', 
                {
                    'flags': GLib.Variant('i', OSTree.RepoPullFlags.NONE),
                    'refs': GLib.Variant('as', (branch_name,)),
                    'override-commit-ids': GLib.Variant('as', (revision,)),
                    'depth': GLib.Variant('i', depth)
                }
            )
            result = self.ostree_repo.pull_with_options(
                remote_name, opts, progress, None)

            progress.finish()
            if not result:
                raise OSTreeError("Unable to pull revision '{}' from '{}' branch at OSTree remote '{}'".format(revision, branch_name, remote_name))
        except GLib.Error as err:
            raise OSTreeError("Unable to pull revision '{}' from '{}' branch at OSTree remote '{}'".format(revision, branch_name, remote_name)) from err

    def checkout_at(self, revision, checkout_path):
        self.logger.debug("Checking out revision '{}' from local OSTree repo".format(revision))

        checkout_dir = None
        try:
            options = OSTree.RepoCheckoutAtOptions()
            options.overwrite_mode = OSTree.RepoCheckoutOverwriteMode.UNION_IDENTICAL
            options.process_whiteouts = True
            options.bareuseronly_dirs = True
            options.no_copy_fallback = True
            options.mode = OSTree.RepoCheckoutMode.USER

            checkout_dir = os.open(checkout_path, os.O_DIRECTORY)
            if not self.ostree_repo.checkout_at(options, checkout_dir, checkout_path, revision):
                raise OSTreeError("Unable to check out revision '{}' from local OSTree repo".format(revision))
        except GLib.Error as err:
            raise OSTreeError("Unable to check out revision '{}' from local OSTree repo".format(revision)) from err
        finally:
            if checkout_dir is not None:
                os.close(checkout_dir)
