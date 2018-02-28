from board import BoardError
from config import ConfigError
from util import add_arg
from fileops import cp
from printing import cprint, oprint, eprint
import printing

from ast import literal_eval
from tempfile import NamedTemporaryFile
from datetime import datetime
import os

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

def print_config(config, id, *, exc={}, color=printing.OUTPUT_COLOR):
    for k in sorted(config.options(id)):
        if not k in exc:
            v = config.get(id, k)
            cprint("{:>20s} = {}".format(k, v), color=color)

def do_config(self, line):
    """config    Print option values.
       config [-u] [-d] [--default] OPTION [VALUE]
                 Set/delete OPTION to VALUE.
    """
    default_board = None
    board_id = 'default'
    try:
        default_board = self.boards.default
        board_id = default_board.id
    except BoardError:
        pass

    if line == '':
        # print configuration
        print_config(self.config, board_id, color=printing.MPY_COLOR)
        if default_board:
            oprint("Defaults:")
            keys = self.config.options(board_id)
            print_config(self.config, 'default', exc=keys)
        return

    # parse arguments
    args = self.line_to_args(line)
    if args.default:
        board_id = 'default'
        default_board = None
    value = ' '.join(args.value)
    try:
        # try to convert value to Python object (e.g. for numbers)
        value = literal_eval(value)
    except:
        pass
    if not args.default and not default_board:
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
        if not default_board:
            eprint("*** No board connected, cannot upload configuration")
            return
        with NamedTemporaryFile() as temp:
            temp.close()
            f = open(temp.name, 'w')
            now = datetime.now().strftime("%Y-%b-%d %H:%M:%S")
            print("# config.py, created on {}".format(now), file=f)
            for key in default_board.config_options():
                print("{} = {}".format(key, repr(default_board.get_config(key))), file=f)
            print("mac_table = {}".format(repr(self.config.mac_table())), file=f)
            f.close()
            dst = os.path.join(default_board.get_config('remote_dir', '/flash'), 'config.py')
            cp(self.boards, temp.name, dst)
            os.unlink(temp.name)
