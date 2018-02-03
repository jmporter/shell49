from util import add_arg
from fileops import resolve_path, rsync
from printing import eprint, qprint

import argparse


argparse_rsync = (
    add_arg(
        '-m', '--mirror',
        dest='mirror',
        action='store_true',
        help="rsync copies all files from SRC_DIR to DST_DIR and deletes files "
             "on DST_DIR that are not also on SRC_DIR. "
             "--mirror suppresses these file deletions.",
        default=False,
    ),
    add_arg(
        '-n', '--dry-run',
        dest='dry_run',
        action='store_true',
        help='Shows what would be done without actually performing any file copies.',
        default=False
    ),
    add_arg(
        'src_dst_dir',
        nargs=argparse.REMAINDER,
        metavar='SRC_DST_DIR',
        default='.',
        help='Source and destination directories'
    )
)

def complete_rsync(self, text, line, begidx, endidx):
    return self.filename_complete(text, line, begidx, endidx)

def do_rsync(self, line):
    """rsync [-m|--mirror] [-n|--dry-run] [SRC_DIR [DST_DIR]]

       Synchronize destination directory tree to source directory tree.
    """
    db = self.boards.default
    args = self.line_to_args(line)
    sd = args.src_dst_dir
    if len(sd) > 2:
        eprint("*** More than one destination directory given")
        return
    src_dir = sd[0] if len(sd) > 0 else db.get_config('host_dir', '~/iot49')
    dst_dir = sd[1] if len(sd) > 1 else db.get_config('remote_dir', '/flash')
    src_dir = resolve_path(self.cur_dir, src_dir)
    dst_dir = resolve_path(self.cur_dir, dst_dir)
    if len(sd) < 2:
        qprint("synchronizing {} --> {}".format(src_dir, dst_dir))
    rsync(self.boards, src_dir, dst_dir,
          mirror=not args.mirror, dry_run=args.dry_run, recursed=True)
