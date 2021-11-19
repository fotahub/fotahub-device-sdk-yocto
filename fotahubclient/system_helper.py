import os
import logging
import subprocess
import shlex

def join_exception_messages(err, message=''):
    if err is not None:
        message = (message + ': ' if message else '') + str(err)
        return join_exception_messages(err.__cause__, message)
    else:
        return message

def run_hook_command(title, command, args=[]):
    if command is not None:
        logging.getLogger().info("Running {}".format(title))

        command = shlex.split(command)
        args = [args] if not isinstance(args, list) else args
        if command[0] == 'sh' or command[0] == 'bash':
            args = [command[0]] + args
        
        process = subprocess.run(command + args, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if process.returncode == 0:
            message = title + ' succeeded'
            if process.stdout:
                message += ': ' + process.stdout.strip()
            logging.getLogger().info(message)
            return [True, message]
        else:
            message = title + ' failed'
            if process.stderr:
                message += ': ' + process.stderr.strip()
            elif process.stdout:
                message += ': ' + process.stdout.strip()
            logging.getLogger().error(message)
            return [False, message]
    else:
        return [True, None]

def reboot_system():
    logging.getLogger().info("Rebooting system")
    
    try:
        subprocess.run("reboot", check=True)
    except subprocess.CalledProcessError as err:
        raise OSError("Failed to reboot system") from err

def chowntree(path, uid, gid):
    logging.getLogger().debug("Changing user/group ownership of each file in {} to {}/{}".format(path, str(uid), str(gid)))

    os.chown(path, uid, gid)
    for dir_path, dir_names, file_names in os.walk(path):
        for dir_name in dir_names:
            os.lchown(os.path.join(dir_path, dir_name), uid, gid)
        for file_name in file_names:
            os.lchown(os.path.join(dir_path, file_name), uid, gid)

def touch(path):
    open(path, 'a').close()
