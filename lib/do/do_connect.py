from mdns_client import MdnsListener
from printing import qprint, eprint

def do_connect(self, line):
    """    connect TYPE TYPE_PARAMS            Connect boards to shell49.
    connect serial [port [baud]]        Wired connection. Uses defaults from config file.
    connect telnet [url [user [pwd]]]   Wireless connection. If no url/ip address is
        specified, connects to all known boards advertising repl service via mDNS.
        Optional user (default: 'micro') and password (default: 'python').

    Note: do not connect to the same board via serial AND telnet connections.
          Doing so may block communication with the board.
    """
    args = self.line_to_args(line)
    if len(args) < 1:
        eprint('Missing connection TYPE')
        return
    connect_type = args[0]
    if connect_type == 'serial':
        port = args[1] if len(args) > 1 else self.config.get(
            0, 'port', '/dev/cu.SLAB_USBtoUART')
        baud = args[2] if len(args) > 2 else self.config.get(
            0, 'baudrate', '115200')
        try:
            baud = int(baud)
        except ValueError:
            eprint("Not a valid baudrate, '{}'".format(baud))
            return
        # Note: board may be connected over telnet, but we don't know ...
        #       in this case, connect blocks
        if self.boards.find_board(port):
            eprint("board already connected on '{}'".format(port))
            return
        self.boards.connect_serial(port, baud)
    elif connect_type == 'telnet':
        if len(args) > 1:
            user = args[2] if len(args) > 2 else 'micro'
            pwd  = args[3] if len(args) > 3 else 'python'
            self.boards.connect_telnet(args[1], user, pwd)
        else:
            listener = MdnsListener()
            adv = list(listener.listen(seconds=1))
            if len(adv) == 0:
                qprint("No boards detected via mDNS.")
            for b in adv:
                qprint("Heard from '{}' ({})".format(b.url, b.ip))
                # connect only to boards in the config database
                board_id = self.config.get_board_from_name(b.hostname)
                if not board_id:
                    qprint("  not in db, skip!")
                    continue
                # we are not already connected to
                if self.boards.connected(b.hostname):
                    qprint("  already connected")
                    continue
                # let's connect!
                user = self.config.get(board_id, 'user', 'micro')
                pwd  = self.config.get(board_id, 'password', 'python')
                self.boards.connect_telnet(b.url, user, pwd)
    else:
        eprint('Unrecognized connection TYPE: {}'.format(connect_type))
