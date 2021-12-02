import logging
import subprocess
import json
from enum import Enum

CONTAINER_LOG_OUT_FILE_NAME = 'log.out'
CONTAINER_LOG_ERR_FILE_NAME = 'log.err'

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
        process = subprocess.run(["runc", "state", container_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if process.returncode != 0:
            return None
        return ContainerState.from_string(json.loads(process.stdout.decode("utf-8"))['status'])

    def run_container(self, container_id, bundle_path):
        container_state = self.get_container_state(container_id)
        if container_state == ContainerState.created:
            raise RunCError("Cannot create and run '{}' container that has already been created - consider to delete it before")
        if container_state == ContainerState.running:
            self.logger.debug("Ignoring request to run '{}' container as it is already running".format(container_id))
            return

        self.logger.debug("Creating and running '{}' container as per '{}' bundle".format(container_id, bundle_path))
        with open('{}/{}'.format(bundle_path, CONTAINER_LOG_OUT_FILE_NAME), "w") as out_file:
            with open('{}/{}'.format(bundle_path, CONTAINER_LOG_ERR_FILE_NAME), "w") as err_file:
                process = subprocess.run(["runc", "run", "--detach", "-b", bundle_path, container_id], stdout=out_file, stderr=err_file, check=False)
                if process.returncode != 0:
                    raise RunCError("Failed to create and run '{}' container: {}".format(container_id, process.stderr.decode("utf-8")))

    def stop_container(self, container_id):
        if self.get_container_state(container_id) != ContainerState.running:
            self.logger.debug("Ignoring request to stop '{}' container as no such is running".format(container_id))
            return

        self.logger.debug("Stopping '{}' container".format(container_id))
        process = subprocess.run(["runc", "kill", container_id, "KILL"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if process.returncode != 0:
            raise RunCError("Failed to stop '{}' container: {}".format(container_id, process.stderr.decode("utf-8")))

        while self.get_container_state(container_id) == ContainerState.running:
            # Wait until container has been effectively stopped
            pass

    def delete_container(self, container_id):
        self.stop_container(container_id)

        if not self.get_container_state(container_id):
            self.logger.debug("Ignoring request to delete '{}' container as no such exists yet or anymore".format(container_id))
            return

        self.logger.debug("Deleting '{}' container".format(container_id))
        process = subprocess.run(["runc", "delete", container_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if process.returncode != 0:
            raise RunCError("Failed to delete '{}' container: {}".format(container_id, process.stderr.decode("utf-8")))
