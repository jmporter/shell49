#! /usr/bin/env python3

from . print_ import cprint, qprint, eprint

from pprint import pprint
from datetime import datetime
from ast import literal_eval
import keyword
import os
import io

class ConfigError(Exception):
    """Errors relating to configuration file and manipulations"""
    def __init__(self, msg):
        super().__init__(msg)

class Config:
    """Manage shell49 configuration file and values"""

    def __init__(self, config_file):
        self._config_file = os.path.expanduser(config_file)
        self._modified = False
        self._config = {}
        self._load()

    def add_board(self, name=None):
        """Add board database record.
        Return board_id.
        """
        if self.find_board_by_name(name):
            dprint("Config.add_board: Board '{}' exists".format(name))
            return self.find_board_by_name(name)
        board = {}
        if name:
            board = { 'name': name }
            self._modified = True
        self._boards().append(board)
        return len(self._boards())-1

    def set(self, board_id, option, value):
        """Set board option parameter value. board_id = 0 is default entries."""
        if not option:
            return
        if not isinstance(option, str):
            raise ConfigError("{}: expected str, got {!r}".format(option, type(option)))
        if not option.isidentifier():
            raise ConfigError("{} is not a valid Python identifier".format(option))
        if keyword.iskeyword(option):
            raise ConfigError("{}: keywords are not permitted as option names".format(option))
        if option != 'name' and not 'name' in self.options(board_id):
            raise ConfigError("assign board name before setting option values (config name ...)")
        if option == 'name' and board_id == 0:
            raise ConfigError("illegal assignment of name to default board configuration")
        if option == 'name' and self.find_board_by_name(value) != 0:
            raise ConfigError("board with name '{}' exists already in database".format(value))
        self._modified = True
        self._boards()[board_id][option] = value

    def get(self, board_id, option, default=None):
        """Get board option parameter value."""
        boards = self._boards()
        return boards[board_id].get(option, boards[0].get(option, default))

    def remove(self, board_id, option=None):
        """Remove board option or entire record if option=None."""
        try:
            self._modified = True
            if option:
                del self._boards()[board_id][option]
            elif board_id != 0:
                self._boards()[board_id] = None
        except KeyError:
            pass

    def find_board_by_name(self, name, create=False):
        """Return id of board with specified name.

        If no board with the indicated name exists, a new one is created
        (create=True) or 0 (default) is returned.
        """
        for i, board in enumerate(self._boards()[1:]):
            if board.get('name') == name:
                return i+1
        return self.add_board(name) if create else 0

    def options(self, board_id):
        """Return list of option names for specified board."""
        try:
            return list(self._boards()[board_id].keys())
        except:
            return []

    def _boards(self):
        return self._config['boards']

    def _create_default(self):
        self._config = { 'boards': [
                {
                    'baudrate': 115200,
                    'buffer_size': 1024,
                    'binary_transfer': True,
                    'time_offset': 0,  # 946684800,
                    'user': 'micro',
                    'password': 'python',
                    'host_dir': '~/iot49',
                    'remote_dir': '/flash',
                    'rsync_includes': '*.py,*.json,*.txt,*.html',
                    'rsync_excludes': '.*,__*__,config.py',
                    'port': '/dev/cu.SLAB_USBtoUART'
                }
            ]}

    def _load(self):
        qprint("Loading configuration '{}'".format(self._config_file))
        try:
            with open(self._config_file) as f:
                self._config = literal_eval(f.read())
        except:
            qprint("WARNING: cannot load '{}', creating default".format(self._config_file))
            self._create_default()
            self._modified = True

    def save(self):
        """Save configuration to config_file."""
        # purge boards without name
        self._config['boards'] = [b for i, b in enumerate(self._boards()) if i is 0 or (b and b.get('name', None))]
        for b in self._boards():
            if not b.get('name', None):
                b = None
        with open(self._config_file, 'w') as f:
            print("# User configuration for micropython shell49", file=f)
            print("# Machine generated on {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), file=f)
            print("# Use the config command in shell49 to modify", file=f)
            print(file=f)
            pprint(self._config, stream=f)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._modified:
            qprint("updating '{}'".format(self._config_file))
            self.save()


if __name__ == "__main__":
    with Config("~/.shell49_rc.py") as c:
        print("default user", c.get(0, 'user'))
        b = c.find_board_by_name("woa!")
        print(c.set(b, 'user', 'xyz'))
        print("get child user, xyz", c.get(b, 'user'))
        print("get default user, still micro", c.get(0, 'user'))
        c.remove(b, 'user')
        print("removed child user, micro", c.get(b, 'user'))
        print("default user, still micro", c.get(0, 'user'))
        c.set(b, "wifi", True)
        c.set(b, "tries", 432)
        c.set(b, "tries", 661234567)
        c.set(b, "user", "top secret!")
