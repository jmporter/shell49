def do_ip(self, line):
    """mac

    Inquire and print out IP address of micropython board.
    """
    print(self.boards.default.remote(get_ip_address).decode('utf-8'), end='')


def get_ip_address():
    try:
        from network import WLAN, STA_IF
        return WLAN(STA_IF).ifconfig()[0]
    except:
        return None
