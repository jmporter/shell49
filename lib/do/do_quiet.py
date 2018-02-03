from printing import quiet


def do_quiet(self, line):
    """quiet [on|off]

    Turn on/off verbose output.
    """
    quiet('on' in line)
    print("Quiet is {}".format('on' if quiet() else 'off'))
