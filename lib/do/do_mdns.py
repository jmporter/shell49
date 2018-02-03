from mdns_client import MdnsListener


def do_mdns(self, line):
    """mdns

    List all MicroPython boards advertising repl telnet via mdns.
    """
    listener = MdnsListener()
    boards = listener.listen(seconds=1)
    if len(boards) == 0:
        print("No board out there waving it's flag ...")
        return
    print("url                  ip               port   spec")
    for b in boards:
        print("{:20s} {:14s}    {:2d}    {}".format(
            b.url, b.ip, b.port, b.spec))
