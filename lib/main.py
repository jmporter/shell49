#! /anaconda/bin/python

"""Remote shell for MicroPython.

   This program uses the raw-repl feature of MicroPython to send small
   programs.
"""

import inspect, sys, os
dir = os.path.dirname(inspect.getfile(inspect.currentframe()))
sys.path.insert(0, dir)
sys.path.insert(0, os.path.join(dir, 'do'))

from config import Config
from shell import Shell, attach_commands
from activeboards import ActiveBoards
from connection import ConnectionError
from board import BoardError
from version import __version__
from printing import debug, quiet, nocolor, oprint, eprint, dprint, qprint
import printing

import argparse


def main():
    """The main program."""

    if sys.version_info.major < 3:
        v = sys.version_info
        eprint("Shell49 requires Python 3.6 (not {}.{}.{})".format(v.major, v.minor, v.micro))
        return

    default_config = os.getenv('SHELL49_CONFIG_FILE') or '~/.shell49_rc.py'
    default_editor = os.getenv('SHELL49_EDITOR') or os.getenv('VISUAL') or os.getenv('EDITOR') or 'vi'
    default_nocolor = 'win32' in sys.platform
    default_debug = False
    default_quiet = False

    parser = argparse.ArgumentParser(
        prog="shell49",
        usage="%(prog)s [options] [cmd]",
        description="Remote Shell for MicroPython boards.",
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
        "-d", "--debug",
        dest="debug",
        action="store_true",
        help="Enable debug features (default %s)" % default_debug,
        default=default_debug
    )
    parser.add_argument(
        "-n", "--nocolor",
        dest="nocolor",
        action="store_true",
        help="Turn off colorized output (default: %s)" % default_nocolor,
        default=default_nocolor
    )
    parser.add_argument(
        "--quiet",
        dest="quiet",
        action="store_true",
        help="Turn off some output (default: %s)" % default_quiet,
        default=False
    )
    parser.add_argument(
        "-a", "--no_auto_connect",
        dest="auto_connect",
        action="store_false",
        help="Do not automatically connect to board connected to serial port",
        default=True
    )
    parser.add_argument(
        '-V', '--version',
        dest='version',
        action='store_true',
        help='Report the version and exit.',
        default=False
    )
    parser.add_argument(
        "-f", "--file",
        dest="filename",
        help="File of commands to process (non-interactive)."
    )
    parser.add_argument(
        "cmd",
        nargs=argparse.REMAINDER,
        help="Optional command to execute and quit."
    )
    args = parser.parse_args(sys.argv[1:])

    debug(args.debug)
    quiet(args.quiet or args.cmd or args.filename)
    if args.nocolor: nocolor()

    dprint("config = %s" % args.config)
    dprint("editor = %s" % args.editor)
    dprint("debug = %s" % args.debug)
    dprint("quiet = %s" % args.quiet)
    dprint("nocolor = %s" % args.nocolor)
    dprint("auto_connect = %s" % args.auto_connect)
    dprint("version = %s" % __version__)
    dprint("cmd = [%s]" % ', '.join(args.cmd))

    if args.version:
        print(__version__)
        return

    cmd_line = ' '.join(args.cmd)
    if not args.filename and cmd_line == '':
        oprint("Welcome to shell49 version {}. Type 'help' for information; Control-D to exit.".format(__version__))

    args.config = os.path.expanduser(args.config)
    args.config = os.path.normpath(args.config)

    with Config(args.config) as config:
        boards = ActiveBoards(config)

        # connect to board ...
        try:
            if args.auto_connect:
                boards.connect_serial(config.get('default', 'port'))
        except (ConnectionError, BoardError) as err:
            eprint(err)
        except KeyboardInterrupt:
            pass

        # start command shell
        attach_commands()
        if args.filename:
            with open(args.filename) as cmd_file:
                shell = Shell(boards, args.editor, stdin=cmd_file)
                shell.cmdloop('')
        else:
            if boards.num_boards() == 0:
                eprint("No MicroPython boards connected - use the connect command to add one.")
            shell = Shell(boards, args.editor)
            try:
                shell.cmdloop(cmd_line)
            except KeyboardInterrupt:
                qprint("Bye")
    print(printing.NO_COLOR)


if __name__ == "__main__":
    main()
