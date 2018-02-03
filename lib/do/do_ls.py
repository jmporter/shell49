from util import add_arg
from fileops import auto, is_pattern, resolve_path, validate_pattern, listdir_stat, \
    get_stat, stat_mode, stat_mtime, stat_size, mode_exists, mode_isdir
from printing import eprint, oprint
import printing

from fnmatch import fnmatch
import shutil
import time


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
            stat = auto(self.boards, get_stat, filename)
            mode = stat_mode(stat)
            if not mode_exists(mode):
                err = "Cannot access '{}': No such file or directory"
                eprint(err.format(filename))
                continue
            if not mode_isdir(mode):
                if args.long:
                    print_long(filename, stat, oprint)
                else:
                    oprint(filename)
                continue
            if len(args.filenames) > 1:
                if idx > 0:
                    oprint('')
                oprint("%s:" % filename)
            pattern = '*'
        else:  # A pattern was specified
            filename, pattern = validate_pattern(
                self.boards, self.cur_dir, fn)
            if filename is None:  # An error was printed
                continue
        files = []
        ldir_stat = auto(self.boards, listdir_stat, filename)
        if ldir_stat is None:
            err = "Cannot access '{}': No such file or directory"
            eprint(err.format(filename))
        else:
            for filename, stat in sorted(ldir_stat,
                                         key=lambda entry: entry[0]):
                if is_visible(filename) or args.all:
                    if fnmatch(filename, pattern):
                        if args.long:
                            print_long(filename, stat, oprint)
                        else:
                            files.append(decorated_filename(filename, stat))
        if len(files) > 0:
            print_cols(sorted(files), oprint, shutil.get_terminal_size().columns)


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
        return printing.DIR_COLOR + filename + printing.END_COLOR + '/'
    if filename.endswith('.py'):
        return printing.MPY_COLOR + filename + printing.END_COLOR
    return filename



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


def word_len(word):
    """Returns the word lenght, minus any color codes."""
    if word[0] == '\x1b':
        return len(word) - 11   # 7 for color, 4 for no-color
    return len(word)


def is_hidden(filename):
    """Determines if the file should be considered to be a "hidden" file."""
    return filename[0] == '.' or filename[-1] == '~'


def is_visible(filename):
    """Just a helper to hide the double negative."""
    return not is_hidden(filename)
