from device import DeviceSerial, DeviceNet, DeviceError
from config import Config
from print_ import oprint, qprint, eprint, dprint

from collections import OrderedDict
import threading


class DevsError(Exception):
    """Errors that we want to report to the user and keep running."""
    pass


class Devs:
    """List of known devices."""

    def __init__(self, config):
        self.devs = []
        self.config = config
        self.default = None
        self.lock = threading.RLock()


    def default_device(self):
        if not self.default:
            raise DevsError("no board connected")
        return self.default


    def get(option, fallback=None):
        section = self.default.name if self.default else Config.DEFAULT
        return self.config.get(section, option, fallback=default)


    def getboolean(option, fallback=False):
        section = self.default.name if self.default else Config.DEFAULT
        return self.config.getboolean(section, option, fallback=default)


    def getint(option, fallback=0):
        section = self.default.name if self.default else Config.DEFAULT
        return self.config.getint(section, option, fallback=default)


    def find_device_by_name(self, name):
        """Tries to find a board by name."""
        with self.lock:
            for d in self.devs:
                if d.name == name: return d
            return self.default_device()


    def find_serial_device_by_port(self, port):
        """Tries to find a board by port name."""
        with self.lock:
            for dev in self.devs:
                if dev.is_serial_port(port):
                    return dev
        return None


    def num_devices(self):
        with self.lock:
            n = 0
            for d in self.devs:
                if d: n += 1
            return n


    def connect_serial(self, port, board_name=Config.DEFAULT):
        """Connect to MicroPython board plugged into the specfied port."""
        qprint("Connecting to '%s' ..." % port)
        baudrate = self.config.getint(board_name, 'baudrate', fallback=115200)
        wait = self.config.getint(board_name, 'wait', fallback=0)
        dev = DeviceSerial(self.config, Config.DEFAULT, port)
        self.add_device(dev)


    def connect_telnet(self, ip_address, board_name=Config.DEFAULT):
        """Connect to MicroPython board at specified IP address."""
        qprint("Connecting to '%s' ..." % ip_address)
        dev = DeviceNet(self.config, board_name, ip_address)
        self.add_device(dev)


    def add_device(self, dev):
        """Adds a device to the list of devices we know about."""
        with self.lock:
            self.devs.append(dev)
            if not self.default:  self.default = dev


    def get_dev_and_path(self, filename):
        """Determines if a given file is located locally or remotely. We assume
           that any directories from the pyboard take precendence over local
           directories of the same name. /dev_name/path where dev_name is the name of a
           given device is also considered to be associaed with the named device.

           If the file is associated with a remote device, then this function
           returns a tuple (dev, dev_filename) where dev is the device and
           dev_filename is the portion of the filename relative to the device.

           If the file is not associated with the remote device, then the dev
           portion of the returned tuple will be None.
        """
        if self.default and self.default.is_root_path(filename):
            return (self.default, filename)
        test_filename = filename + '/'
        with self.lock:
            for dev in self.devs:
                if test_filename.startswith(dev.name):
                    dev_filename = filename[len(dev.name)-1:]
                    if dev_filename == '':
                        dev_filename = '/'
                    return (dev, dev_filename)
        return (None, filename)
