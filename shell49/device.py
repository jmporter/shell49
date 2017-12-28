from print_ import qprint, dprint, eprint
from pyboard import Pyboard, PyboardError
from remote_op import listdir, remote_repr, set_time, epoch, \
    osdebug, board_name, test_buffer

import inspect
import time
import serial
import os


class DeviceError(Exception):
    """Errors that we want to report to the user and keep running."""
    pass


class Device(object):

    def __init__(self, pyb, config, board):
        self.pyb = pyb
        self.config = config
        self.name = board        # temporary, replace below with real name obtained from board
        self.has_buffer = False  # needs to be set for remote_eval to work
        self.root_dirs = ['/{}/'.format(dir) for dir in self.remote_eval(listdir, '/')]
        self.sync_time()
        self.esp_osdebug(None)
        # try to get the actual board name
        self.name = self.remote_eval(board_name, board)
        self.has_buffer = self.remote_eval(test_buffer)

    def check_pyb(self):
        """Raises an error if the pyb object was closed."""
        if self.pyb is None:
            raise DeviceError('serial port %s closed' % self.dev_name_short)

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

    def is_serial_port(self, port):
        return False

    def read(self, num_bytes):
        """Reads data from the pyboard over the serial port."""
        self.check_pyb()
        try:
            return self.pyb.serial.read(num_bytes)
        except (serial.serialutil.SerialException, TypeError):
            # Write failed - assume that we got disconnected
            self.close()
            raise DeviceError('serial port %s closed' % self.dev_name_short)

    def remote(self, func, *args, xfer_func=None, **kwargs):
        """Calls func with the indicated args on the micropython board."""
        time_offset = self.config.getint(self.name, 'time_offset', fallback=946684800)
        buffer_size = self.config.getint(self.name, 'buffer_size', fallback=128)
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
            raise DeviceError('serial port %s closed' % self.dev_name_short)
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
        self.remote(set_time, (now.tm_year, now.tm_mon, now.tm_mday, None,
                               now.tm_hour, now.tm_min, now.tm_sec, 0))
        global TIME_OFFSET
        dt = time.time() - float(self.remote(epoch))
        dprint("TIME_OFFSET set to", int(dt))
        TIME_OFFSET = int(dt)


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
            raise DeviceError('{} closed'.format(self.dev_name_short))


class DeviceSerial(Device):

    def __init__(self, config, board_name, port):
        self.port = port
        baud = config.getint(board_name, 'baudrate', fallback=115200)
        wait = config.getint(board_name, 'wait', fallback=0)

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

        self.dev_name_short = self.port
        self.dev_name_long = '%s at %d baud' % (self.port, baud)

        try:
            pyb = Pyboard(self.port, baudrate=baud, wait=wait)
        except PyboardError as err:
            print(err)
            sys.exit(1)

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
        Device.__init__(self, pyb, config, board_name)

    def is_serial_port(self, port):
        return self.dev_name_short == port

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

    def __init__(self, ip_address, config, board):
        user = config.get(board, 'user', fallback='micro')
        password = config.get(board, 'password', fallback='python')

        try:
            pyb = Pyboard(ip_address, user=user, password=password)
        except (socket.timeout, OSError):
            raise DeviceError('No response from {}'.format(ip_address))
        except KeyboardInterrupt:
            raise DeviceError('Interrupted')
        Device.__init__(self, pyb, config, board)
        self.dev_name_short = '{} ({})'.format(self.name, ip_address)
        self.dev_name_long = self.dev_name_short

    def timeout(self, timeout=None):
        """There is no equivalent to timeout for the telnet connection."""
        return None
