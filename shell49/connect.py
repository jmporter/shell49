from print_ import qprint
from device import DeviceError, DeviceSerial

USE_AUTOCONNECT = True

import socket


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
