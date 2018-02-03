from board import BoardError
from printing import oprint
from util import column_print

def do_boards(self, line):
    """boards          List connected devices.
    boards #        Make board number # the default board.
    boards NAME     Make board NAME the default board.
    """
    try:
        self.boards.default = int(line)
    except ValueError:
        self.boards.default = line
    rows = []
    rows.append(("#", "Name", "Port/IP", "Unique ID", "Directories"))
    try:
        default_board = self.boards.default
    except BoardError:
        default_board = None
    for index, board in enumerate(self.boards.boards()):
        dirs = []
        if board is default_board:
            dirs += [dir[:-1] for dir in board.root_dirs]
        dirs += ['/{}{}'.format(board.name, dir)[:-1] for dir in board.root_dirs]
        dirs = ', '.join(dirs)
        default = '*' if board is default_board else ''
        rows.append((default + str(index + 1), board.name,
                     board.address, board.id, dirs))
    if len(rows) > 1:
        column_print('><<< ', rows, oprint)
    else:
        print('No boards connected')
