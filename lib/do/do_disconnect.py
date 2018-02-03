def do_disconnect(self, line):
    """Disconnect current default board, then run boards command."""
    self.boards.default.disconnect()
    self.do_boards(line)
