#! python

"""Remote shell for MicroPython.

   This program uses the raw-repl feature of MicroPython to send small
   programs.
"""

from . config import Config
from . shell import Shell
from . devs import Devs
from . device import DeviceError
from . print_ import oprint, qprint, eprint, dprint, cprint
import shell49.print_

import os
import sys
import argparse

def real_main():
    """The main program."""
    default_config = os.getenv('SHELL49_CONFIG_FILE') or '~/.shell49_rc.py'
    default_editor = os.getenv('SHELL49_EDITOR') or os.getenv('VISUAL') or os.getenv('EDITOR') or 'vi'
    default_nocolor = False
    default_debug = False
    default_quiet = False

    parser = argparse.ArgumentParser(
        prog="shell49",
        usage="%(prog)s [options] [command]",
        description="Remote Shell for a MicroPython board.",
        epilog=(
"""
Environment variables:
  SHELL49_CONFIG_FILE   configuration file (Default: '{}')
  SHELL49_EDITOR        editor (Default: {})
""".format(default_config, default_editor)),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-c", "--config",
        dest="config",
        help="Set path of the configuration file (default: '%s')" % default_config,
        default=default_config
    )
    parser.add_argument(
        "-e", "--editor",
        dest="editor",
        help="Set the editor to use (default: '%s')" % default_editor,
        default=default_editor
    )
    parser.add_argument(
        "-f", "--file",
        dest="filename",
        help="Specifies a file of commands to process."
    )
    parser.add_argument(
        "-d", "--debug",
        dest="debug",
        action="store_true",
        help="Enable debug features (default %s)" % default_debug,
        default=default_debug
    )
    parser.add_argument(
        "--quiet",
        dest="quiet",
        action="store_true",
        help="Turns off some output (default: %s)" % default_quiet,
        default=False
    )
    parser.add_argument(
        "-n", "--nocolor",
        dest="nocolor",
        action="store_true",
        help="Turn off colorized output (default: %s)" % default_nocolor,
        default=default_nocolor
    )
    parser.add_argument(
        "--timing",
        dest="timing",
        action="store_true",
        help="Print timing information about each command",
        default=False
    )
    parser.add_argument(
        '-V', '--version',
        dest='version',
        action='store_true',
        help='Reports the version and exits.',
        default=False
    )
    parser.add_argument(
        "cmd",
        nargs=argparse.REMAINDER,
        help="Optional command to execute"
    )
    args = parser.parse_args(sys.argv[1:])

    shell49.print_.DEBUG = args.debug
    shell49.print_.QUIET = args.quiet
    if args.nocolor: print.nocolor()

    dprint("debug = %s" % args.debug)
    dprint("quiet = %d" % args.quiet)
    dprint("nocolor = %d" % args.nocolor)
    dprint("timing = %d" % args.timing)
    dprint("cmd = [%s]" % ', '.join(args.cmd))

    if args.version:
        print(__version__)
        return

    with Config(args.config) as config:
        devs = Devs(config)

        try:
            if config.get(0, 'auto_connect', True):
                devs.connect_serial(config.get(0, 'port', '/dev/cu.SLAB_USBtoUART'))
        except DeviceError as err:
            eprint(err)
            autoscan()

        if args.filename:
            with open(args.filename) as cmd_file:
                shell = Shell(args.editor, config, devs, stdin=cmd_file, filename=args.filename, timing=args.timing)
                shell.cmdloop('')
        else:
            cmd_line = ' '.join(args.cmd)
            if cmd_line == '':
                oprint("Welcome to shell49. Type 'help' for information; Control-D to exit.\n")
            if devs.num_devices() == 0:
                eprint('No MicroPython boards connected - use the connect command to add one.\n')
            shell = Shell(args.editor, config, devs, timing=args.timing)
            try:
                shell.cmdloop(cmd_line)
            except KeyboardInterrupt:
                print('')


def main():
    """This main function saves the stdin termios settings, calls real_main,
       and restores stdin termios settings when it returns.
    """
    save_settings = None
    stdin_fd = -1
    try:
        import termios
        stdin_fd = sys.stdin.fileno()
        save_settings = termios.tcgetattr(stdin_fd)
    except:
        pass
    try:
        real_main()
    finally:
        if save_settings:
            termios.tcsetattr(stdin_fd, termios.TCSANOW, save_settings)


if __name__ == "__main__":
    main()
