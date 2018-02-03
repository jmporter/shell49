from util import add_arg
from fileops import auto, resolve_path, is_pattern, process_pattern, get_mode, \
    mkdir, cp, rsync, listdir_stat, mode_exists, mode_isdir, stat_mode
from printing import eprint

import os

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


def complete_cp(self, text, line, begidx, endidx):
    return self.filename_complete(text, line, begidx, endidx)

def do_cp(self, line):
    """cp SOURCE DEST               Copy a single SOURCE file to DEST file.
    cp SOURCE... DIRECTORY          Copy multiple SOURCE files to a directory.
    cp [-r] PATTERN DIRECTORY       Copy matching files to DIRECTORY.
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
    dst_mode = auto(self.boards, get_mode, dst_dirname)
    d_dst = {}  # Destination directory: lookup stat by basename
    if args.recursive:
        dst_files = auto(self.boards, listdir_stat, dst_dirname)
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
        src_filenames = process_pattern(self.boards, self.cur_dir, sfn)
        if src_filenames is None:
            return

    for src_filename in src_filenames:
        if is_pattern(src_filename):
            eprint("Only one pattern permitted.")
            return
        src_filename = resolve_path(self.cur_dir, src_filename)
        src_mode = auto(self.boards, get_mode, src_filename)
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
        if not cp(self.boards, src_filename, dst_filename):
            err = "Unable to copy '{}' to '{}'"
            eprint(err.format(src_filename, dst_filename))
            break
