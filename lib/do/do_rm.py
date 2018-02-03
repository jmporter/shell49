from util import add_arg
from fileops import is_pattern, process_pattern, resolve_path, rm
from printing import eprint

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
    """rm [-f|--force] FILE...             Remove one or more files
    rm [-f|--force] PATTERN                Remove multiple files
    rm -r [-f|--force] [FILE|DIRECTORY]... Files and/or directories
    rm -r [-f|--force] PATTERN             Multiple files and/or directories

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
        filenames = process_pattern(self.boards, self.cur_dir, sfn)
        if filenames is None:
            return

    for filename in filenames:
        filename = resolve_path(self.cur_dir, filename)
        if not rm(self.boards, filename, recursive=args.recursive, force=args.force):
            if not args.force:
                eprint("Unable to remove '{}' (try -rf if you are sure)".format(filename))
            break
