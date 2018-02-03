import os


def do_shell(self, line):
    """!some-shell-command args

       Launches a shell and executes whatever command you provide. If you
       don't provide any commands, then it will launch a bash sub-shell
       and when exit from bash (Control-D) then it will return to shell49.
    """
    if not line:
        line = '/bin/bash'
    os.system(line)
