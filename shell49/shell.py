from . print_ import dprint, eprint, oprint, qprint, cprint
import shell49.print_ as print_
from . config import ConfigError
from . device import DeviceError
from . devs import DevsError
from . pyboard import PyboardError
from . remote_op import is_pattern, resolve_path, auto, get_mode, mode_isdir, \
    chdir, get_stat, stat_mode, mode_exists, listdir_stat, is_visible, \
    decorated_filename, print_cols, mode_isfile, cat, column_print, \
    get_ip_address, get_mac_address, get_time, set_time, osdebug, get_filesize, \
    cp, rsync, mkdir, rm, process_pattern, print_long, trim, unescape, \
    listdir_matches, escape, validate_pattern, get_unique_id, \
    upy_version, recv_file_from_host, send_file_to_remote
from . getch import getch
from . mdns_client import MdnsListenter
from . flasher import Flasher, FlasherError
from . version import __version__

from datetime import datetime
from tempfile import NamedTemporaryFile
import argparse
import cmd
import sys
import os
import glob
import time
import shutil
import shlex
import readline
import itertools
import fnmatch
import threading
import tempfile
import traceback
import serial


# D.H.: I got the following from
# http://www.farmckon.net/2009/08/rlcompleter-how-do-i-get-it-to-work/

# Under OSX, if you call input with a prompt which contains ANSI escape
# sequences for colors, and readline is installed, then the escape sequences
# do not get rendered properly as colors.
#
# One solution would be to not use readline, but then you'd lose TAB completion.
# So I opted to print the colored prompt before calling input, which makes
# things work most of the time. If you try to backspace when at the first
# column of the input it wipes out the prompt, but everything returns to normal
# if you hit return.

BROKEN_READLINE = False

try:
    # on windows, readline.__doc__ is None!
    if 'libedit' in readline.__doc__:
        readline.parse_and_bind("bind ^I rl_complete")
        BROKEN_READLINE = True
    else:
        readline.parse_and_bind("tab: complete")
except:
    pass

FAKE_INPUT_PROMPT = False

if sys.platform == 'darwin':
    # The readline that comes with OSX screws up colors in the prompt
    # BEB - not my mac / not my python
    FAKE_INPUT_PROMPT = False  # True

QUIT_REPL_CHAR = 'X'
QUIT_REPL_BYTE = bytes((ord(QUIT_REPL_CHAR) - ord('@'),))  # Control-X

# DELIMS is used by readline for determining word boundaries.
DELIMS = ' \t\n>;'


class SmartFile(object):
    """Class which implements a write method which takes bytes or str."""

    def __init__(self, file):
        self.file = file

    def close(self):
        self.file.close()

    def flush(self):
        self.file.flush()

    def read(self, num_bytes):
        return self.file.buffer.read(num_bytes)

    def seek(self, pos):
        self.file.seek(pos)

    def tell(self):
        return self.file.tell()

    def write(self, data):
        if isinstance(data, str):
            return self.file.write(data)
        return self.file.buffer.write(data)


class AutoBool(object):
    """A simple class which allows a boolean to be set to False in conjunction
       with a with: statement.
    """

    def __init__(self):
        self.value = False

    def __enter__(self):
        self.value = True

    def __exit__(self, type, value, traceback):
        self.value = False

    def __call__(self):
        return self.value


class ShellError(Exception):
    """Errors that we want to report to the user and keep running."""
    pass


def add_arg(*args, **kwargs):
    """Returns a list containing args and kwargs."""
    return (args, kwargs)


class Shell(cmd.Cmd):
    """Implements the shell as a command line interpreter."""

    def __init__(self, editor, config, devs, filename=None, timing=False, **kwargs):
        cmd.Cmd.__init__(self, **kwargs)
        if 'stdin' in kwargs:
            cmd.Cmd.use_rawinput = 0

        self.editor = editor
        self.config = config
        self.devs = devs

        self.real_stdout = self.stdout
        self.smart_stdout = SmartFile(self.stdout)

        self.stderr = SmartFile(sys.stderr)

        self.filename = filename
        self.line_num = 0
        self.timing = timing

        self.cur_dir = os.path.expanduser(
            config.get(0, 'host_dir', os.getcwd()))
        self.prev_dir = self.cur_dir
        self.columns = shutil.get_terminal_size().columns

        self.redirect_dev = None
        self.redirect_filename = ''
        self.redirect_mode = ''

        self.quit_when_no_output = False
        self.quit_serial_reader = False
        readline.set_completer_delims(DELIMS)

        self.last_run_file = None

        self.set_prompt()

    def set_prompt(self):
        if self.stdin == sys.stdin:
            prompt = print_.PROMPT_COLOR + self.cur_dir + print_.END_COLOR + '> '
            if FAKE_INPUT_PROMPT:
                print(prompt, end='')
                self.prompt = ''
            else:
                self.prompt = prompt
        else:
            # Executing commands from a file
            self.prompt = ''

    def cmdloop(self, line=None):
        if line:
            line = self.precmd(line)
            stop = self.onecmd(line)
            stop = self.postcmd(stop, line)
        else:
            cmd.Cmd.cmdloop(self)

    def onecmd(self, line):
        """Override onecmd.

        1 - So we don't have to have a do_EOF method.
        2 - So we can strip comments
        3 - So we can track line numbers
        """
        try:
            dprint('Executing "%s"' % line)
            self.line_num += 1
            if line == "EOF":
                if cmd.Cmd.use_rawinput:
                    # This means that we printed a prompt, and we'll want to
                    # print a newline to pretty things up for the caller.
                    self.print('')
                return True
            # Strip comments
            comment_idx = line.find("#")
            if comment_idx >= 0:
                line = line[0:comment_idx]
                line = line.strip()

            # search multiple commands on the same line
            lexer = shlex.shlex(line)
            lexer.whitespace = ''

            for issemicolon, group in itertools.groupby(lexer, lambda x: x == ";"):
                if not issemicolon:
                    self.onecmd_exec("".join(group))
        except KeyboardInterrupt:
            pass
        except Exception as e:
            eprint("***", e)
            traceback.print_exc(file=sys.stdout)

    def onecmd_exec(self, line):
        try:
            if self.timing:
                start_time = time.time()
                result = cmd.Cmd.onecmd(self, line)
                end_time = time.time()
                print('took %.3f seconds' % (end_time - start_time))
                return result
            else:
                return cmd.Cmd.onecmd(self, line)
        except DevsError as err:
            eprint(err)
        except DeviceError as err:
            eprint(err)
        except ShellError as err:
            eprint(err)
        except SystemExit:
            # When you use -h with argparse it winds up call sys.exit, which
            # raises a SystemExit. We intercept it because we don't want to
            # exit the shell, just the command.
            return False

    def default(self, line):
        eprint("Unrecognized command:", line)

    def emptyline(self):
        """We want empty lines to do nothing. By default they would repeat the
        previous command.

        """
        pass

    def precmd(self, line):
        self.stdout = self.smart_stdout
        return line

    def postcmd(self, stop, line):
        if self.stdout != self.smart_stdout:
            if self.redirect_dev is not None:
                # Redirecting to a remote device, now that we're finished the
                # command, we can copy the collected output to the remote.
                dprint('Copy redirected output to "%s"' %
                       self.redirect_filename)
                # This belongs on the remote. Copy/append now
                filesize = self.stdout.tell()
                self.stdout.seek(0)
                self.redirect_dev.remote(recv_file_from_host, self.stdout,
                                         self.redirect_filename, filesize,
                                         dst_mode=self.redirect_mode,
                                         xfer_func=send_file_to_remote)
            self.stdout.close()
        self.stdout = self.real_stdout
        if not stop:
            self.set_prompt()
        return stop

    def print(self, *args, end='\n', file=None):
        """Convenience function so you don't need to remember to put the \n
           at the end of the line.
        """
        if file is None:
            file = self.stdout
        s = ' '.join(str(arg) for arg in args) + end
        file.write(s)

    def create_argparser(self, command):
        try:
            argparse_args = getattr(self, "argparse_" + command)
        except AttributeError:
            return None
        doc_lines = getattr(
            self, "do_" + command).__doc__.expandtabs().splitlines()
        if '' in doc_lines:
            blank_idx = doc_lines.index('')
            usage = doc_lines[:blank_idx]
            description = doc_lines[blank_idx + 1:]
        else:
            usage = doc_lines
            description = []
        parser = argparse.ArgumentParser(
            prog=command,
            usage='\n'.join(usage),
            description='\n'.join(description),
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        for args, kwargs in argparse_args:
            parser.add_argument(*args, **kwargs)
        return parser

    def filename_complete(self, text, line, begidx, endidx):
        """Wrapper for catching exceptions since cmd seems to silently
           absorb them.
        """
        try:
            return self.real_filename_complete(text, line, begidx, endidx)
        except:
            traceback.print_exc()

    def real_filename_complete(self, text, line, begidx, endidx):
        """Figure out what filenames match the completion."""

        # line contains the full command line that's been entered so far.
        # text contains the portion of the line that readline is trying to complete
        # text should correspond to line[begidx:endidx]
        #
        # The way the completer works text will start after one of the characters
        # in DELIMS. So if the filename entered so far was "embedded\ sp" and
        # then text will point to the s in sp.
        #
        # The following bit of logic backs up to find the real beginning of the
        # filename.

        for before_match in range(begidx, 0, -1):
            if line[before_match] in DELIMS and before_match >= 1 and line[before_match - 1] != '\\':
                break

        # We set fixed to be the portion of the filename which is before text
        # and match is the full portion of the filename that's been entered so
        # far (that's that part we use for matching files).
        #
        # When we return a list of completions, the bit that we return should
        # just be the portion that we replace 'text' with.

        # fixed portion of the match
        fixed = unescape(line[before_match + 1:begidx])
        # portion to match filenames against
        match = unescape(line[before_match + 1:endidx])

        # We do the following to cover the case that the current directory
        # is / and the path being entered is relative.
        if match[0] == '/':
            abs_match = match
        elif self.cur_dir == '/':
            abs_match = self.cur_dir + match
        else:
            abs_match = self.cur_dir + '/' + match

        completions = []
        prepend = ''
        if abs_match.rfind('/') == 0:  # match is in the root directory
            # This means that we're looking for matches in the root directory
            # (i.e. abs_match is /foo and the user hit TAB).
            # So we'll supply the matching board names as possible completions.
            # Since they're all treated as directories we leave the trailing slash.
            if match[0] == '/':
                completions += [dev.name_path() for dev in self.devs.devices()
                                if dev.name_path().startswith(abs_match)]
            else:
                completions += [dev.name_path()[1:] for dev in self.devs.devices()
                                if dev.name_path().startswith(abs_match)]
            try:
                # Add root directories of the default device
                def_dev = self.devs.default_device()
                if match[0] == '/':
                    completions += [
                        root_dir for root_dir in def_dev.root_dirs if root_dir.startswith(match)]
                else:
                    completions += [root_dir[1:]
                                    for root_dir in def_dev.root_dirs if root_dir[1:].startswith(match)]
            except DevsError:
                pass
        else:
            # This means that there are at least 2 slashes in abs_match. If one
            # of them matches a board name then we need to remove the board
            # name from fixed. Since the results from listdir_matches won't
            # contain the board name, we need to prepend each of the completions.
            for dev in self.devs.devices():
                if abs_match.startswith(dev.name_path()):
                    prepend = dev.name_path()[:-1]

        paths = sorted(auto(self.devs, listdir_matches, match))
        for path in paths:
            path = prepend + path
            completions.append(escape(path.replace(fixed, '', 1)))
        return completions

    def directory_complete(self, text, line, begidx, endidx):
        """Figure out what directories match the completion."""
        return [filename for filename in self.filename_complete(text, line, begidx, endidx) if filename[-1] == '/']

    def line_to_args(self, line):
        """This will convert the line passed into the do_xxx functions into
        an array of arguments and handle the Output Redirection Operator.
        """
        args = line.split()
        self.redirect_filename = ''
        self.redirect_dev = None
        redirect_index = -1
        if '>' in args:
            redirect_index = args.index('>')
        elif '>>' in args:
            redirect_index = args.index('>>')
        if redirect_index >= 0:
            if redirect_index + 1 >= len(args):
                raise ShellError("> requires a filename")
            self.redirect_filename = resolve_path(
                self.cur_dir, args[redirect_index + 1])
            rmode = auto(self.devs, self.devs, get_mode,
                         os.path.dirname(self.redirect_filename))
            if not mode_isdir(rmode):
                raise ShellError("Unable to redirect to '%s', directory doesn't exist" %
                                 self.redirect_filename)
            if args[redirect_index] == '>':
                self.redirect_mode = 'w'
                dprint('Redirecting (write) to', self.redirect_filename)
            else:
                self.redirect_mode = 'a'
                dprint('Redirecting (append) to', self.redirect_filename)
            self.redirect_dev, self.redirect_filename = self.devs.get_dev_and_path(
                self.redirect_filename)
            try:
                if self.redirect_dev is None:
                    self.stdout = SmartFile(
                        open(self.redirect_filename, self.redirect_mode))
                else:
                    # Redirecting to a remote device. We collect the results locally
                    # and copy them to the remote device at the end of the command.
                    self.stdout = SmartFile(tempfile.TemporaryFile(mode='w+'))
            except OSError as err:
                raise ShellError(err)

            del args[redirect_index + 1]
            del args[redirect_index]
        curr_cmd, _, _ = self.parseline(self.lastcmd)
        parser = self.create_argparser(curr_cmd)
        if parser:
            args = parser.parse_args(args)
        return args

    def do_args(self, line):
        """args [arguments...]

           Debug function for verifying argument parsing. This function just
           prints out each argument that it receives.
        """
        args = self.line_to_args(line)
        for idx in range(len(args)):
            self.print("arg[%d] = '%s'" % (idx, args[idx]))

    def do_version(self, line):
        """version

        Print shell49 and MicroPython version information.
        """
        dd = self.devs.default_device()
        release, machine, version = dd.remote_eval(upy_version)
        fmt = "{:>10s} = {}"
        oprint(fmt.format("board", dd.get('name')))
        oprint(fmt.format("firmware", version))
        oprint(fmt.format("release", release))
        oprint(fmt.format("machine", machine))
        oprint(fmt.format("shell49", __version__))

    def do_mdns(self, line):
        """mdns

        List all MicroPython boards advertising repl telnet via mdns.
        """
        listener = MdnsListenter()
        cprint("url                  ip               port   spec",
               color=print_.PY_COLOR)
        for b in listener.listen(seconds=1):
            oprint("{:20s} {:14s}    {:2d}    {}".format(
                b.url, b.ip, b.port, b.spec))

    def do_boards(self, line):
        """boards          List connected devices.
        boards #        Make board number # the default board.
        boards NAME     Make board NAME the default board.
        """
        try:
            self.devs.default_device(index=int(line))
        except ValueError:
            self.devs.default_device(name=line)
        rows = []
        rows.append(("#", "Name", "Port/IP", "Unique ID", "Directories"))
        for index, dev in enumerate(self.devs.devices()):
            name = dev.name()
            if not name:
                name = '-'
            if dev is self.devs.default_device():
                dirs = [dir[:-1] for dir in dev.root_directories()]
            else:
                dirs = []
            if dev.name():
                dirs += ['/{}{}'.format(name, dir)[:-1]
                         for dir in dev.root_directories()]
            dirs = ', '.join(dirs)
            default = '*' if dev is self.devs.default_device() else ''
            rows.append((default + str(index + 1), name,
                         dev.address(), dev.get_id(), dirs))
        if len(rows) > 1:
            column_print('><<< ', rows, self.print)
        else:
            print('No boards connected')

    argparse_config = (
        add_arg(
            '-u', '--upload',
            dest='upload',
            action='store_true',
            help='upload configuration to board',
            default=False
        ),
        add_arg(
            '-d', '--delete',
            dest='delete',
            action='store_true',
            help='delete option',
            default=False
        ),
        add_arg(
            '--default',
            dest='default',
            action='store_true',
            help='set default option value',
            default=False
        ),
        add_arg(
            'option',
            metavar='OPTION',
            nargs='?',
            help='option name'
        ),
        add_arg(
            'value',
            metavar='VALUE',
            nargs='*',
            help='option value'
        ),
    )

    def print_config(self, id, *, exc={}, color=print_.OUTPUT_COLOR):
        for k in sorted(self.config.options(id)):
            if not k in exc:
                v = self.config.get(id, k)
                cprint("{:>20s} = {}".format(k, v), color=color)

    def do_config(self, line):
        """config                                   Print option values.
       config [-u] [-d] [--default] OPTION [VALUE]   Set/delete OPTION to VALUE.

       Options:
          --default                                  Act on default configuration, rather than default board.
          -d                                         Delete rather than set OPTION.
          -u                                         Upload configuration to default board.
        """
        def_dev = None
        board_id = 'default'
        try:
            def_dev = self.devs.default_device()
            board_id = def_dev.get_id()
        except DevsError:
            pass

        if line == '':
            # print configuration
            self.print_config(board_id, color=print_.PY_COLOR)
            if def_dev:
                oprint("Defaults:")
                keys = def_dev.options()
                self.print_config('default', exc=keys)
            return

        # parse arguments
        args = self.line_to_args(line)
        if args.default:
            board_id = 'default'
            def_dev = None
        value = ' '.join(args.value)
        try:
            # try to convert value to Python object (e.g. for numbers)
            value = eval(value)
        except:
            pass
        if not args.default and not def_dev:
            eprint("*** No board connected, use --default to change default configuration")
            return

        # delete / set option value
        if args.delete:
            # delete option
            self.config.remove(board_id, args.option)
        else:
            # set option
            try:
                self.config.set(board_id, args.option, value)
            except ConfigError as e:
                eprint("*** {}".format(e))

        # upload
        if args.upload:
            if not def_dev:
                eprint("*** No board connected, cannot upload configuration")
                return
            with NamedTemporaryFile() as temp:
                temp.close()
                f = open(temp.name, 'w')
                now = datetime.now().strftime("%Y-%b-%d %H:%M:%S")
                print("# config.py, created on {}".format(now), file=f)
                for key in def_dev.options():
                    print("{} = {}".format(key, repr(def_dev.get(key))), file=f)
                f.close()
                dst = os.path.join(def_dev.get(
                    'remote_dir', '/flash'), 'config.py')
                cp(self.devs, temp.name, dst)
                os.unlink(temp.name)


    argparse_flash = (
        add_arg(
            '-l', '--list',
            dest='list',
            action='store_true',
            help='list firmware versions (no flashing)',
            default=False
        ),
        add_arg(
            '-e', '--erase',
            dest='erase',
            action='store_true',
            help='erase flash memory (including file system) before flashing firmware',
            default=False
        ),
        add_arg(
            '-v', '--version',
            dest='version',
            help='firmware version',
            default='STABLE'
        ),
        add_arg(
            '-b', '--board',
            dest='board',
            help='microcontroller board (e.g. HUZZAH32)',
            default=None
        ),
    )

    def do_flash(self, line):
        """flash [-l|--list] [-e|--erase] [-v|--version VERSION] [-b|--board BOARD]

        Flash firmware to microcontroller.
        """

        args = self.line_to_args(line)
        firmware_url = "https://people.eecs.berkeley.edu/~boser/iot49/firmware"
        flash_options = "--chip esp32 " \
            "--before default_reset --after hard_reset " \
            "write_flash -z --flash_mode dio --flash_freq 40m --flash_size detect"
        id = 0
        try:
            id = self.devs.default_device().get_id()
        except DevsError:
            pass
        firmware_url = self.config.get(id, "firmware_url", firmware_url)
        flash_options = self.config.get(id, "flash_options", flash_options)
        port = self.config.get(id, "port", "/dev/cu.SLAB_USBtoUART")
        baudrate = self.config.get(id, "flash_baudrate", 921600)
        board = self.config.get(id, "board", "HUZZAH32")
        if args.board:
            board = args.board

        dprint("firmware url: ", firmware_url)
        dprint("flash options:", flash_options)
        dprint("port:         ", port)
        dprint("baudrate:     ", baudrate)
        dprint("board:        ", board)

        try:
            f = Flasher(board=board, url=firmware_url)
            if args.list:
                oprint("available firmware versions:")
                oprint('\n'.join(["  {:8s} {}".format(v, d)
                                  for v, d in f.versions()]))
                return
            dev = self.devs.find_serial_device_by_port(port)
            if dev: dev.close()
            if args.erase:
                f.erase_flash(port)
            f.flash(args.version, flash_options=flash_options,
                    port=port, baudrate=baudrate)
        except FlasherError as e:
            eprint(e)

    def complete_cat(self, text, line, begidx, endidx):
        return self.filename_complete(text, line, begidx, endidx)

    def do_cat(self, line):
        """cat FILENAME...

           Concatenates files and sends to stdout.
        """
        # note: when we get around to supporting cat from stdin, we'll need
        #       to write stdin to a temp file, and then copy the file
        #       since we need to know the filesize when copying to the pyboard.
        args = self.line_to_args(line)
        for filename in args:
            filename = resolve_path(self.cur_dir, filename)
            mode = auto(self.devs, get_mode, filename)
            if not mode_exists(mode):
                eprint("Cannot access '%s': No such file" % filename)
                continue
            if not mode_isfile(mode):
                eprint("'%s': is not a file" % filename)
                continue
            cat(self.devs, filename, self.stdout)

    def complete_cd(self, text, line, begidx, endidx):
        return self.directory_complete(text, line, begidx, endidx)

    def do_cd(self, line):
        """cd DIRECTORY

           Changes the current directory. ~ expansion is supported, and cd -
           goes to the previous directory.
        """
        args = self.line_to_args(line)
        if len(args) == 0:
            dirname = '~'
        else:
            if args[0] == '-':
                dirname = self.prev_dir
            else:
                dirname = args[0]
        dirname = resolve_path(self.cur_dir, dirname)

        mode = auto(self.devs, get_mode, dirname)
        if mode_isdir(mode):
            self.prev_dir = self.cur_dir
            self.cur_dir = dirname
            auto(self.devs, chdir, dirname)
        else:
            eprint("Directory '%s' does not exist" % dirname)

    def serial_ports(self):
        """ Lists serial port names

            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        """
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        else:
            ports = glob.glob('/dev/*')
            ports = [ p for p in ports if 'usb' in p.lower() ]

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result

    def do_ports(self, line):
        """do_ports

        List available USB ports."""
        available = self.serial_ports()
        connected = [ d.address() for d in self.devs.devices() ]
        all = sorted(set(available + connected))
        for p in all:
            oprint("{} {}".format("*" if p in connected else " ", p))

    def do_connect(self, line):
        """connect TYPE TYPE_PARAMS       Connect boards to shell49.
        connect serial [port [baud]]   Serial connection. Uses defaults from config file.
        connect telnet [url]           Wireless connection. If no url/ip address is
                                       specified, connects to all known boards advertising
                                       repl service via mDNS.

        Note: do not connect to the same board via serial AND telnet connections.
              Doing so may block communication with the board.
        """
        args = self.line_to_args(line)
        if len(args) < 1:
            eprint('Missing connection TYPE')
            return
        connect_type = args[0]
        if connect_type == 'serial':
            port = args[1] if len(args) > 1 else self.config.get(
                0, 'port', '/dev/cu.SLAB_USBtoUART')
            baud = args[2] if len(args) > 2 else self.config.get(
                0, 'baudrate', '115200')
            try:
                baud = int(baud)
            except ValueError:
                eprint("Not a valid baudrate, '{}'".format(baud))
                return
            # Note: board may be connected over telnet, but we don't know ...
            #       in this case, connect blocks
            if self.devs.find_serial_device_by_port(port):
                eprint("board already connected on '{}'".format(port))
                return
            self.devs.connect_serial(port, baud)
        elif connect_type == 'telnet':
            if len(args) > 1:
                self.devs.connect_telnet(args[1])
            else:
                listener = MdnsListenter()
                for b in listener.listen(seconds=1):
                    qprint("Heard from '{}' ({})".format(b.url, b.ip))
                    # connect only to boards in the config database
                    if not self.config.has_board_with_name(b.hostname):
                        qprint("  not in db, skip!")
                        continue
                    # we are not already connected to
                    if self.devs.is_connected(b.hostname):
                        qprint("  already connected")
                        continue
                    # let's connect!
                    self.devs.connect_telnet(b.url)
        else:
            eprint('Unrecognized connection TYPE: {}'.format(connect_type))

    def complete_cp(self, text, line, begidx, endidx):
        return self.filename_complete(text, line, begidx, endidx)

    def do_cp(self, line):
        """cp SOURCE DEST               Copy a single SOURCE file to DEST file.
       cp SOURCE... DIRECTORY       Copy multiple SOURCE files to a directory.
       cp [-r] PATTERN DIRECTORY    Copy matching files to DIRECTORY.
       cp [-r|--recursive] [SOURCE|SOURCE_DIR]... DIRECTORY

           The destination must be a directory except in the case of
           copying a single file. To copy directories -r must be specified.
           This will cause directories and their contents to be recursively
           copied.
        """
        args = self.line_to_args(line)
        if len(args.filenames) < 2:
            eprint('Missing destination file')
            return
        dst_dirname = resolve_path(self.cur_dir, args.filenames[-1])
        dst_mode = auto(self.devs, get_mode, dst_dirname)
        d_dst = {}  # Destination directory: lookup stat by basename
        if args.recursive:
            dst_files = auto(self.devs, listdir_stat, dst_dirname)
            if dst_files is None:
                err = "cp: target {} is not a directory"
                eprint(err.format(dst_dirname))
                return
            for name, stat in dst_files:
                d_dst[name] = stat

        src_filenames = args.filenames[:-1]

        # Process PATTERN
        sfn = src_filenames[0]
        if is_pattern(sfn):
            if len(src_filenames) > 1:
                eprint("Usage: cp [-r] PATTERN DIRECTORY")
                return
            src_filenames = process_pattern(self.devs, self.cur_dir, sfn)
            if src_filenames is None:
                return

        for src_filename in src_filenames:
            if is_pattern(src_filename):
                eprint("Only one pattern permitted.")
                return
            src_filename = resolve_path(self.cur_dir, src_filename)
            src_mode = auto(self.devs, get_mode, src_filename)
            if not mode_exists(src_mode):
                eprint("File '{}' doesn't exist".format(src_filename))
                return
            if mode_isdir(src_mode):
                if args.recursive:  # Copying a directory
                    src_basename = os.path.basename(src_filename)
                    dst_filename = os.path.join(dst_dirname, src_basename)
                    if src_basename in d_dst:
                        dst_stat = d_dst[src_basename]
                        dst_mode = stat_mode(dst_stat)
                        if not mode_isdir(dst_mode):
                            err = "Destination {} is not a directory"
                            eprint(err.format(dst_filename))
                            return
                    else:
                        if not mkdir(dst_filename):
                            err = "Unable to create directory {}"
                            eprint(err.format(dst_filename))
                            return

                    rsync(src_filename, dst_filename, mirror=False, dry_run=False,
                          print_func=lambda *args: None, recursed=False)
                else:
                    eprint("Omitting directory {}".format(src_filename))
                continue
            if mode_isdir(dst_mode):
                dst_filename = os.path.join(
                    dst_dirname, os.path.basename(src_filename))
            else:
                dst_filename = dst_dirname
            if not cp(self.devs, src_filename, dst_filename):
                err = "Unable to copy '{}' to '{}'"
                eprint(err.format(src_filename, dst_filename))
                break

    def do_echo(self, line):
        """echo TEXT...

           Display a line of text.
        """
        args = self.line_to_args(line)
        self.print(*args)

    def complete_edit(self, text, line, begidx, endidx):
        return self.filename_complete(text, line, begidx, endidx)

    def do_edit(self, line):
        """edit FILE

           Copies the file locally, launches an editor to edit the file.
           When the editor exits, if the file was modified then its copied
           back.

           You can specify the editor used with the --editor command line
           option when you start shell49, or by using the SHELL49_EDITOR or VISUAL
           or EDITOR environment variable. If none of those are set, then
           vi will be used.
        """
        if len(line) == 0:
            eprint("Must provide a filename")
            return
        filename = resolve_path(self.cur_dir, line)
        dev, dev_filename = self.devs.get_dev_and_path(filename)
        mode = auto(self.devs, get_mode, filename)
        if mode_exists(mode) and mode_isdir(mode):
            eprint("Unable to edit directory '{}'".format(filename))
            return
        if dev is None:
            # File is local
            os.system("{} '{}'".format(self.editor, filename))
        else:
            # File is remote
            with tempfile.TemporaryDirectory() as temp_dir:
                local_filename = os.path.join(
                    temp_dir, os.path.basename(filename))
                if mode_exists(mode):
                    print('Retrieving {} ...'.format(filename))
                    cp(filename, local_filename)
                old_stat = get_stat(local_filename)
                os.system("{} '{}'".format(self.editor, local_filename))
                new_stat = get_stat(local_filename)
                if old_stat != new_stat:
                    self.print('Updating {} ...'.format(filename))
                    cp(local_filename, filename)

    def complete_filesize(self, text, line, begidx, endidx):
        return self.filename_complete(text, line, begidx, endidx)

    def do_filesize(self, line):
        """filesize FILE

           Prints the size of the file, in bytes. This function is primarily
           testing.
        """
        if len(line) == 0:
            eprint("Must provide a filename")
            return
        filename = resolve_path(self.cur_dir, line)
        self.print(auto(self.devs, get_filesize, filename))

    def complete_filetype(self, text, line, begidx, endidx):
        return self.filename_complete(text, line, begidx, endidx)

    def do_filetype(self, line):
        """filetype FILE

           Prints the type of file (dir or file). This function is primarily
           for testing.
        """
        if len(line) == 0:
            eprint("Must provide a filename")
            return
        filename = resolve_path(self.cur_dir, line)
        mode = auto(self.devs, get_mode, filename)
        if mode_exists(mode):
            if mode_isdir(mode):
                self.print('dir')
            elif mode_isfile(mode):
                self.print('file')
            else:
                self.print('unknown')
        else:
            self.print('missing')

    def do_help(self, line):
        """help [COMMAND]

           List available commands with no arguments, or detailed help when
           a command is provided.

           help all

           prints out help for all commands.
        """
        # We provide a help function so that we can trim the leading spaces
        # from the docstrings. The builtin help function doesn't do that.
        if not line:
            cmd.Cmd.do_help(self, line)
            self.print("'help all' prints help for all commands.\n")
            self.print("Use Control-D to exit shell49.")
            return
        parser = self.create_argparser(line)
        if parser:
            parser.print_help()
            return
        try:
            doc = getattr(self, 'do_' + line).__doc__
            if doc:
                self.print("%s" % trim(doc))
                return
        except AttributeError:
            if 'all' in line:
                for k in dir(self):
                    if k.startswith('do_'):
                        doc = getattr(self, k).__doc__
                        self.print(
                            "-- help for {} {}\n".format(k[3:], '-' * (64 - len(k))))
                        self.print("{}\n\n".format(trim(doc)))
            else:
                self.print(str(self.nohelp % (line,)))

    argparse_ls = (
        add_arg(
            '-a', '--all',
            dest='all',
            action='store_true',
            help='do not ignore hidden files',
            default=False
        ),
        add_arg(
            '-l', '--long',
            dest='long',
            action='store_true',
            help='use a long listing format',
            default=False
        ),
        add_arg(
            'filenames',
            metavar='FILE',
            nargs='*',
            help='Files directories or patterns to list'
        ),
    )

    def complete_ls(self, text, line, begidx, endidx):
        return self.filename_complete(text, line, begidx, endidx)

    def do_ls(self, line):
        """ls [-a] [-l] [FILE|DIRECTORY|PATTERN]...
       PATTERN supports * ? [seq] [!seq] Unix filename matching

           List directory contents.
        """
        args = self.line_to_args(line)
        if len(args.filenames) == 0:
            args.filenames = ['.']
        for idx, fn in enumerate(args.filenames):
            if not is_pattern(fn):
                filename = resolve_path(self.cur_dir, fn)
                stat = auto(self.devs, get_stat, filename)
                mode = stat_mode(stat)
                if not mode_exists(mode):
                    err = "Cannot access '{}': No such file or directory"
                    eprint(err.format(filename))
                    continue
                if not mode_isdir(mode):
                    if args.long:
                        print_long(filename, stat, self.print)
                    else:
                        self.print(filename)
                    continue
                if len(args.filenames) > 1:
                    if idx > 0:
                        self.print('')
                    self.print("%s:" % filename)
                pattern = '*'
            else:  # A pattern was specified
                filename, pattern = validate_pattern(
                    self.devs, self.cur_dir, fn)
                if filename is None:  # An error was printed
                    continue
            files = []
            ldir_stat = auto(self.devs, listdir_stat, filename)
            if ldir_stat is None:
                err = "Cannot access '{}': No such file or directory"
                eprint(err.format(filename))
            else:
                for filename, stat in sorted(ldir_stat,
                                             key=lambda entry: entry[0]):
                    if is_visible(filename) or args.all:
                        if fnmatch.fnmatch(filename, pattern):
                            if args.long:
                                print_long(filename, stat, self.print)
                            else:
                                files.append(
                                    decorated_filename(filename, stat))
            if len(files) > 0:
                print_cols(sorted(files), self.print, self.columns)

    def complete_mkdir(self, text, line, begidx, endidx):
        return self.filename_complete(text, line, begidx, endidx)

    def do_mkdir(self, line):
        """mkdir DIRECTORY...

           Creates one or more directories.
        """
        args = self.line_to_args(line)
        for filename in args:
            filename = resolve_path(self.cur_dir, filename)
            if not mkdir(self.devs, filename):
                eprint('Unable to create %s' % filename)

    def repl_serial_to_stdout(self, dev):
        """Runs as a thread which has a sole purpose of reading bytes from
           the serial port and writing them to stdout. Used by do_repl.
        """
        with self.serial_reader_running:
            try:
                save_timeout = dev.timeout()
                # Set a timeout so that the read returns periodically with no data
                # and allows us to check whether the main thread wants us to quit.
                dev.timeout(0.5)
                while not self.quit_serial_reader:
                    try:
                        char = dev.read(1)
                    except serial.serialutil.SerialException:
                        # This happens if the pyboard reboots, or a USB port
                        # goes away.
                        return
                    except TypeError:
                        # There is a bug in serialposix.py starting with python 3.3
                        # which causes a TypeError during the handling of the
                        # select.error. So we treat this the same as
                        # serial.serialutil.SerialException:
                        return
                    except ConnectionResetError:
                        # This happens over a telnet seesion, if it resets
                        return
                    if not char:
                        # This means that the read timed out. We'll check the quit
                        # flag and return if needed
                        if self.quit_when_no_output:
                            break
                        continue
                    print(char.decode('ascii'), end='', flush=True)
                dev.timeout(save_timeout)
            except DeviceError:
                # The device is no longer present.
                return

    def do_repl(self, line):
        """repl [board-name] [~ line [~]]

           Enters into the regular REPL (read-eval-print-loop) with the
           MicroPython board.
           Use Control-X to exit REPL mode and return the shell.
           It may take a couple of seconds before the REPL exits.

           If you provide a line to the repl command, then that will be executed.
           If you want the REPL to exit, end the line with the ~ character.
        """
        args = self.line_to_args(line)
        if len(args) > 0 and line[0] != '~':
            name = args[0]
            line = ' '.join(args[1:])
        else:
            name = ''
        dev = self.devs.find_device_by_name(name)
        if not dev:
            eprint("Unable to find board '%s'" % name)
            return

        if line[0:2] == '~ ':
            line = line[2:]

        self.print(print_.PY_COLOR, end='')
        self.print('Entering REPL. Use Control-%c to exit.' % QUIT_REPL_CHAR)
        self.print('   Soft reset:  Control-D or sys.exit()')
        self.print('   Hard reset:  Reset button on board or machine.reset()')
        self.quit_serial_reader = False
        self.quit_when_no_output = False
        self.serial_reader_running = AutoBool()
        repl_thread = threading.Thread(
            target=self.repl_serial_to_stdout, args=(dev,), name='REPL_serial_to_stdout')
        repl_thread.daemon = True
        repl_thread.start()
        # Wait for reader to start
        while not self.serial_reader_running():
            pass
        try:
            # Wake up the prompt
            dev.write(b'\r')
            if line:
                if line[-1] == '~':
                    line = line[:-1]
                    self.quit_when_no_output = True
                line = ';'.join(line.split('~'))
                dev.write(bytes(line, encoding='utf-8'))
                dev.write(b'\r')
            if not self.quit_when_no_output:
                while self.serial_reader_running():
                    char = getch()
                    if not char:
                        continue
                    if char == QUIT_REPL_BYTE:
                        self.quit_serial_reader = True
                        # When using telnet with the WiPy, it doesn't support
                        # an initial timeout. So for the meantime, we send a
                        # space which should cause the wipy to echo back a
                        # space which will wakeup our reader thread so it will
                        # notice the quit.
                        dev.write(b' ')
                        # Give the reader thread a chance to detect the quit
                        # then we don't have to call getch() above again which
                        # means we'd need to wait for another character.
                        time.sleep(0.5)
                        # Print a newline so that the shell49 prompt looks good.
                        self.print(print_.PY_COLOR)
                        # We stay in the loop so that we can still enter
                        # characters until we detect the reader thread quitting
                        # (mostly to cover off weird states).
                        continue
                    if char == b'\n':
                        dev.write(b'\r')
                    else:
                        dev.write(char)
        except DeviceError as err:
            # The device is no longer present.
            self.print('')
            self.stdout.flush()
            eprint(err)
        repl_thread.join()
        self.print(print_.END_COLOR)

    argparse_cp = (
        add_arg(
            '-r', '--recursive',
            dest='recursive',
            action='store_true',
            help='Copy directories recursively',
            default=False
        ),
        add_arg(
            'filenames',
            metavar='FILE',
            nargs='+',
            help='Pattern or files and directories to copy'
        ),
    )

    argparse_rm = (
        add_arg(
            '-r', '--recursive',
            dest='recursive',
            action='store_true',
            help='remove directories and their contents recursively',
            default=False
        ),
        add_arg(
            '-f', '--force',
            dest='force',
            action='store_true',
            help='ignore nonexistent files and arguments',
            default=False
        ),
        add_arg(
            'filename',
            metavar='FILE',
            nargs='+',
            help='Pattern or files and directories to remove'
        ),
    )

    def complete_rm(self, text, line, begidx, endidx):
        return self.filename_complete(text, line, begidx, endidx)

    def do_rm(self, line):
        """rm [-f|--force] FILE...            Remove one or more files
       rm [-f|--force] PATTERN            Remove multiple files
       rm -r [-f|--force] [FILE|DIRECTORY]... Files and/or directories
       rm -r [-f|--force] PATTERN         Multiple files and/or directories

           Removes files or directories. To remove directories (and
           any contents) -r must be specified.

        """
        args = self.line_to_args(line)
        filenames = args.filename
        # Process PATTERN
        sfn = filenames[0]
        if is_pattern(sfn):
            if len(filenames) > 1:
                eprint("Usage: rm [-r] [-f] PATTERN")
                return
            filenames = process_pattern(self.devs, self.cur_dir, sfn)
            if filenames is None:
                return

        for filename in filenames:
            filename = resolve_path(self.cur_dir, filename)
            if not rm(self.devs, filename, recursive=args.recursive, force=args.force):
                if not args.force:
                    eprint("Unable to remove '{}'".format(filename))
                break

    def do_shell(self, line):
        """!some-shell-command args

           Launches a shell and executes whatever command you provide. If you
           don't provide any commands, then it will launch a bash sub-shell
           and when exit from bash (Control-D) then it will return to shell49.
        """
        if not line:
            line = '/bin/bash'
        os.system(line)

    argparse_rsync = (
        add_arg(
            '-m', '--mirror',
            dest='mirror',
            action='store_true',
            help="causes files in the destination which don't exist in "
                 "the source to be removed. Without --mirror only file "
                 "copies occur. No deletions will take place.",
            default=True,
        ),
        add_arg(
            '-n', '--dry-run',
            dest='dry_run',
            action='store_true',
            help='shows what would be done without actually performing '
            'any file copies.',
            default=False
        ),
        add_arg(
            'src_dst_dir',
            nargs=argparse.REMAINDER,
            metavar='SRC_DIR',
            default='.',
            help='Source and destination directories'
        )
    )

    def do_rsync(self, line):
        """rsync [-m|--mirror] [-n|--dry-run] [SRC_DIR [DEST_DIR]]

           Synchronize destination directory tree to source directory tree.
        """
        dd = self.devs.default_device()
        host_dir = dd.get('host_dir', '~/iot49')
        remote_dir = dd.get('remote_dir', '/flash')
        args = self.line_to_args(line)
        sd = args.src_dst_dir
        if len(sd) > 2:
            eprint("*** More than one destination directory given")
            return
        src_dir = sd[0] if len(sd) > 0 else host_dir
        dst_dir = sd[1] if len(sd) > 1 else remote_dir
        src_dir = resolve_path(self.cur_dir, src_dir)
        dst_dir = resolve_path(self.cur_dir, dst_dir)
        if len(sd) < 2:
            qprint("synchronizing {} --> {}".format(src_dir, dst_dir))
        rsync(self.devs, src_dir, dst_dir,
              mirror=args.mirror, dry_run=args.dry_run, recursed=True)

    def complete_run(self, text, line, begidx, endidx):
        return self.filename_complete(text, line, begidx, endidx)

    def do_run(self, line):
        """run [FILE]

        Send file to remote for execution and print results on console.

        If FILE is not specified, executes the file from the last invocation.
        """
        args = line.split()
        if len(args) > 1:
            eprint("*** Only one file, please!")
            return

        if len(args) == 0:
            file = self.last_run_file
            qprint("run '{}' on micropython board".format(file))
        else:
            file = os.path.join(self.cur_dir, args[0])
            self.last_run_file = file

        try:
            self.devs.default_device().runfile(file)
        except TypeError:
            eprint("*** No file specified")
        except FileNotFoundError:
            eprint("*** File not found,", file)
        except PyboardError as err:
            eprint("*** Syntax:", str(err))

    def do_time(self, line):
        """time [now]

        Inquire time on micropython board.
        If the optional now argument is given, synchronizes the time of the
        board to the host (Note: run by default on program start).
        """
        if 'now' in line:
            now = time.localtime(time.time())
            self.devs.default_device().remote(set_time, now.tm_year, now.tm_mon, now.tm_mday,
                                              now.tm_hour, now.tm_min, now.tm_sec)
        oprint(self.devs.default_device().remote(
            get_time).decode('utf-8'), end='')

    def do_ip(self, line):
        """ip

        Inquire and print out IP address of micropython board.
        """
        oprint(self.devs.default_device().remote(
            get_ip_address).decode('utf-8'), end='')

    def do_mac(self, line):
        """mac

        Inquire and print out MAC address of micropython board.
        """
        oprint(self.devs.default_device().remote(
            get_mac_address).decode('utf-8'), end='')

    def do_id(self, line):
        """id

        Inquire board id (machine.unique_id()).
        """
        oprint(self.devs.default_device().remote(
            get_unique_id, "none").decode('utf-8'), end='')

    def do_osdebug(self, line):
        """osdebug  [ none (default) | error | warning | info | debug | verbose ]

        Sets debug level on ESP32. Does nothing on architectures that do not
        implement esp.osdebug().
        """
        if line is '':
            line = 'none'
        osdebug(line)
        oprint("set debug level to {}".format(
            self.devs.default_device().esp_osdebug(line).decode('utf-8')), end='')

    def do_debug(self, line):
        """debug [on|off]

        Turn debug output on/off.
        """
        print_.DEBUG = 'on' in line
        oprint("Debug is {}".format('on' if print_.DEBUG else 'off'))

    def do_quiet(self, line):
        """quiet [on|off]

        Turn on/off verbose output.
        """
        print_.QUIET = 'on' in line
        oprint("Quiet is {}".format('on' if print_.QUIET else 'off'))
