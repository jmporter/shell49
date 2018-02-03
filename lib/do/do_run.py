from printing import eprint, qprint
import printing

import os

LAST_RUN_FILE = ''


def complete_run(self, text, line, begidx, endidx):
    return self.filename_complete(text, line, begidx, endidx)


def do_run(self, line):
    """run [FILE]

    Send file to remote for execution and print results on console.

    If FILE is not specified, executes the file from the last invocation.
    """
    global LAST_RUN_FILE
    args = line.split()
    if len(args) > 1:
        eprint("*** Only one file, please!")
        return

    if len(args) == 0:
        file = LAST_RUN_FILE
        qprint("run '{}' on micropython board".format(file))
    else:
        file = os.path.join(self.cur_dir, args[0])
        LAST_RUN_FILE = file

    print(printing.MPY_COLOR, end='')
    try:
        self.boards.default.execfile(file, data_consumer=putch, timeout=None)
    except FileNotFoundError:
        eprint("*** File not found on host, '{}'".format(file))
    except KeyboardInterrupt:
        print()


def putch(byte):
    print(byte.decode('utf-8'), end='', flush=True)
