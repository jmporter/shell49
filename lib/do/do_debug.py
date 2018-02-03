from printing import debug

def do_debug(self, line):
    """debug [on|off]

    Turn debug output on/off.
    """
    debug('on' in line)
    print("Debug is {}".format('on' if debug() else 'off'))
