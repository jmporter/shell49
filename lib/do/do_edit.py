from fileops import resolve_path, auto, mode_exists, mode_isdir, get_mode, get_stat, cp
from printing import eprint

import tempfile
import os

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
    dev, dev_filename = self.boards.get_dev_and_path(filename)
    mode = auto(self.boards, get_mode, filename)
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
                print('Updating {} ...'.format(filename))
                cp(local_filename, filename)
