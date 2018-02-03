from fileops import resolve_path, auto, get_mode, mode_exists, mode_isfile, cat
from printing import eprint


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
        mode = auto(self.boards, get_mode, filename)
        if not mode_exists(mode):
            eprint("Cannot access '%s': No such file" % filename)
            continue
        if not mode_isfile(mode):
            eprint("'%s': is not a file" % filename)
            continue
        cat(self.boards, filename, self.stdout)
