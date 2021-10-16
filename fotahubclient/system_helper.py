import logging
import subprocess
import shlex

def run_hook_command(title, command, args=[]):
    if command is not None:
        logging.getLogger().info('Running ' + title)

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