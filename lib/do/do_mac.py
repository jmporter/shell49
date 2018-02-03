def do_mac(self, line):
    """mac

    Inquire and print out MAC address of micropython board.
    """
    print(self.boards.default.remote(get_mac_address).decode('utf-8'), end='')


def get_mac_address():
    try:
        from binascii import hexlify
        from network import WLAN, STA_IF
        mac = hexlify(WLAN(STA_IF).config('mac'), ':').decode('ascii')
    except:
        mac = None
    return repr(mac)
