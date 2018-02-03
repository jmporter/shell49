from printing import oprint
from version import __version__


def do_version(self, line):
    """version

    Print shell49 and MicroPython version information.
    """
    db = self.boards.default
    release, machine, version = db.remote_eval(upy_version)
    fmt = "{:>10s} = {}"
    oprint(fmt.format("board", db.name))
    oprint(fmt.format("firmware", version))
    oprint(fmt.format("release", release))
    oprint(fmt.format("machine", machine))
    oprint(fmt.format("shell49", __version__))


def upy_version():
    """Return MicroPython version information."""
    import os
    version = '?'
    try:
        import iot49
        version = iot49.version()
    except:
        pass
    u = os.uname()
    return (u.release, u.machine, version)
