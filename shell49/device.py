from . print_ import qprint, dprint, eprint
from . pyboard import Pyboard, PyboardError
from . remote_op import listdir, remote_repr, set_time, epoch, \
    osdebug, board_name, test_buffer
import shell49.remote_op

import inspect
import time
import serial
import os
import socket


class DeviceError(Exception):
    """Errors that we want to report to the user and keep running."""
    pass


class Device(object):

    def __init__(self, config, default_name):
        self.config = config
        self.has_buffer = False  # needs to be set for remote_eval to work
        self.id = config.find_board_by_name(default_name)


    def _set_pyb(self, pyb, default_name):
        self.pyb = pyb
        # try to retrieve the current name from the board
        name = self.remote_eval(board_name, default_name)
        qprint("Connected to board '{}'".format(name))
        # update id to match true board name
        self.id = self.config.find_board_by_name(name, create=True)
        self.has_buffer = self.remote_eval(test_buffer)
        dprint("find has_buffer", self.has_buffer)
        self.root_dirs = ['/{}/'.format(dir) for dir in self.remote_eval(listdir, '/')]
        dprint("root_dirs", self.root_dirs)
        self.sync_time()
        dprint("synced time")
        # self.esp_osdebug(None)


    def get_id(self):
        return self.id


    def get(self, option, default=None):
        return self.config.get(self.id, option, default=default)


    def name(self):
        return self.config.get(self.id, 'name')


    def set(self, option, value):
        self.config.set(self.id, option, value)


    def remove_option(self, name):
        self.config.remove(self.id, name)


    def options(self):
        return self.config.options(self.id)


    def config_string(self):
        return self.config.config_string(self.id)


    def address(self):
        raise DeviceError("Device.address called - Device is abstract class")


    def name_path(self):
        return '/{}/'.format(self.name())


    def check_pyb(self):
        """Raises an error if the pyb object was closed."""
        if self.pyb is None:
            raise DeviceError('serial port %s closed' % self.address())


    def close(self):
        """Closes the serial port."""
        if self.pyb and self.pyb.serial:
            self.pyb.serial.close()
        self.pyb = None


    def is_root_path(self, filename):
        """Determines if 'filename' corresponds to a directory on this device."""
        test_filename = filename + '/'
        for root_dir in self.root_dirs:
            if test_filename.startswith(root_dir):
                return True
        return False


    def root_directories(self):
        return self.root_dirs


    def is_serial_port(self, port):
        return False


    def is_telnet_ip(self, ip):
        return False


    def is_telnet(self):
        return False


    def read(self, num_bytes):
        """Reads data from the pyboard over the serial port."""
        self.check_pyb()
        try:
            return self.pyb.serial.read(num_bytes)
        except (serial.serialutil.SerialException, TypeError):
            # Write failed - assume that we got disconnected
            self.close()
            raise DeviceError('serial port %s closed' % self.address())


    def remote(self, func, *args, xfer_func=None, **kwargs):
        """Calls func with the indicated args on the micropython board."""
        time_offset = self.get('time_offset', default=946684800)
        # buffer_size must be consistent between remote and local methods
        # e.g. for recv_file_from_host &  send_file_to_remote
        buffer_size = self.get('buffer_size', default=128)
        shell49.remote_op.BUFFER_SIZE = buffer_size
        has_buffer = self.has_buffer
        args_arr = [remote_repr(i) for i in args]
        kwargs_arr = ["{}={}".format(k, remote_repr(v)) for k, v in kwargs.items()]
        func_str = inspect.getsource(func)
        func_str += 'output = ' + func.__name__ + '('
        func_str += ', '.join(args_arr + kwargs_arr)
        func_str += ')\n'
        func_str += 'if output is None:\n'
        func_str += '    print("None")\n'
        func_str += 'else:\n'
        func_str += '    print(output)\n'
        func_str = func_str.replace('TIME_OFFSET', '{}'.format(time_offset))
        func_str = func_str.replace('HAS_BUFFER', '{}'.format(has_buffer))
        func_str = func_str.replace('BUFFER_SIZE', '{}'.format(buffer_size))
        func_str = func_str.replace('IS_UPY', 'True')
        dprint('----- About to send %d bytes of code to the pyboard -----' % len(func_str))
        dprint(func_str)
        dprint('-----')
        self.check_pyb()
        try:
            self.pyb.enter_raw_repl()
            self.check_pyb()
            output = self.pyb.exec_raw_no_follow(func_str)
            if xfer_func:
                xfer_func(self, *args, **kwargs)
            self.check_pyb()
            output, _ = self.pyb.follow(timeout=10)
            self.check_pyb()
            self.pyb.exit_raw_repl()
        except (serial.serialutil.SerialException, TypeError):
            self.close()
            raise DeviceError('serial port %s closed' % self.address())
        dprint('-----Response-----')
        dprint(output)
        dprint('-----')
        return output


    def remote_eval(self, func, *args, **kwargs):
        """Calls func with the indicated args on the micropython board, and
           converts the response back into python by using eval.
        """
        res = self.remote(func, *args, **kwargs)
        try:
            return eval(res)
        except Exception as e:
            eprint("*** remote_eval({}, {}, {}) -> \n{} is not valid python code".format(func.__name__, args, kwargs, res))
            return None


    def execfile(self, file):
        """Transfers file to board and runs it.
           Same as typing contents of file at repl prompt.
        """
        try:
            self.pyb.enter_raw_repl()
            res = self.pyb.execfile(file)
            self.pyb.exit_raw_repl()
            return res
        except Exception as ex:
            eprint("*** ", ex)


    def exec(self, code):
        self.pyb.enter_raw_repl()
        res = self.pyb.exec(code)
        self.pyb.exit_raw_repl()
        print(repr(res))
        return res


    def status(self):
        """Returns a status string to indicate whether we're connected to
           the pyboard or not.
        """
        if self.pyb is None:
            return 'closed'
        return 'connected'


    def sync_time(self):
        """Sets the time on the pyboard to match the time on the host."""
        now = time.localtime(time.time())
        self.remote(set_time, now.tm_year, now.tm_mon, now.tm_mday,
                              now.tm_hour, now.tm_min, now.tm_sec)
        # determine actual time offset
        # dt = time.time() - float(self.remote(epoch))
        # eprint("TIME_OFFSET is", int(dt))


    def esp_osdebug(self, level=None):
        """Sets esp.osdebug on ESP32."""
        return self.remote(osdebug, level)


    def write(self, buf):
        """Writes data to the pyboard over the serial port."""
        self.check_pyb()
        try:
            return self.pyb.serial.write(buf)
        except (serial.serialutil.SerialException, BrokenPipeError, TypeError):
            # Write failed - assume that we got disconnected
            self.close()
            raise DeviceError('{} closed'.format(self.name()))


class DeviceSerial(Device):

    def __init__(self, port, config, name=None):
        super().__init__(config, name)
        self.port = port
        baud = self.get('baudrate', default=115200)
        wait = self.get('wait', default=0)

        if wait and not os.path.exists(port):
            toggle = False
            try:
                sys.stdout.write("Waiting %d seconds for serial port '%s' to exist" % (wait, self.port))
                sys.stdout.flush()
                while wait and not os.path.exists(self.port):
                    sys.stdout.write('.')
                    sys.stdout.flush()
                    time.sleep(0.5)
                    toggle = not toggle
                    wait = wait if not toggle else wait -1
                sys.stdout.write("\n")
            except KeyboardInterrupt:
                raise DeviceError('Interrupted')

        try:
            pyb = Pyboard(self.port, baudrate=baud, wait=wait)
        except PyboardError as err:
            eprint(err)
            return
            # sys.exit(1)

        # Bluetooth devices take some time to connect at startup, and writes
        # issued while the remote isn't connected will fail. So we send newlines
        # with pauses until one of our writes succeeds.
        try:
            # we send a Control-C which should kill the current line
            # assuming we're talking to tha micropython repl. If we send
            # a newline, then the junk might get interpreted as a command
            # which will do who knows what.
            pyb.serial.write(b'\x03')
        except serial.serialutil.SerialException:
            # Write failed. Now report that we're waiting and keep trying until
            # a write succeeds
            sys.stdout.write("Waiting for transport to be connected.")
            while True:
                time.sleep(0.5)
                try:
                    pyb.serial.write(b'\x03')
                    break
                except serial.serialutil.SerialException:
                    pass
                sys.stdout.write('.')
                sys.stdout.flush()
            sys.stdout.write('\n')

        # In theory the serial port is now ready to use
        super()._set_pyb(pyb, name)

    def is_serial_port(self, port):
        return self.port == port

    def address(self):
        return self.port

    def timeout(self, timeout=None):
        """Sets the timeout associated with the serial port."""
        self.check_pyb()
        if timeout is None:
            return self.pyb.serial.timeout
        try:
            self.pyb.serial.timeout = timeout
        except:
            # timeout is a property so it calls code, and that can fail
            # if the serial port is closed.
            pass


class DeviceNet(Device):

    def __init__(self, url, config, name=None):
        super().__init__(config, name)
        self.url = url
        self.ip_address = socket.gethostbyname(url)
        user = self.get('user', default='micro')
        password = self.get('password', default='python')

        try:
            pyb = Pyboard(ip=url, user=user, password=password)
        except (socket.timeout, OSError):
            raise DeviceError('No response from {}'.format(ip_address))
        except KeyboardInterrupt:
            raise DeviceError('Interrupted')

        self._set_pyb(pyb, name)

    def timeout(self, timeout=None):
        """There is no equivalent to timeout for the telnet connection."""
        return None

    def address(self):
        return self.ip_address

    def is_telnet(self):
        return True

    def is_telnet_ip(self, ip):
        return ip == self.ip_address or ip == self.url
