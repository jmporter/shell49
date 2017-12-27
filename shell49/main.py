#! python

"""Remote shell for MicroPython.

   This program uses the raw-repl feature of MicroPython to send small
   programs.
"""

import sys
sys.path.append('shell49')

from shell import Shell
from device import DeviceError, Device, DeviceSerial, DeviceNet
from connect import connect, autoconnect, num_devices
from print_ import oprint, qprint, eprint, dprint
import print_
import globals_
import const

import os
import argparse

def real_main():
    """The main program."""
    try:
        default_baud = int(os.getenv('RSHELL_BAUD'))
    except:
        default_baud = 115200
    default_port = os.getenv('RSHELL_PORT')
    #if not default_port:
    #    default_port = '/dev/ttyACM0'
    default_user = os.getenv('RSHELL_USER') or 'micro'
    default_password = os.getenv('RSHELL_PASSWORD') or 'python'
    default_editor = os.getenv('RSHELL_EDITOR') or os.getenv('VISUAL') or os.getenv('EDITOR') or 'vi'
    try:
        default_buffer_size = int(os.getenv('RSHELL_BUFFER_SIZE'))
    except:
        default_buffer_size = const.BUFFER_SIZE
    parser = argparse.ArgumentParser(
        prog="rshell",
        usage="%(prog)s [options] [command]",
        description="Remote Shell for a MicroPython board.",
        epilog=(
"""
Environment variables:
    RSHELL_PORT        serial port or ip address of remote;
    RSHELL_HOST_DIR    default host directory for rsync command (default: '.');
    RSHELL_REMOTE_DIR  default remote directory for rsync command (default: '/ls ');
    RSHELL_USER        remote login (default: micro);
    RSHELL_PASSWORD    remote password (default: python);
    RSHELL_EDITOR      EDITOR
"""),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-b", "--baud",
        dest="baud",
        action="store",
        type=int,
        help="Set the baudrate used (default = %d)" % default_baud,
        default=default_baud
    )
    parser.add_argument(
        "--buffer-size",
        dest="buffer_size",
        action="store",
        type=int,
        help="Set the buffer size used for transfers (default = %d)" % default_buffer_size,
        default=default_buffer_size
    )
    parser.add_argument(
        "-p", "--port",
        dest="port",
        help="Set the serial port or IP address to use (default '%s')" % default_port,
        default=default_port
    )
    parser.add_argument(
        "-u", "--user",
        dest="user",
        help="Set username to use (default '%s')" % default_user,
        default=default_user
    )
    parser.add_argument(
        "-w", "--password",
        dest="password",
        help="Set password to use (default '%s')" % default_password,
        default=default_password
    )
    parser.add_argument(
        "-e", "--editor",
        dest="editor",
        help="Set the editor to use (default '%s')" % default_editor,
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
        help="Enable debug features",
        default=False
    )
    parser.add_argument(
        "-n", "--nocolor",
        dest="nocolor",
        action="store_true",
        help="Turn off colorized output",
        default=False
    )
    parser.add_argument(
        "-a", "--ascii",
        dest="binary_xfer",
        action="store_true",
        help="ASCII encode binary files for transfer",
    )
    parser.add_argument(
        "--wait",
        dest="wait",
        type=int,
        action="store",
        help="Seconds to wait for serial port",
        default=0
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
        "--quiet",
        dest="quiet",
        action="store_true",
        help="Turns off some output (useful for testing)",
        default=False
    )
    parser.add_argument(
        '--rsync_includes',
        default='*.py,*.json,*.txt,*.html',
        help="file patterns included in rsync"
    )
    parser.add_argument(
        '--rsync_excludes',
        default='.*,__*__',
        help="file patterns excluded from rsync"
    )
    parser.add_argument(
        "cmd",
        nargs=argparse.REMAINDER,
        help="Optional command to execute"
    )
    args = parser.parse_args(sys.argv[1:])

    globals_.ARGS = args

    print_.DEBUG = args.debug
    print_.QUIET = args.quiet

    global EDITOR
    EDITOR = args.editor

    BUFFER_SIZE = args.buffer_size

    if args.nocolor:
        print.nocolor()

    const.BINARY_XFER = args.binary_xfer

    dprint("Debug = %s" % args.debug)
    dprint("Port = %s" % args.port)
    dprint("Baud = %d" % args.baud)
    dprint("User = %s" % args.user)
    dprint("Password = %s" % args.password)
    dprint("Wait = %d" % args.wait)
    dprint("nocolor = %d" % args.nocolor)
    dprint("binary = %d" % args.binary_xfer)
    dprint("Timing = %d" % args.timing)
    dprint("Quiet = %d" % args.quiet)
    dprint("Buffer_size = %d" % args.buffer_size)
    dprint("Cmd = [%s]" % ', '.join(args.cmd))

    if args.version:
        print(__version__)
        return

    if args.port:
        try:
            connect(args.port, baud=args.baud, wait=args.wait, user=args.user, password=args.password)
        except DeviceError as err:
            eprint(err)
    else:
        autoscan()
    autoconnect()

    if args.filename:
        with open(args.filename) as cmd_file:
            shell = Shell(stdin=cmd_file, filename=args.filename, timing=args.timing)
            shell.cmdloop('')
    else:
        cmd_line = ' '.join(args.cmd)
        if cmd_line == '':
            oprint("Welcome to rshell 'Version IoT 49'. Type help for information; Control-D to exit.\n")
        if num_devices() == 0:
            print('')
            eprint('No MicroPython boards connected - use the connect command to add one')
            print('')
        shell = Shell(timing=args.timing)
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
