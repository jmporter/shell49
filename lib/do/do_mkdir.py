from fileops import resolve_path, mkdir
from printing import eprint


def complete_mkdir(self, text, line, begidx, endidx):
    return self.filename_complete(text, line, begidx, endidx)

def do_mkdir(self, line):
    """mkdir DIRECTORY...

       Creates one or more directories.
    """
    args = self.line_to_args(line)
    for filename in args:
        filename = resolve_path(self.cur_dir, filename)
        if not mkdir(self.boards, filename):
            eprint('Unable to create %s' % filename)
