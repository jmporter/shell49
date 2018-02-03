from fileops import resolve_path, get_mode, mode_isdir, auto, chdir
from printing import eprint


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

    mode = auto(self.boards, get_mode, dirname)
    if mode_isdir(mode):
        self.prev_dir = self.cur_dir
        self.cur_dir = dirname
        auto(self.boards, chdir, dirname)
    else:
        eprint("Directory '%s' does not exist" % dirname)
