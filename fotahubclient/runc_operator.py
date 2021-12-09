import os
import logging
import subprocess
import json
from enum import Enum

from fotahubclient.system_helper import get_process_text_outcome, read_last_lines
from fotahubclient.system_helper import read_last_lines

CONTAINER_LOG_OUT_FILE_NAME = 'log.out'
CONTAINER_LOG_ERR_FILE_NAME = 'log.err'

MAX_LOG_LINES_DEFAULT = 10

class RunCError(Exception):
    pass

class ContainerState(Enum):
    created = 1
    running = 2
    stopped = 3

    @classmethod
    def from_string(cls, value):
        for k, v in cls.__members__.items():
            if k == value:
                return v
        return None

# See https://medium.com/@Mark.io/https-medium-com-mark-io-managing-runc-containers-e40a9b3c58bd for details
class RunCOperator(object):
    
    def __init__(self):
        self.logger = logging.getLogger()

    def get_container_state(self, container_id):
        process = subprocess.run(["runc", "state", container_id], universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if process.returncode != 0:
            return None
        return ContainerState.from_string(json.loads(process.stdout)['status'])

    def read_container_logs(self, bundle_path, max_lines=MAX_LOG_LINES_DEFAULT):
        out_path = '{}/{}'.format(bundle_path, CONTAINER_LOG_OUT_FILE_NAME)
        err_path = '{}/{}'.format(bundle_path, CONTAINER_LOG_ERR_FILE_NAME)

        logs = ''
        if os.path.getsize(out_path):
            logs = read_last_lines(out_path, max_lines if os.path.getsize(err_path) == 0 else max_lines - 1)

        if logs and not logs.endswith('\n'):
            logs += '\n'
        
        if os.path.getsize(err_path):
            logs += read_last_lines(err_path, 1)

    def run_container(self, container_id, bundle_path):
        container_state = self.get_container_state(container_id)
        if container_state == ContainerState.created:
            raise RunCError("Cannot create and run '{}' container that has already been created - consider to delete it before")
        if container_state == ContainerState.running:
            self.logger.debug("Ignoring request to run '{}' container as it is already running".format(container_id))
            return

        if container_state == ContainerState.stopped:
            self.delete_container(container_id)

        self.logger.debug("Creating and running '{}' container as per '{}' bundle".format(container_id, bundle_path))
        with open('{}/{}'.format(bundle_path, CONTAINER_LOG_OUT_FILE_NAME), "w") as out_file:
            with open('{}/{}'.format(bundle_path, CONTAINER_LOG_ERR_FILE_NAME), "w") as err_file:
                process = subprocess.run(["runc", "run", "--detach", "-b", bundle_path, container_id], universal_newlines=True, stdout=out_file, stderr=err_file, check=False)
                if process.returncode == 0:
                    return [self.get_container_state(container_id), self.read_container_logs(bundle_path)]
                else:
                    raise RunCError("Failed to create and run '{}' container: {}".format(container_id, err_file.read()))

    def stop_container(self, container_id):
        if self.get_container_state(container_id) != ContainerState.running:
            self.logger.debug("Ignoring request to stop '{}' container as no such is running".format(container_id))
            return

        self.logger.debug("Stopping '{}' container".format(container_id))
        process = subprocess.run(["runc", "kill", container_id, "KILL"], universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if process.returncode != 0:
            raise RunCError("Failed to stop '{}' container: {}".format(container_id, get_process_text_outcome(process)))

        while self.get_container_state(container_id) == ContainerState.running:
            # Wait until container has been effectively stopped
            pass

    def delete_container(self, container_id):
        if not self.get_container_state(container_id):
            self.logger.debug("Ignoring request to delete '{}' container as no such exists yet or anymore".format(container_id))
            return

        self.stop_container(container_id)

        self.logger.debug("Deleting '{}' container".format(container_id))
        process = subprocess.run(["runc", "delete", container_id], universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if process.returncode != 0:
            raise RunCError("Failed to delete '{}' container: {}".format(container_id, get_process_text_outcome(process)))
