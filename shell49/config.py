#! /usr/bin/env python3

from print_ import cprint, qprint, eprint

from configparser import ConfigParser, NoSectionError, NoOptionError
import os

class Config(ConfigParser):

    DEFAULT = 'DEFAULT'

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
            self.add_section(section)
        self.modified = True
        super().set(section, option, value)

    def remove_section(self, section):
        self.modified = True
        super().remove_section(section)

    def remove_option(self, section, option):
        self.modified = True
        super().remove_option(section, option)

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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.modified:
            qprint("updating '{}'".format(self.config_file))
            self.save()


if __name__ == "__main__":
    with Config("~/.shell49_rc") as c:
        print(c)
        print(c[Config.DEFAULT]['buffer_size'])
        print(c.get(Config.DEFAULT, "buffer_size", fallback=123))
        print(c.get(Config.DEFAULT, "buffer_sizeX", fallback=123))
        print(c.getint(Config.DEFAULT, 'buffer_size'))
        print(c.getboolean(Config.DEFAULT, "ascii", fallback=True))
        c.set(Config.DEFAULT, 'ascii', False)
        c.set('pyboard', 'user', 'glXobi')
        c.set('pyboard2', 'name', 'abcd')
        print(c.get(Config.DEFAULT, "user"))
        print(c.get('pyboard', "user"))
