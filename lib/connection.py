from printing import qprint, dprint

from serial import Serial
from serial.serialutil import SerialException
import time
import os

"""Serial or Telnet connection to a MicroPython REPL."""

class ConnectionError(Exception):
    """Errors relating to board connections"""
    def __init__(self, msg):
        super().__init__(msg)


class Connection:

    def __init__(self):
        pass

    def close(self):
        """Close connection and free up resources"""
        pass

    def read(self, bytes=1):
        """Read bytes from device"""
        raise NotImplementedError("read: connection is abstract")

    def write(self, bytes):
        """Write bytes from device"""
        raise NotImplementedError("write: connection is abstract")

    def read_until(self, min_num_bytes, ending, timeout=10, data_consumer=None):
        """Read from board until 'ending'. Timeout None disables timeout."""
        dprint("read_until({}, {})".format(min_num_bytes, ending))
        data = self.read(min_num_bytes)
        if data_consumer:
            data_consumer(data)
        timeout_count = 0
        while True:
            if data.endswith(ending):
                dprint("   data = '{}'".format(data))
                break
            elif self.in_waiting > 0:
                new_data = self.read(1)
                data = data + new_data
                if data_consumer:
                    data_consumer(new_data)
                timeout_count = 0
            else:
                timeout_count += 1
                if timeout and timeout_count >= 100 * timeout:
                    raise ConnectionError('timeout in read_until "{}"'.format(ending))
                time.sleep(0.01)
        return data

    @property
    def connected(self):
        """Connection is active"""
        raise NotImplementedError("connected: connection is abstract")

    @property
    def in_waiting(self):
        """Number of bytes in queue waiting to be read without blocking"""
        raise NotImplementedError("in_waiting: connection is abstract")

    @property
    def timeout(self):
        raise NotImplementedError("timeout: connection is abstract")

    @timeout.setter
    def timeout(self, val):
        raise NotImplementedError("timeout: connection is abstract")

    @property
    def address(self):
        """Serial port or telnet ip"""
        raise NotImplementedError("address: connection is abstract")

    def match(self, spec):
        """Checks if board connection matches spec (port, ip, or url)"""
        return False

    @property
    def is_telnet(self):
        """Board is connected via telnet"""
        return False


class SerialConnection(Connection):

    def __init__(self, port, baudrate):
        try:
            # wait for port to come online
            for wait in range(3):
                if os.path.exists(port): break
                qprint("Waiting for port '{}' to come online".format(port))
                time.sleep(1)
            # try to connect
            for attempt in range(5):
                try:
                    self._serial = Serial(port, baudrate, inter_byte_timeout=1)
                    break
                except IOError:
                    qprint("Waiting for serial connection at '{}'".format(port))
                time.sleep(1)
            # send Control-C to put MicroPython in known state
            for attempt in range(20):
                try:
                    self._serial.write(b'\x03')
                    break
                except SerialException:
                    time.sleep(0.5)
                    qprint("Trying to talk to the MicroPython interpreter")
            self._port = port
        except AttributeError:
            raise ConnectionError("Failed connecting to board at '{}'".format(port))
        except KeyboardInterrupt:
            self._serial = None

    def close(self):
        """Close connection and free up resources"""
        self._port = None
        if self._serial:
            self._serial.close()
            self._serial = None

    def read(self, bytes=1):
        """Read bytes from device"""
        try:
            return self._serial.read(bytes)
        except (SerialException, AttributeError):
            self.close()
            raise ConnectionError("Board disconnected, cannot read")

    def write(self, bytes):
        """Write bytes to device"""
        try:
            self._serial.write(bytes)
        except (SerialException, AttributeError):
            self.close()
            raise ConnectionError("Board disconnected, cannot write")

    @property
    def connected(self):
        """Connection is active"""
        return self._serial != None

    @property
    def in_waiting(self):
        """Number of bytes in queue waiting to be read without blocking"""
        if not self._serial: return 0
        return self._serial.in_waiting

    @property
    def timeout(self):
        return self._serial.timeout

    @timeout.setter
    def timeout(self, val):
        self._serial.timeout = val

    @property
    def address(self):
        """Serial port or telnet ip"""
        return self._port

    def match(self, port):
        """Checks if board is connected on port"""
        return self._port == port


class TelnetConnection(Connection):

    def __init__(self, ip, user, password, read_timeout=5):
        dprint("TelnetConnection({}, user={}, password={})".format(ip, user, password))
        import telnetlib
        try:
            self._telnet = telnetlib.Telnet(ip, timeout=15)
        except ConnectionRefusedError:
            raise ConnectionError("Board refused telnet connection")
        self._ip = ip
        self._read_timeout = read_timeout
        if b'Login as:' in self._telnet.read_until(b'Login as:', timeout=read_timeout):
            self._telnet.write(bytes(user, 'ascii') + b"\r\n")
            dprint("sent user", user)
            if b'Password:' in self._telnet.read_until(b'Password:', timeout=read_timeout):
                # needed because of internal implementation details of the telnet server
                time.sleep(0.2)
                self._telnet.write(bytes(password, 'ascii') + b"\r\n")
                dprint("sent password", password)
                if b'for more information.' in self._telnet.read_until(b'Type "help()" for more information.', timeout=read_timeout):
                    dprint("got greeting")
                    # login succesful
                    from collections import deque
                    self._fifo = deque()
                    return
        raise ConnectionError('Failed to establish a telnet connection with the board')

    def __del__(self):
        self.close()

    def close(self):
        """Close connection and free up resources"""
        self._ip = None
        if self._telnet:
            try:
                self._telnet.close()
            except:
                # telnet object may not exist yet, ignore
                pass
            self._telnet = None

    def read(self, size=1):
        """Read bytes from device"""
        while len(self._fifo) < size:
            timeout_count = 0
            try:
                data = self._telnet.read_eager()
            except (OSError, EOFError) as e:
                raise ConnectionError(e)
            if len(data):
                self._fifo.extend(data)
                timeout_count = 0
            else:
                time.sleep(0.25)
                if self._read_timeout is not None and timeout_count > 4 * self._read_timeout:
                    break
                timeout_count += 1
        data = b''
        while len(data) < size and len(self._fifo) > 0:
            data += bytes([self._fifo.popleft()])
        return data

    def write(self, data):
        """Write bytes to device"""
        try:
            self._telnet.write(data)
            return len(data)
        except (BrokenPipeError, OSError, EOFError) as e:
            raise ConnectionError(e)

    @property
    def connected(self):
        """Connection is active"""
        return self._telnet != None

    @property
    def in_waiting(self):
        """Number of bytes in queue waiting to be read without blocking"""
        if not self._telnet: return 0
        n_waiting = len(self._fifo)
        if not n_waiting:
            try:
                data = self._telnet.read_eager()
            except EOFError as e:
                raise ConnectionError(e)
            self._fifo.extend(data)
            return len(data)
        else:
            return n_waiting

    @property
    def timeout(self):
        return self._read_timeout

    @timeout.setter
    def timeout(self, val):
        self._read_timeout = val

    @property
    def address(self):
        """Serial port or telnet ip"""
        return self._ip

    def match(self, ip):
        """Checks if board is connected on ip"""
        return self._ip == ip

    @property
    def is_telnet(self):
        """Board is connected via telnet"""
        return True
