from fotahubclient.system_helper import run_command

def test_run_simple_bash_command():
    assert run_command('Hello command', "bash -c 'echo \"Hello\"'") == [True, 'Hello command succeeded: Hello']

def test_run_bash_command_with_arg():
    assert run_command('OS update verification', "bash -c 'echo \"The downloaded OS update (revision $1) looks good!\"'", '123456789') == [True, 'OS update verification succeeded: The downloaded OS update (revision 123456789) looks good!'] 

def test_run_failing_bash_command():
    assert run_command('Failing command', "bash -c 'echo \"You have screwed it up!\"; false'") == [False, 'Failing command failed: You have screwed it up!']