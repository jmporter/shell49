import glob
import sys
import serial

def do_ports(self, line):
    """do_ports

    List available USB ports."""
    available = serial_ports()
    connected = [ d.address for d in self.boards.boards() ]
    all = sorted(set(available + connected))
    for p in all:
        print("{} {}".format("*" if p in connected else " ", p))


def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    else:
        ports = glob.glob('/dev/*')
        ports = [ p for p in ports if 'usb' in p.lower() ]

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result
