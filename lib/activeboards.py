from board import Board, BoardError
from printing import qprint

class ActiveBoards:
    """List of connected boards."""

    def __init__(self, config):
        self._boards = []
        self._default_board = None
        self.config = config

    def _check_status(self):
        """Check connection status of all boards"""
        self._boards = [ b for b in self._boards if b.connected ]
        # list(filter(lambda b: b.connected(), self._boards))
        if len(self._boards) == 0 or not self._default_board or not self._default_board.connected:
            self._default_board = None
            return

    @property
    def default(self):
        """Return default board. BoardError if none."""
        self._check_status()
        if not self._default_board:
            raise BoardError("No default board")
        return self._default_board

    @default.setter
    def default(self, board):
        """Set default board by name or index"""
        self._check_status()
        new_default = None
        if isinstance(board, str):
            new_default = self.find_board(board)
        else:
            try:
                new_default = self._boards[board-1]
            except:
                pass
        if new_default:
            self._default_board = new_default
        return self._default_board

    def boards(self):
        """Iterate over all active boards"""
        self._check_status()
        for b in self._boards:
            if b: yield b

    def find_board(self, board):
        """Find board by id, name, port, ip, or url."""
        for b in self.boards():
            if b.match(board): return b
        return None

    def connected(self, name):
        """Return True if board with specified name/id/port/ip/url is already connected."""
        return self.find_board(name) != None

    def num_boards(self):
        """Number of connected boards"""
        return len(list(self.boards()))

    def connect_serial(self, port, baudrate=None):
        """Connect to MicroPython board plugged into the specfied port."""
        if not baudrate:
            baudrate = self.config.get('default', 'baudrate', 115200)
        qprint("Connecting via serial to {} @ {} baud ...".format(port, baudrate))
        b = Board(self.config)
        b.connect_serial(port, baudrate)
        self._boards.append(b)
        if not self._default_board: self._default_board = b

    def connect_telnet(self, ip_address, user='micro', pwd='python'):
        """Connect to MicroPython board at specified IP address."""
        qprint("Connecting via telnet to '{}' ...".format(ip_address))
        b = Board(self.config)
        b.connect_telnet(ip_address, user, pwd)
        self._boards.append(b)
        if not self._default_board: self._default_board = b

    def get_dev_and_path(self, filename):
        """Check if filename is located on one of the connected boards.
        Convention: path starting with '/board_name/' or is in default.root_directories()
        are considered to be remote, all others local.

        Returns tuple (board, board_filename) or (None, filename).
        """
        self._check_status()
        if self._default_board and self._default_board.is_root_path(filename):
            return (self._default_board, filename)
        if not filename.startswith('/'):
            return (None, filename)
        test_filename = filename + '/'
        for b in self.boards():
            if test_filename.startswith('/' + b.name):
                board_filename = filename[len(b.name) + 1:]
                if board_filename == '':
                    board_filename = '/'
                return (b, board_filename)
        return (None, filename)
