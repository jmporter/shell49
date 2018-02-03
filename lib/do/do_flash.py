from util import add_arg
from board import BoardError
from flasher import Flasher, FlasherError
from printing import dprint, eprint

argparse_flash = (
    add_arg(
        '-l', '--list',
        dest='list',
        action='store_true',
        help='list firmware versions (no flashing)',
        default=False
    ),
    add_arg(
        '-e', '--erase',
        dest='erase',
        action='store_true',
        help='erase flash memory (including file system) before flashing firmware',
        default=False
    ),
    add_arg(
        '-v', '--version',
        dest='version',
        help='firmware version',
        default='STABLE'
    ),
    add_arg(
        '-b', '--board',
        dest='board',
        help='microcontroller board (e.g. HUZZAH32)',
        default=None
    ),
)

def do_flash(self, line):
    """flash [-l|--list] [-e|--erase] [-v|--version VERSION] [-b|--board BOARD]

    Flash firmware to microcontroller.
    """

    args = self.line_to_args(line)
    firmware_url = "https://people.eecs.berkeley.edu/~boser/iot49/firmware"
    flash_options = "--chip esp32 " \
        "--before default_reset --after hard_reset " \
        "write_flash -z --flash_mode dio --flash_freq 40m --flash_size detect"
    id = 0
    try:
        id = self.boards.default.id
    except BoardError:
        pass
    firmware_url = self.config.get(id, "firmware_url", firmware_url)
    flash_options = self.config.get(id, "flash_options", flash_options)
    port = self.config.get(id, "port", "/dev/cu.SLAB_USBtoUART")
    baudrate = self.config.get(id, "flash_baudrate", 921600)
    board = self.config.get(id, "board", "HUZZAH32")
    if args.board:
        board = args.board

    dprint("firmware url: ", firmware_url)
    dprint("flash options:", flash_options)
    dprint("port:         ", port)
    dprint("baudrate:     ", baudrate)
    dprint("board:        ", board)

    try:
        f = Flasher(board=board, url=firmware_url)
        if args.list:
            print("available firmware versions:")
            print('\n'.join(["  {:8s} {}".format(v, d) for v, d in f.versions()]))
            return
        dev = self.boards.find_board(port)
        if dev: dev.disconnect()
        if args.erase:
            f.erase_flash(port)
        f.flash(args.version, flash_options=flash_options,
                port=port, baudrate=baudrate)
    except FlasherError as e:
        eprint(e)
