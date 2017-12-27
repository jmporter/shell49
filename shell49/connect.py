from print_ import qprint
from device import DeviceError, DeviceSerial
from const import USE_AUTOCONNECT
import globals_


import socket
import threading

def add_device(dev):
    """Adds a device to the list of devices we know about."""
    with globals_.DEV_LOCK:
        for idx in range(len(globals_.DEVS)):
            test_dev = DEVS[idx]
            if test_dev.dev_name_short == dev.dev_name_short:
                # This device is already in our list. Delete the old one
                if test_dev is globals_DEFAULT_DEV:
                    globals_.DEFAULT_DEV = None
                del globals_.DEVS[idx]
                break
        if find_device_by_name(dev.name):
            # This name is taken - make it unique
            dev.name += '-%d' % globals_.DEV_IDX
        dev.name_path = '/' + dev.name + '/'
        globals_.DEVS.append(dev)
        globals_.DEV_IDX += 1
        if globals_.DEFAULT_DEV is None:
            globals_.DEFAULT_DEV = dev


def find_device_by_name(name):
    """Tries to find a board by board name."""
    if not name:
        return globals_.DEFAULT_DEV
    with globals_.DEV_LOCK:
        for dev in globals_.DEVS:
            if dev.name == name:
                return dev
    return None


def find_serial_device_by_port(port):
    """Tries to find a board by port name."""
    with globals_.DEV_LOCK:
        for dev in globals_.DEVS:
            if dev.is_serial_port(port):
                return dev
    return None


def num_devices():
    with globals_.DEV_LOCK:
        return len(globals_.DEVS)

def is_micropython_usb_device(port):
    """Checks a USB device to see if it looks like a MicroPython device.
    """
    if type(port).__name__ == 'Device':
        # Assume its a pyudev.device.Device
        if ('ID_BUS' not in port or port['ID_BUS'] != 'usb' or
            'SUBSYSTEM' not in port or port['SUBSYSTEM'] != 'tty'):
            return False
        usb_id = 'usb vid:pid={}:{}'.format(port['ID_VENDOR_ID'], port['ID_MODEL_ID'])
    else:
        # Assume its a port from serial.tools.list_ports.comports()
        usb_id = port[2].lower()
    # We don't check the last digit of the PID since there are 3 possible
    # values.
    if usb_id.startswith('usb vid:pid=f055:980'):
        return True
    # Check for Teensy VID:PID
    if usb_id.startswith('usb vid:pid=16c0:0483'):
        return True
    return False


def connect(port, baud=115200, user='micro', password='python', wait=0):
    """Tries to connect automagically vie network or serial."""
    try:
        ip_address = socket.gethostbyname(port)
        #print('Connecting to ip', ip_address)
        connect_telnet(port, ip_address, user=user, password=password)
    except socket.gaierror:
        # Doesn't look like a hostname or IP-address, assume its a serial port
        #print('connecting to serial', port)
        connect_serial(port, baud=baud, wait=wait)


def connect_telnet(name, ip_address=None, user='micro', password='python'):
    """Connect to a MicroPython board via telnet."""
    if ip_address is None:
        try:
            ip_address = socket.gethostbyname(name)
        except socket.gaierror:
            ip_address = name
    if name == ip_address:
        qprint('Connecting to (%s) ...' % ip_address)
    else:
        qprint('Connecting to %s (%s) ...' % (name, ip_address))
    dev = DeviceNet(name, ip_address, user, password)
    add_device(dev)


def connect_serial(port, baud=115200, wait=0):
    """Connect to a MicroPython board via a serial port."""
    qprint('Connecting to %s ...' % port)
    try:
        dev = DeviceSerial(port, baud, wait)
    except DeviceError as err:
        sys.stderr.write(str(err))
        sys.stderr.write('\n')
        return False
    add_device(dev)
    return True


def autoconnect():
    """Sets up a thread to detect when USB devices are plugged and unplugged.
       If the device looks like a MicroPython board, then it will automatically
       connect to it.
    """
    if not USE_AUTOCONNECT:
        return
    try:
        import pyudev
    except ImportError:
        return
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    connect_thread = threading.Thread(target=autoconnect_thread, args=(monitor,), name='AutoConnect')
    connect_thread.daemon = True
    connect_thread.start()


def autoconnect_thread(monitor):
    """Thread which detects USB Serial devices connecting and disconnecting."""
    monitor.start()
    monitor.filter_by('tty')

    epoll = select.epoll()
    epoll.register(monitor.fileno(), select.POLLIN)

    while True:
        try:
            events = epoll.poll()
        except InterruptedError:
            continue
        for fileno, _ in events:
            if fileno == monitor.fileno():
                usb_dev = monitor.poll()
                print('autoconnect: {} action: {}'.format(usb_dev.device_node, usb_dev.action))
                dev = find_serial_device_by_port(usb_dev.device_node)
                if usb_dev.action == 'add':
                    # Try connecting a few times. Sometimes the serial port
                    # reports itself as busy, which causes the connection to fail.
                    for i in range(8):
                        if dev:
                            connected = connect_serial(dev.port, dev.baud, dev.wait)
                        elif is_micropython_usb_device(usb_dev):
                            connected = connect_serial(usb_dev.device_node)
                        else:
                            connected = False
                        if connected:
                            break
                        time.sleep(0.25)
                elif usb_dev.action == 'remove':
                    print('')
                    print("USB Serial device '%s' disconnected" % usb_dev.device_node)
                    if dev:
                        dev.close()
                        break


def autoscan():
    """autoscan will check all of the serial ports to see if they have
       a matching VID:PID for a MicroPython board. If it matches.
    """
    for port in serial.tools.list_ports.comports():
        if is_micropython_usb_device(port):
            connect_serial(port[0])
