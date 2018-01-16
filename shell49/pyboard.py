#!/usr/bin/env python3

"""
pyboard interface

This module provides the Pyboard class, used to communicate with and
control the pyboard over a serial USB or telent connection.
"""

from . print_ import oprint

import sys
import time

try:
    stdout = sys.stdout.buffer
except AttributeError:
    # Python2 doesn't have buffer attr
    stdout = sys.stdout


def stdout_write_bytes(b):
    b = b.replace(b"\x04", b"")
    stdout.write(b)
    stdout.flush()


class PyboardError(BaseException):
    pass


class TelnetToSerial:
    def __init__(self, ip, user, password, read_timeout=5):
        import telnetlib
        self.ip = ip
        self.tn = telnetlib.Telnet(ip, timeout=15)
        self.read_timeout = read_timeout
        if b'Login as:' in self.tn.read_until(b'Login as:', timeout=read_timeout):
            self.tn.write(bytes(user, 'ascii') + b"\r\n")

            if b'Password:' in self.tn.read_until(b'Password:', timeout=read_timeout):
                # needed because of internal implementation details of the telnet server
                time.sleep(0.2)
                self.tn.write(bytes(password, 'ascii') + b"\r\n")

                if b'for more information.' in self.tn.read_until(b'Type "help()" for more information.', timeout=read_timeout):
                    # login succesful
                    from collections import deque
                    self.fifo = deque()
                    return

        raise PyboardError(
            'Failed to establish a telnet connection with the board')

    def __del__(self):
        self.close()

    def close(self):
        try:
            self.tn.close()
        except:
            # the telnet object might not exist yet, so ignore this one
            pass

    def read(self, size=1):
        while len(self.fifo) < size:
            timeout_count = 0
            data = self.tn.read_eager()
            if len(data):
                self.fifo.extend(data)
                timeout_count = 0
            else:
                time.sleep(0.25)
                if self.read_timeout is not None and timeout_count > 4 * self.read_timeout:
                    break
                timeout_count += 1

        data = b''
        while len(data) < size and len(self.fifo) > 0:
            data += bytes([self.fifo.popleft()])
        return data

    def write(self, data):
        try:
            self.tn.write(data)
            return len(data)
        except BrokenPipeError as e:
            raise PyboardError("Broken pipe to '{}'".format(self.ip))

    def inWaiting(self):
        n_waiting = len(self.fifo)
        if not n_waiting:
            data = self.tn.read_eager()
            self.fifo.extend(data)
            return len(data)
        else:
            return n_waiting


class Pyboard:

    def __init__(self, port=None, baudrate=0, wait=10, ip=None, user='micro', password='python'):
        """Connect to MicroPython board via serial or telnet (if IP specified)."""
        self.port = port
        self.baudrate = baudrate
        self.wait = wait
        self.ip = ip
        self.user = user
        self.password = password
        self.connect()

    def address(self):
        return self.ip if self.ip else self.port

    def ip(self):
        return self.ip

    def port(self):
        return self.port

    def connect(self):
        if self.ip:
            self.serial = TelnetToSerial(
                self.ip, self.user, self.password, read_timeout=10)
        else:
            import serial
            delayed = False
            wait = self.wait
            for attempt in range(wait + 1):
                try:
                    if serial.VERSION == '3.0':
                        self.serial = serial.Serial(
                            self.port, baudrate=self.baudrate, inter_byte_timeout=1)
                    else:
                        self.serial = serial.Serial(
                            self.port, baudrate=self.baudrate, interCharTimeout=1)
                    break
                except (OSError, IOError):  # Py2 and Py3 have different errors
                    if wait == 0:
                        continue
                    if attempt == 0:
                        sys.stdout.write(
                            'Waiting {} seconds for pyboard '.format(wait))
                        delayed = True
                time.sleep(1)
                sys.stdout.write('.')
                sys.stdout.flush()
            else:
                if delayed:
                    print('')
                raise PyboardError('failed to access {}'.format(self.port))
            if delayed:
                print('')

    def close(self):
        self.serial.close()

    def read_until(self, min_num_bytes, ending, timeout=10, data_consumer=None):
        # dprint("pyb.read_until min={}, ending='{}'".format(min_num_bytes, ending))
        data = self.serial.read(min_num_bytes)
        if data_consumer:
            data_consumer(data)
        timeout_count = 0
        while True:
            if data.endswith(ending):
                break
            elif self.serial.inWaiting() > 0:
                new_data = self.serial.read(1)
                data = data + new_data
                if data_consumer:
                    data_consumer(new_data)
                timeout_count = 0
            else:
                timeout_count += 1
                if timeout is not None and timeout_count >= 100 * timeout:
                    break
                time.sleep(0.01)
        return data

    def enter_raw_repl(self):
        # dprint("enter_raw_repl ...")
        # ctrl-C twice: interrupt any running program
        self.serial.write(b'\r\x03\x03')

        # flush input (without relying on serial.flushInput())
        n = self.serial.inWaiting()
        while n > 0:
            self.serial.read(n)
            n = self.serial.inWaiting()

        self.serial.write(b'\r\x01')  # ctrl-A: enter raw REPL
        expect = b'raw REPL; CTRL-B to exit\r\n>'
        data = self.read_until(1, expect)
        if not data.endswith(expect):
            raise PyboardError('could not enter raw repl: expected {}, got {}'.format(expect, data))

        self.serial.write(b'\x04')  # ctrl-D: soft reset
        expect = b'soft reboot\r\n'
        data = self.read_until(1, expect)
        if not data.endswith(expect):
            raise PyboardError('could not enter raw repl: expected {}, got {}'.format(expect, data))
        # By splitting this into 2 reads, it allows boot.py to print stuff,
        # which will show up after the soft reboot and before the raw REPL.
        expect = b'raw REPL; CTRL-B to exit\r\n'
        data = self.read_until(1, expect)
        if not data.endswith(expect):
            raise PyboardError('could not enter raw repl: expected {}, got {}'.format(expect, data))

    def exit_raw_repl(self):
        # dprint("exit_raw_repl")
        self.serial.write(b'\r\x02')  # ctrl-B: enter friendly REPL

    def follow(self, timeout, data_consumer=None):
        # wait for normal output
        data = self.read_until(1, b'\x04', timeout=timeout,
                               data_consumer=data_consumer)
        if not data.endswith(b'\x04'):
            raise PyboardError('timeout waiting for first EOF reception')
        data = data[:-1]

        # wait for error output
        data_err = self.read_until(1, b'\x04', timeout=timeout)
        if not data_err.endswith(b'\x04'):
            raise PyboardError('timeout waiting for second EOF reception')
        data_err = data_err[:-1]

        # return normal and error output
        return data, data_err

    def exec_raw_no_follow(self, command):
        if isinstance(command, bytes):
            command_bytes = command
        else:
            command_bytes = bytes(command, encoding='utf8')

        # check we have a prompt
        data = self.read_until(1, b'>')
        if not data.endswith(b'>'):
            raise PyboardError('could not enter raw repl')

        # write command
        for i in range(0, len(command_bytes), 256):
            self.serial.write(
                command_bytes[i:min(i + 256, len(command_bytes))])
            time.sleep(0.01)
        self.serial.write(b'\x04')

        # check if we could exec command
        data = self.serial.read(2)
        if data != b'OK':
            raise PyboardError('could not exec command')

    def exec_raw(self, command, timeout=10, data_consumer=None):
        self.exec_raw_no_follow(command)
        return self.follow(timeout, data_consumer)

    def eval(self, expression):
        ret = self.exec('print({})'.format(expression))
        ret = ret.strip()
        return ret

    def exec(self, command, data_consumer=None):
        ret, ret_err = self.exec_raw(command, data_consumer=data_consumer)
        if ret_err:
            raise PyboardError('exception', ret, ret_err)
        return ret

    def execfile(self, filename):
        with open(filename, 'rb') as f:
            pyfile = f.read()
        return self.exec(pyfile)

    def data_consumer(self, data):
        oprint(data.decode('utf-8'), end='')

    def runfile(self, filename):
        with open(filename, 'rb') as f:
            pyfile = f.read()
        self.exec(pyfile, self.data_consumer)
