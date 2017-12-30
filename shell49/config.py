#! /usr/bin/env python3

from print_ import cprint, qprint, eprint

from configparser import ConfigParser, NoSectionError, NoOptionError
import os, uuid

class Config(ConfigParser):

    def __init__(self, config_file):
        super().__init__()
        self.config_file = os.path.expanduser(config_file)
        self.modified = False
        if os.path.isfile(self.config_file):
            qprint("Loading configuration '{}'".format(self.config_file))
            self.read(self.config_file)
        else:
            qprint("WARNING: configuration '{}' does not exist, creating default".format(self.config_file))
            self.create_default()
            self.save()

    def set(self, section, option, value):
        value = str(value)
        try:
            if self.get(section, option) == value:
                return
        except NoOptionError:
            pass
        except NoSectionError:
            eprint("BEB: config.set, section='{}'".format(section))
            self.add_section(section)
        self.modified = True
        super().set(section, option, value)

    def remove_section(self, section):
        self.modified = True
        super().remove_section(section)

    def remove_option(self, section, option):
        self.modified = True
        super().remove_option(section, option)

    def is_default_option(self, option, value):
        """Return true if option is defined in DEFAULT section with the specified value."""
        try:
            return self['DEFAULT'][option] == str(value)
        except KeyError:
            return False

    def save(self):
        with open(self.config_file, 'w') as cf:
            self.write(cf)

    def create_default(self):
        self['DEFAULT'] = {
            'baudrate': 115200,
            'buffer_size': 512,
            'binary_transfer': True,
            'time_offset': 946684800,
            'user': 'micro',
            'password': 'python',
            'host_dir': '~/iot49',
            'remote_dir': '/flash',
            'rsync_includes': '*.py,*.json,*.txt,*.html',
            'rsync_excludes': '.*,__*__'
        }

    def add_board(self, name=None):
        id = "board-{}".format(uuid.uuid4().hex[:6].upper())
        self.add_section(id)
        # assign a default name
        if not name:
            name = id
        self.set(id, 'name', name)
        return id

    def find_board_by_name(self, name, create=False):
        """Return board ID or DEFAULT if no board with specified name exists."""
        for s in self.sections():
            if self.get(s, 'name', fallback=None) == name:
                return s
        if create:
            return self.add_board(name)
        return 'DEFAULT'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.modified:
            qprint("updating '{}'".format(self.config_file))
            self.save()


if __name__ == "__main__":
    with Config("~/.shell49_rc.test") as c:
        # c.create_default()
        print(c['DEFAULT']['buffer_size'])
        print(c.get('DEFAULT', "buffer_size", fallback=123))
        print(c.get('DEFAULT', "buffer_sizeX", fallback=123))
        print(c.getint('DEFAULT', 'buffer_size'))
        print(c.getboolean('DEFAULT', "ascii", fallback=True))
        c.set('DEFAULT', 'ascii', False)
        c.set('pyboard', 'user', 'glXobi')
        c.set('pyboard2', 'name', 'abcd')
        print(c.get('DEFAULT', "user"))
        print(c.get('pyboard', "user"))
        b = c.add_board()
        print("add_board", c.add_board())
        c.set(b, 'name', 'bf')
        print("board abc", c.find_board_by_name('abc'))
        print("board bf", c.find_board_by_name('bf'))
