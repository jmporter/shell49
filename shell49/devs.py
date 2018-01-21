from . device import DeviceSerial, DeviceNet
from . print_ import qprint


class DevsError(Exception):
    """Errors that we want to report to the user and keep running."""
    pass


class Devs:
    """List of connected devices."""

    def __init__(self, config):
        self._devices = []
        self._default_dev = None
        self.config = config

    def default_device(self, index=None, name=None):
        """Set/get default device id"""
        if index:
            try:
                devs = list(self.devices())
                self._default_dev = devs[index - 1]
            except Exception as e:
                pass
        if name:
            self._default_dev = self.find_device_by_name(name)
        if not self._default_dev:
            raise DevsError("no board connected")
        return self._default_dev

    def devices(self):
        """Iterate over all devices"""
        # remove devices that are disconnected
        self._devices = list(filter(lambda dev: dev.connected(), self._devices))
        for dev in self._devices:
            if dev:
                yield dev

    def find_device_by_name(self, name):
        """Find board by name."""
        for d in self.devices():
            if d.name() == name:
                return d
        return self._default_dev

    def is_connected(self, name):
        """Return True if board with specified name is already connected."""
        for d in self._devices:
            if d.name() == name:
                return True
        return False

    def find_serial_device_by_port(self, port):
        """Find board by port name."""
        for dev in self.devices():
            if dev.is_serial_port(port):
                return dev
        return None

    def find_telnet_device_by_ip(self, ip):
        """Find board by ip address."""
        for dev in self.devices():
            if dev.is_telnet_ip(ip):
                return dev
        return None

    def num_devices(self):
        """Number of connected devices"""
        return sum(x is not None for x in self.devices())

    def connect_serial(self, port, baudrate=None):
        """Connect to MicroPython board plugged into the specfied port."""
        if not port:
            return
        if not baudrate:
            baudrate = self.config.get('default', 'baudrate', 115200)
        qprint("Connecting via serial to {} @ {} baud ...".format(port, baudrate))
        dev = DeviceSerial(self.config, port, baudrate)
        self.add_device(dev)

    def connect_telnet(self, ip_address):
        """Connect to MicroPython board at specified IP address."""
        qprint("Connecting via telnet to '{}' ...".format(ip_address))
        dev = DeviceNet(self.config, ip_address)
        self.add_device(dev)

    def add_device(self, dev):
        """Adds a device to the list of devices we know about and make it the new default."""
        if dev.connected():
            self._devices.append(dev)
            self._default_dev = dev

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
        if self._default_dev and self._default_dev.is_root_path(filename):
            return (self._default_dev, filename)
        test_filename = filename + '/'
        for dev in self.devices():
            if dev.name() and test_filename.startswith('/' + dev.name()):
                dev_filename = filename[len(dev.name()) + 1:]
                if dev_filename == '':
                    dev_filename = '/'
                return (dev, dev_filename)
        return (None, filename)
