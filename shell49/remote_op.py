from . print_ import dprint, eprint, qprint, oprint
import shell49.print_ as print_

import os
import sys
import binascii
import fnmatch
import time
import tempfile

"""
Many of the functions defined in this file are sent to the remote upy
board for execution. Some of them can run either on the host or remote,
with small differences.

IS_UPY is used to determine if a funcion is running on the host (False)
or remote (True). It is set to True in function Device.remote().
"""
IS_UPY = False
HAS_BUFFER = True
BUFFER_SIZE = 2048
TIME_OFFSET = 0


def escape(str):
    """Precede all special characters with a backslash."""
    out = ''
    for char in str:
        if char in '\\ ':
            out += '\\'
        out += char
    return out


def unescape(str):
    """Undoes the effects of the escape() function."""
    out = ''
    prev_backslash = False
    for char in str:
        if not prev_backslash and char == '\\':
            prev_backslash = True
            continue
        out += char
        prev_backslash = False
    return out


def align_cell(fmt, elem, width):
    """Returns an aligned element."""
    if fmt == "<":
        return elem + ' ' * (width - len(elem))
    if fmt == ">":
        return ' ' * (width - len(elem)) + elem
    return elem


def column_print(fmt, rows, print_func):
    """Prints a formatted list, adjusting the width so everything fits.
    fmt contains a single character for each column. < indicates that the
    column should be left justified, > indicates that the column should
    be right justified. The last column may be a space which imples left
    justification and no padding.

    """
    # Figure out the max width of each column
    num_cols = len(fmt)
    width = [max(0 if isinstance(row, str) else len(row[i]) for row in rows)
             for i in range(num_cols)]
    for row in rows:
        if isinstance(row, str):
            # Print a seperator line
            print_func('  '.join([row * width[i] for i in range(num_cols)]))
        else:
            print_func('  '.join([align_cell(fmt[i], row[i], width[i])
                                  for i in range(num_cols)]))


def find_matching_files(match):
    """Finds all of the files wihch match (used for completion)."""
    last_slash = match.rfind('/')
    if last_slash == -1:
        dirname = '.'
        match_prefix = match
        result_prefix = ''
    else:
        dirname = match[0:last_slash]
        match_prefix = match[last_slash + 1:]
        result_prefix = dirname + '/'
    return [result_prefix + filename for filename in os.listdir(dirname) if filename.startswith(match_prefix)]


def is_pattern(s):
    """Return True if a string contains Unix wildcard pattern characters.
    """
    return not set('*?[{').intersection(set(s)) == set()


# Disallow patterns like path/t*/bar* because handling them on remote
# system is difficult without the glob library.
def parse_pattern(s):
    """Parse a string such as 'foo/bar/*.py'
    Assumes is_pattern(s) has been called and returned True
    1. directory to process
    2. pattern to match"""
    if '{' in s:
        return None, None  # Unsupported by fnmatch
    if s and s[0] == '~':
        s = os.path.expanduser(s)
    parts = s.split('/')
    absolute = len(parts) > 1 and not parts[0]
    if parts[-1] == '':  # # Outcome of trailing /
        parts = parts[:-1]  # discard
    if len(parts) == 0:
        directory = ''
        pattern = ''
    else:
        directory = '/'.join(parts[:-1])
        pattern = parts[-1]
    if not is_pattern(directory):  # Check for e.g. /abc/*/def
        if is_pattern(pattern):
            if not directory:
                directory = '/' if absolute else '.'
            return directory, pattern
    return None, None  # Invalid or nonexistent pattern


def validate_pattern(devs, cur_dir, fn):
    """On success return an absolute path and a pattern.
    Otherwise print a message and return None, None
    """
    directory, pattern = parse_pattern(fn)
    if directory is None:
        eprint("Invalid pattern {}.".format(fn))
        return None, None
    target = resolve_path(cur_dir, directory)
    mode = auto(devs, get_mode, target)
    if not mode_exists(mode):
        eprint("cannot access '{}': No such file or directory".format(fn))
        return None, None
    if not mode_isdir(mode):
        eprint("cannot access '{}': Not a directory".format(fn))
        return None, None
    return directory, pattern


def process_pattern(devs, cur_dir, fn):
    """Return a list of paths matching a pattern (or None on error).
    """
    directory, pattern = validate_pattern(devs, cur_dir, fn)
    if directory is not None:
        filenames = fnmatch.filter(auto(devs, listdir, directory), pattern)
        if filenames:
            return [directory + '/' + sfn for sfn in filenames]
        else:
            eprint("cannot access '{}': No such file or directory".format(fn))


def resolve_path_original(cur_dir, path):
    """Resolves path and converts it into an absolute path."""
    if path[0] == '~':
        # ~ or ~user
        path = os.path.expanduser(path)
    if path[0] != '/':
        # Relative path
        if cur_dir[-1] == '/':
            path = cur_dir + path
        else:
            path = cur_dir + '/' + path
    comps = path.split('/')
    new_comps = []
    for comp in comps:
        # We strip out xxx/./xxx and xxx//xxx, except that we want to keep the
        # leading / for absolute paths. This also removes the trailing slash
        # that autocompletion adds to a directory.
        if comp == '.' or (comp == '' and len(new_comps) > 0):
            continue
        if comp == '..':
            if len(new_comps) > 1:
                new_comps.pop()
        else:
            new_comps.append(comp)
    if len(new_comps) == 1 and new_comps[0] == '':
        return '/'
    res = '/'.join(new_comps)
    if len(res) == 0: res = '.'
    return res


def resolve_path(cur_dir, path):
    """Resolves path and converts it into an absolute path."""
    res = os.path.expanduser(path)
    if not os.path.isabs(path):
        res = os.path.join(cur_dir, res)
    res = os.path.normpath(res)
    if 'win32' in sys.platform and res.startswith('\\'):
        res = res.replace('\\', '/')
    # eprint("resolve_path:\ncur_dir {}\npath    {}\n-> res  {}\nvs      {}".format(cur_dir, path, res, resolve_path_original(cur_dir, path)))
    return res


def remote_repr(i):
    """Helper function to deal with types which we can't send to the pyboard."""
    repr_str = repr(i)
    if repr_str and repr_str[0] == '<':
        return 'None'
    return repr_str


def print_bytes(byte_str):
    """Prints a string or converts bytes to a string and then prints."""
    if isinstance(byte_str, str):
        oprint(byte_str)
    else:
        oprint(str(byte_str, encoding='utf8'))


def board_name(default):
    """Returns the boards name (if available)."""
    try:
        import config
        name = config.name
    except:
        try:
            import board
            name = board.name
        except:
            name = default
    return repr(name)


def upy_version():
    """Returns MicroPython version information."""
    import os
    version = '?'
    try:
        import iot49
        version = iot49.version()
    except:
        pass
    u = os.uname()
    return (u.release, u.machine, version)


def auto(devs, func, filename, *args, **kwargs):
    """If `filename` is a remote file, then this function calls func on the
       micropython board, otherwise it calls it locally.
    """
    dev, dev_filename = devs.get_dev_and_path(filename)
    if dev is None:
        # use large buffer on the host
        global BUFFER_SIZE
        BUFFER_SIZE = 4096
        try:
            dev_filename = os.path.expanduser(dev_filename)
        except IndexError:
            pass
        return func(dev_filename, *args, **kwargs)
    res = dev.remote_eval(func, dev_filename, *args, **kwargs)
    return res


def cat(devs, src_filename, dst_file):
    """Copies the contents of the indicated file to an already opened file."""
    (dev, dev_filename) = devs.get_dev_and_path(src_filename)
    if dev is None:
        with open(dev_filename, 'rb') as txtfile:
            for line in txtfile:
                dst_file.write(line)
    else:
        filesize = dev.remote_eval(get_filesize, dev_filename)
        return dev.remote(send_file_to_host, dev_filename, dst_file, filesize,
                          xfer_func=recv_file_from_remote)


def chdir(dirname):
    """Changes the current working directory."""
    import os
    os.chdir(dirname)


def copy_file(src_filename, dst_filename):
    """Copies a file from one place to another. Both the source and destination
       files must exist on the same machine.
    """
    try:
        with open(src_filename, 'rb') as src_file:
            with open(dst_filename, 'wb') as dst_file:
                while True:
                    buf = src_file.read(BUFFER_SIZE)
                    if len(buf) > 0:
                        dst_file.write(buf)
                    if len(buf) < BUFFER_SIZE:
                        break
        return True
    except Exception as e:
        return False


def cp(devs, src_filename, dst_filename):
    """Copies one file to another. The source file may be local or remote and
       the destnation file may be local or remote.
    """
    src_dev, src_dev_filename = devs.get_dev_and_path(src_filename)
    dst_dev, dst_dev_filename = devs.get_dev_and_path(dst_filename)

    if src_dev is dst_dev:
        # src and dst are either on the same remote, or both are on the host
        return auto(devs, copy_file, src_filename, dst_dev_filename)

    filesize = auto(devs, get_filesize, src_filename)

    if dst_dev is None:
        # Copying from remote to host
        with open(dst_dev_filename, 'wb') as dst_file:
            return src_dev.remote(send_file_to_host, src_dev_filename, dst_file,
                                  filesize, xfer_func=recv_file_from_remote)
    if src_dev is None:
        # Copying from host to remote
        with open(src_dev_filename, 'rb') as src_file:
            res = dst_dev.remote(recv_file_from_host, src_file, dst_dev_filename,
                                 filesize, xfer_func=send_file_to_remote)
            return res

    # Copying from remote A to remote B. We first copy the file
    # from remote A to the host and then from the host to remote B
    host_temp_file = tempfile.TemporaryFile()
    if src_dev.remote(send_file_to_host, src_dev_filename, host_temp_file,
                      filesize, xfer_func=recv_file_from_remote):
        host_temp_file.seek(0)
        return dst_dev.remote(recv_file_from_host, host_temp_file, dst_dev_filename,
                              filesize, xfer_func=send_file_to_remote)
    return False


def eval_str(string):
    """Executes a string containing python code."""
    output = eval(string)
    return output


def get_filesize(filename):
    """Returns the size of a file, in bytes."""
    import os
    try:
        # Since this function runs remotely, it can't depend on other functions,
        # so we can't call stat_mode.
        return os.stat(filename)[6]
    except OSError:
        return -1


def get_mode(filename):
    """Returns the mode of a file, which can be used to determine if a file
       exists, if a file is a file or a directory.
    """
    import os
    try:
        # Since this function runs remotely, it can't depend on other functions,
        # so we can't call stat_mode.
        return os.stat(filename)[0]
    except OSError:
        return 0


def get_stat(filename):
    """Returns the stat array for a given file. Returns all 0's if the file
       doesn't exist.
    """
    import os

    def stat(filename):
        rstat = os.stat(filename)
        if IS_UPY:
            # Micropython dates are relative to Jan 1, 2000. On the host, time
            # is relative to Jan 1, 1970.
            return rstat[:7] + tuple(tim + TIME_OFFSET for tim in rstat[7:])
        return rstat
    try:
        return stat(filename)
    except OSError:
        return (0,) * 10


def listdir(dirname):
    """Returns a list of filenames contained in the named directory."""
    import os
    return os.listdir(dirname)


def listdir_matches(match):
    """Returns a list of filenames contained in the named directory.
       Only filenames which start with `match` will be returned.
       Directories will have a trailing slash.
    """
    import os
    last_slash = match.rfind('/')
    if last_slash == -1:
        dirname = '.'
        match_prefix = match
        result_prefix = ''
    else:
        match_prefix = match[last_slash + 1:]
        if last_slash == 0:
            dirname = '/'
            result_prefix = '/'
        else:
            dirname = match[0:last_slash]
            result_prefix = dirname + '/'

    def add_suffix_if_dir(filename):
        if (os.stat(filename)[0] & 0x4000) != 0:
            return filename + '/'
        return filename
    matches = [add_suffix_if_dir(result_prefix + filename)
               for filename in os.listdir(dirname) if filename.startswith(match_prefix)]
    return matches


def listdir_stat(dirname):
    """Returns a list of tuples for each file contained in the named
       directory, or None if the directory does not exist. Each tuple
       contains the filename, followed by the tuple returned by
       calling os.stat on the filename.
    """
    import os

    def stat(filename):
        rstat = os.stat(filename)
        if IS_UPY:
            # Micropython dates are relative to Jan 1, 2000. On the host, time
            # is relative to Jan 1, 1970.
            return rstat[:7] + tuple(tim + TIME_OFFSET for tim in rstat[7:])
        return tuple(rstat)  # PGH formerly returned an os.stat_result instance

    try:
        files = os.listdir(dirname)
    except OSError:
        return None

    if dirname == '/':
        return list((file, stat('/' + file)) for file in files)

    return list((file, stat(dirname + '/' + file)) for file in files)


def make_directory(dirname):
    """Creates one or more directories."""
    import os
    try:
        os.mkdir(dirname)
    except:
        return False
    return True


def mkdir(devs, filename):
    """Creates a directory."""
    return auto(devs, make_directory, filename)


def remove_file(filename, recursive=False, force=False):
    """Removes a file or directory."""
    import os
    try:
        mode = os.stat(filename)[0]
        if mode & 0x4000 != 0:
            # directory
            if recursive:
                for file in os.listdir(filename):
                    success = remove_file(
                        filename + '/' + file, recursive, force)
                    if not success and not force:
                        return False
                os.rmdir(filename)  # PGH Work like Unix: require recursive
            else:
                if not force:
                    return False
        else:
            os.remove(filename)
    except:
        if not force:
            return False
    return True


def rm(devs, filename, recursive=False, force=False):
    """Removes a file or directory tree."""
    return auto(devs, remove_file, filename, recursive, force)


def make_dir(devs, dst_dir, dry_run, recursed):
    """Creates a directory. Produces information in case of dry run.
    Isues error where necessary.
    """
    parent = os.path.split(dst_dir.rstrip(
        '/'))[0]  # Check for nonexistent parent
    parent_files = auto(devs, listdir_stat,
                        parent) if parent else True  # Relative dir
    if dry_run:
        if recursed:  # Assume success: parent not actually created yet
            qprint("Creating directory {}".format(dst_dir))
        elif parent_files is None:
            qprint("Unable to create {}".format(dst_dir))
        return True
    if not mkdir(devs, dst_dir):
        eprint("Unable to create {}".format(dst_dir))
        return False
    return True


def file_dir(devs, directory):
    """Dict name->stat of files in directory,
       filted by rsync_includes, rsync_excludes
    """
    dev, filename = devs.get_dev_and_path(directory)
    inc = devs.config.get(0, 'rsync_includes',
                          default='*.py,*.json,*.txt,*.html').split(',')
    exc = devs.config.get(0, 'rsync_excludes', default='.*,__*__').split(',')
    files = auto(devs, listdir_stat, directory)
    if not files:
        files = []
    d = {}
    for name, stat in files:
        y = any(map((lambda x: fnmatch.fnmatch(name, x)), inc)) or is_dir(stat)
        n = any(map((lambda x: fnmatch.fnmatch(name, x)), exc))
        if y and not n:
            d[name] = stat
        else:
            dprint("squashing {} y={} n={}".format(name, y, n))
    return d


def rsync(devs, src_dir, dst_dir, mirror, dry_run, recursed):
    """Synchronizes 2 directory trees."""

    # This test is a hack to avoid errors when accessing /flash. When the
    # cache synchronisation issue is solved it should be removed
    if not isinstance(src_dir, str) or not len(src_dir):
        return

    # check that source is a directory
    sstat = auto(devs, get_stat, src_dir)
    if not is_dir(sstat):
        eprint("*** Source {} is not a directory".format(src_dir))
        return

    # create destination directory if it does not exist
    sstat = auto(devs, get_stat, dst_dir)
    if not file_exists(sstat):
        qprint("Create {} on remote".format(dst_dir))
        if not dry_run:
            if recursed and not make_dir(devs, dst_dir, dry_run, recursed):
                eprint("*** Unable to create directory", dst_dir)
    elif not is_dir(sstat):
        eprint("*** Destination {} is not a directory".format(src_dir))
        return

    # get list of src & dst files and stats
    qprint("   analyzing {}".format(dst_dir))
    d_src = file_dir(devs, src_dir)
    d_dst = file_dir(devs, dst_dir)

    # determine what needs to be copied or deleted
    set_dst = set(d_dst.keys())
    set_src = set(d_src.keys())
    to_add = set_src - set_dst  # Files to copy to dest
    to_del = set_dst - set_src  # To delete from dest
    to_upd = set_dst.intersection(set_src)  # In both: may need updating

    if False:
        eprint("rsync {} -> {}".format(src_dir, dst_dir))
        eprint("  sources", set_src)
        eprint("  dest   ", set_dst)
        eprint("  add    ", to_add)
        eprint("  delete ", to_del)
        eprint("  update ", to_upd)

    # add ...
    for f in to_add:
        src = os.path.join(src_dir, f)
        dst = os.path.join(dst_dir, f)
        qprint("Adding {}".format(dst))
        if is_dir(d_src[f]):
            if recursed:
                rsync(devs, src, dst, mirror, dry_run, recursed)
        else:
            if not dry_run:
                if not cp(devs, src, dst):
                    eprint("*** Unable to add {} --> {}".format(src, dst))

    # delete ...
    for f in to_del:
        if not mirror:
            break
        dst = os.path.join(dst_dir, f)
        qprint("Removing {}".format(dst))
        if not dry_run:
            res = rm(devs, dst, recursive=True, force=True)
            if not res:
                eprint("Cannot remove {}", dst)

    # update ...
    for f in to_upd:
        src = os.path.join(src_dir, f)
        dst = os.path.join(dst_dir, f)
        if is_dir(d_src[f]):
            if is_dir(d_dst[f]):
                # src and dst are directories
                if recursed:
                    rsync(devs, src, dst, mirror, dry_run, recursed)
            else:
                msg = "Source '{}' is a directory and destination " \
                      "'{}' is a file. Ignoring"
                eprint(msg.format(src, dst))
        else:
            if is_dir(d_dst[f]):
                msg = "Source '{}' is a file and destination " \
                      "'{}' is a directory. Ignoring"
                eprint(msg.format(src, dst))
            else:
                if False:
                    eprint("BEB src {} > dst {} delta={}".format(
                        stat_mtime(d_src[f]), stat_mtime(d_dst[f]),
                        stat_mtime(d_src[f]) - stat_mtime(d_dst[f])))
                if stat_size(d_src[f]) != stat_size(d_dst[f]) or \
                   stat_mtime(d_src[f]) > stat_mtime(d_dst[f]):
                    msg = "Copying {} (newer than {})"
                    qprint(msg.format(src, dst))
                    if not dry_run:
                        if not cp(devs, src, dst):
                            eprint(
                                "*** Unable to update {} --> {}".format(src, dst))
                else:
                    dprint(f, "NO update src time:", stat_mtime(d_src[f]), "dst time", stat_mtime(
                        d_dst[f]), "delta", stat_mtime(d_src[f]) - stat_mtime(d_dst[f]))


def set_time(y, m, d, h, min, s):
    """Set time on upy board."""
    rtc = None
    try:
        import pyb
        rtc = pyb.RTC()
        rtc.datetime((y, m, d, None, h, min, s))
        return rtc.datetime()
    except:
        try:
            import machine
            rtc = machine.RTC()
            if not rtc.synced():
                try:
                    rtc.datetime((y, m, d, None, h, min, s))
                    return rtc.datetime()
                except:
                    rtc.init((y, m, d, h, min, s))
                    return rtc.now()
        except:
            return None


def epoch():
    import time
    return time.time()


def osdebug(level):
    try:
        import esp
        l = esp.LOG_ERROR
        if level:
            if level is 'error':
                l = esp.LOG_ERROR
            elif level is 'warning':
                l = esp.LOG_WARNING
            elif level is 'info':
                l = esp.LOG_INFO
            elif level is 'debug':
                l = esp.LOG_DEBUG
            elif level is 'verbose':
                l = esp.LOG_VERBOSE
            else:
                level = 'none'
        esp.osdebug('', l)
        return level
    except:
        return "*** Cannot set osdebug level"


def get_time():
    try:
        import time
        return time.strftime('%c', time.localtime())
    except:
        return None


def get_ip_address():
    try:
        from network import WLAN, STA_IF
        return WLAN(STA_IF).ifconfig()[0]
    except:
        return None


def get_mac_address():
    try:
        from binascii import hexlify
        from network import WLAN, STA_IF
        mac = hexlify(WLAN(STA_IF).config('mac'), ':').decode('ascii')
    except:
        mac = None
    return repr(mac)

def get_unique_id(default):
    """Returns the boards name (if available)."""
    try:
        from machine import unique_id
        from binascii import hexlify
        uid = hexlify(unique_id()).decode('ascii')
    except:
        uid = default
    return repr(uid)

# 0x0D's sent from the host get transformed into 0x0A's, and 0x0A sent to the
# host get converted into 0x0D0A when using sys.stdin. sys.tsin.buffer does
# no transformations, so if that's available, we use it, otherwise we need
# to use hexlify in order to get unaltered data.


def recv_file_from_host(src_file, dst_filename, filesize, dst_mode='wb'):
    """Function which runs on the pyboard. Matches up with send_file_to_remote."""
    import sys
    import ubinascii
    if HAS_BUFFER:
        try:
            import pyb
            usb = pyb.USB_VCP()
        except:
            try:
                import machine
                usb = machine.USB_VCP()
            except:
                usb = None
        if usb and usb.isconnected():
            # We don't want 0x03 bytes in the data to be interpreted as a Control-C
            # This gets reset each time the REPL runs a line, so we don't need to
            # worry about resetting it ourselves
            usb.setinterrupt(-1)
    try:
        with open(dst_filename, dst_mode) as dst_file:
            bytes_remaining = filesize
            if not HAS_BUFFER:
                bytes_remaining *= 2  # hexlify makes each byte into 2
            buf_size = BUFFER_SIZE
            write_buf = bytearray(buf_size)
            read_buf = bytearray(buf_size)
            while bytes_remaining > 0:
                read_size = min(bytes_remaining, buf_size)
                buf_remaining = read_size
                buf_index = 0
                while buf_remaining > 0:
                    if HAS_BUFFER:
                        bytes_read = sys.stdin.buffer.readinto(
                            read_buf, bytes_remaining)
                    else:
                        bytes_read = sys.stdin.readinto(
                            read_buf, bytes_remaining)
                    if bytes_read > 0:
                        write_buf[buf_index:bytes_read] = read_buf[0:bytes_read]
                        buf_index += bytes_read
                        buf_remaining -= bytes_read
                if HAS_BUFFER:
                    dst_file.write(write_buf[0:read_size])
                else:
                    dst_file.write(ubinascii.unhexlify(write_buf[0:read_size]))
                # Send back an ack as a form of flow control
                sys.stdout.write('\x06')
                bytes_remaining -= read_size
        return True
    except:
        return False


def send_file_to_remote(dev, src_file, dst_filename, filesize, dst_mode='wb'):
    """Intended to be passed to the `remote` function as the xfer_func argument.
       Matches up with recv_file_from_host.
    """
    bytes_remaining = filesize
    while bytes_remaining > 0:
        if dev.has_buffer:
            buf_size = BUFFER_SIZE
        else:
            buf_size = BUFFER_SIZE // 2
        read_size = min(bytes_remaining, buf_size)
        buf = src_file.read(read_size)
        #sys.stdout.write('\r%d/%d' % (filesize - bytes_remaining, filesize))
        # sys.stdout.flush()
        if dev.has_buffer:
            dev.write(buf)
        else:
            dev.write(binascii.hexlify(buf))
        # Wait for ack so we don't get too far ahead of the remote
        while True:
            char = dev.read(1)
            if char == b'\x06':
                break
            # This should only happen if an error occurs
            sys.stdout.write(chr(ord(char)))
        bytes_remaining -= read_size
    # sys.stdout.write('\r')


def recv_file_from_remote(dev, src_filename, dst_file, filesize):
    """Intended to be passed to the `remote` function as the xfer_func argument.
       Matches up with send_file_to_host.
    """
    bytes_remaining = filesize
    if not dev.has_buffer:
        bytes_remaining *= 2  # hexlify makes each byte into 2
    buf_size = BUFFER_SIZE
    write_buf = bytearray(buf_size)
    while bytes_remaining > 0:
        read_size = min(bytes_remaining, buf_size)
        buf_remaining = read_size
        buf_index = 0
        while buf_remaining > 0:
            read_buf = dev.read(buf_remaining)
            bytes_read = len(read_buf)
            if bytes_read:
                write_buf[buf_index:bytes_read] = read_buf[0:bytes_read]
                buf_index += bytes_read
                buf_remaining -= bytes_read
        if dev.has_buffer:
            dst_file.write(write_buf[0:read_size])
        else:
            dst_file.write(binascii.unhexlify(write_buf[0:read_size]))
        # Send an ack to the remote as a form of flow control
        dev.write(b'\x06')   # ASCII ACK is 0x06
        bytes_remaining -= read_size


def send_file_to_host(src_filename, dst_file, filesize):
    """Function which runs on the pyboard. Matches up with recv_file_from_remote."""
    import sys
    import ubinascii
    try:
        with open(src_filename, 'rb') as src_file:
            bytes_remaining = filesize
            if HAS_BUFFER:
                buf_size = BUFFER_SIZE
            else:
                buf_size = BUFFER_SIZE // 2
            while bytes_remaining > 0:
                read_size = min(bytes_remaining, buf_size)
                buf = src_file.read(read_size)
                if HAS_BUFFER:
                    sys.stdout.buffer.write(buf)
                else:
                    sys.stdout.write(ubinascii.hexlify(buf))
                bytes_remaining -= read_size
                # Wait for an ack so we don't get ahead of the remote
                while True:
                    char = sys.stdin.read(1)
                    if char:
                        if char == '\x06':
                            break
                        # This should only happen if an error occurs
                        sys.stdout.write(char)
        return True
    except:
        return False


def test_buffer():
    """Checks the micropython firmware to see if sys.stdin.buffer exists."""
    import sys
    try:
        return sys.stdin.buffer != None
    except:
        return False


def test_readinto():
    """Checks the micropython firmware to see if sys.stdin.readinto exists."""
    import sys
    try:
        return sys.stdin.readinto != None
    except:
        return False


def test_unhexlify():
    """Checks the micropython firmware to see if ubinascii.unhexlify exists."""
    import ubinascii
    try:
        return ubinascii.unhexlify != None
    except:
        return False


def is_dir(stat):
    return stat[0] & 0x4000 != 0


def is_file(stat):
    return stat[0] & 0x8000 != 0


def file_exists(stat):
    return stat[0] & 0xc000 != 0


def mode_exists(mode):
    return mode & 0xc000 != 0


def mode_isdir(mode):
    return mode & 0x4000 != 0


def mode_isfile(mode):
    return mode & 0x8000 != 0


def stat_mode(stat):
    """Returns the mode field from the results returne by os.stat()."""
    return stat[0]


def stat_size(stat):
    """Returns the filesize field from the results returne by os.stat()."""
    return stat[6]


def stat_mtime(stat):
    """Returns the mtime field from the results returne by os.stat()."""
    return stat[8]


def word_len(word):
    """Returns the word lenght, minus any color codes."""
    if word[0] == '\x1b':
        return len(word) - 11   # 7 for color, 4 for no-color
    return len(word)


def print_cols(words, print_func, termwidth=79):
    """Takes a single column of words, and prints it as multiple columns that
    will fit in termwidth columns.
    """
    width = max([word_len(word) for word in words])
    nwords = len(words)
    ncols = max(1, (termwidth + 1) // (width + 1))
    nrows = (nwords + ncols - 1) // ncols
    for row in range(nrows):
        for i in range(row, nwords, nrows):
            word = words[i]
            if word[0] == '\x1b':
                print_func('%-*s' % (width + 11, words[i]),
                           end='\n' if i + nrows >= nwords else ' ')
            else:
                print_func('%-*s' % (width, words[i]),
                           end='\n' if i + nrows >= nwords else ' ')


def decorated_filename(filename, stat):
    """Takes a filename and the stat info and returns the decorated filename.
       The decoration takes the form of a single character which follows
       the filename. Currently, the only decodation is '/' for directories.
    """
    mode = stat[0]
    if mode_isdir(mode):
        return print_.DIR_COLOR + filename + print_.END_COLOR + '/'
    if filename.endswith('.py'):
        return print_.PY_COLOR + filename + print_.END_COLOR
    return filename


def is_hidden(filename):
    """Determines if the file should be considered to be a "hidden" file."""
    return filename[0] == '.' or filename[-1] == '~'


def is_visible(filename):
    """Just a helper to hide the double negative."""
    return not is_hidden(filename)


MONTH = ('', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')


SIX_MONTHS = 183 * 24 * 60 * 60


def print_long(filename, stat, print_func):
    """Prints detailed information about the file passed in."""
    size = stat_size(stat)
    mtime = stat_mtime(stat)
    file_mtime = time.gmtime(mtime)
    curr_time = time.time()
    if mtime > curr_time or mtime < (curr_time - SIX_MONTHS):
        print_func('%6d %s %2d %04d  %s' % (size, MONTH[file_mtime[1]],
                                            file_mtime[2], file_mtime[0],
                                            decorated_filename(filename, stat)))
    else:
        print_func('%6d %s %2d %02d:%02d %s' % (size, MONTH[file_mtime[1]],
                                                file_mtime[2], file_mtime[3], file_mtime[4],
                                                decorated_filename(filename, stat)))


def trim(docstring):
    """Trims the leading spaces from docstring comments.

    From http://www.python.org/dev/peps/pep-0257/

    """
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)
