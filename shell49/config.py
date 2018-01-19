#! /usr/bin/env python3

from . print_ import qprint, eprint, dprint, oprint

from pprint import pprint
from datetime import datetime
from ast import literal_eval
import keyword
import sys
import os


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

    def set(self, board_id, option, value):
        """Set board option parameter value. board_id = 0 is default entries."""
        dprint("config.set id={} {}={}".format(board_id, option, value))
        if board_id == 0:
            board_id = 'default'
        if not option:
            return
        if not isinstance(option, str):
            raise ConfigError(
                "{}: expected str, got {!r}".format(option, type(option)))
        if not option.isidentifier():
            raise ConfigError(
                "{} is not a valid Python identifier".format(option))
        if keyword.iskeyword(option):
            raise ConfigError(
                "{}: keywords are not permitted as option names".format(option))
        self._modified = True
        boards = self._boards()
        if not board_id in boards:
            boards[board_id] = {}
        boards[board_id][option] = value

    def get(self, board_id, option, default=None):
        """Get board option parameter value."""
        if board_id == 0:
            board_id = 'default'
        boards = self._boards()
        try:
            return boards[board_id].get(option, boards['default'].get(option, default))
        except KeyError:
            return default

    def remove(self, board_id, option):
        """Remove board option or entire record if option=None."""
        if board_id == 0:
            board_id = 'default'
        dprint("config.remove id={} option={}".format(board_id, option))
        try:
            self._modified = True
            del self._boards()[board_id][option]
        except KeyError:
            pass

    def has_board_with_name(self, name):
        """Check if board_id is known."""
        for b in self._boards().values():
            if b.get('name', None) == name:
                return True
        return False

    def options(self, board_id='default'):
        """Return list of option names for specified board."""
        try:
            keys = list(self._boards()[board_id].keys())
            keys.extend(['user', 'password'])
            return set(keys)
        except:
            return []

    def _boards(self):
        return self._config['boards']

    def _create_default(self):
        self._config = {'boards': {
            'default': {
                'board': 'HUZZAH32',
                'baudrate': 115200,
                'buffer_size': 1024,
                'binary_transfer': True,
                'time_offset': 946684800,
                'user': 'micro',
                'password': 'python',
                'host_dir': '.',
                'remote_dir': '/flash',
                'rsync_includes': '*.py,*.json,*.txt,*.html',
                'rsync_excludes': '.*,__*__,config.py',
                'flash_options': "--chip esp32 --before default_reset --after hard_reset write_flash -z --flash_mode dio --flash_freq 40m --flash_size detect ",
                'firmware_url': "https://people.eecs.berkeley.edu/~boser/iot49/firmware",
                'flash_baudrate': 921600}
        }}

    def _load(self):
        qprint("Loading configuration '{}'".format(self._config_file))
        try:
            with open(self._config_file) as f:
                self._config = literal_eval(f.read())
        except FileNotFoundError:
            oprint("WARNING: configuration '{}' does not exist, creating default".format(self._config_file))
            self._create_default()
            self._modified = True
        except SyntaxError as e:
            eprint("Syntax error in {}: {}".format(self._config_file, e))
            sys.exit()

    def save(self):
        """Save configuration to config_file."""
        with open(self._config_file, 'w') as f:
            print("# User configuration for micropython shell49", file=f)
            print("# Machine generated on {}".format(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")), file=f)
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
