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
    if command:
        logging.getLogger().info("Running {}".format(title))

        command = shlex.split(command)
        args = [args] if not isinstance(args, list) else args
        if command[0] == 'sh' or command[0] == 'bash':
            args = [command[0]] + args
        
        process = subprocess.run(command + args, text=True, capture_output=True, check=False)
        outcome = get_process_text_outcome(process)
        message = title + " {}" + (': ' + outcome if outcome else '').format('succeeded' if process.returncode == 0 else 'failed')
        if process.returncode == 0:
            logging.getLogger().info(message)
            return [True, message]
        else:
            logging.getLogger().error(message)
            return [False, message]
    else:
        return [True, None]

def get_process_text_outcome(process):
    if process.stderr is not None and process.stderr.strip():
        return process.stderr.strip()
    elif process.stdout is not None and process.stdout.strip():
        return process.stdout.strip()
    else:
        return "Exit code {}".format(process.returncode) if process.returncode != 0 else ''

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
