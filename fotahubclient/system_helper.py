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

def run_command(title, command, args=[]):
    if command:
        logging.getLogger().info("Running {}".format(title))

        command = shlex.split(command)
        args = [args] if not isinstance(args, list) else args

        # Running shell scripts requires the name of the shell or shell script to be injected explicitly as first argument 
        # so that the $0 shell parameter gets assigned with the same and all other arguments get mapped to $1, $2, ...
        if command[0].endswith('sh') or command[0].endswith('bash'):
            args = [command[0]] + args

        logging.getLogger().debug("Launching subprocess: {}".format(' '.join(command + args)))
        process = subprocess.run(command + args, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        outcome = get_process_text_outcome(process)
        message = "{} {}".format(title, 'succeeded' if process.returncode == 0 else 'failed')
        if outcome:
            message += ": {}".format(outcome) 
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

def read_last_lines(path, max_lines):
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        return ''
    
    with open(path, "rb") as file:
        # Go to the end of the file (ignore trailing whitespace if any)
        file.seek(-1, os.SEEK_END) 
        while file.read(1).isspace():
            if file.tell() >= 2:
                file.seek(-2, os.SEEK_CUR)
            else:
                break

        # Move back specified number of lines
        for _ in range(max_lines):
            # Keep moving backward until the next break-line
            file.seek(-1, os.SEEK_CUR)
            while file.read(1) != b'\n':
                if file.tell() >= 2:
                    file.seek(-2, os.SEEK_CUR)
                else:
                    break
            file.seek(-1, os.SEEK_CUR)
            
            # Stop moving when having reached the beginning of the file again
            if file.tell() == 0:
                break

        # Read file content from current position on and convert result into text
        return file.read().decode().strip()

def reboot_system():
    logging.getLogger().info("Rebooting system")
    
    try:
        subprocess.run(["reboot", "--force"], check=True)
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
