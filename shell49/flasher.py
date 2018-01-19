#! /usr/bin/env python3

from . print_ import qprint
from shell49 import esptool

from urllib.request import urlopen, urlretrieve
from urllib.error import HTTPError
from tempfile import TemporaryDirectory
from ast import literal_eval
import os, shlex


class FlasherError(BaseException):
    pass


class Flasher:

    def __init__(self, *, board='HUZZAH32', url="https://people.eecs.berkeley.edu/~boser/iot49/firmware/"):
        if not url.endswith('/'):
            url = url + '/'
        self.board = board
        self.url = url
        specfile = url + board + '/spec.py'
        qprint("download", specfile)
        try:
            with urlopen(specfile) as f:
                self.spec = literal_eval(f.read().decode('utf-8'))
        except HTTPError:
            raise FlasherError("{} not found".format(specfile))

    def _esptool(self, cmd):
        # os.system(cmd)
        esptool.sys.argv = shlex.split(cmd)
        esptool._main()

    def flash(self, version, **kwargs):
        flasher = self.spec['flasher']
        if flasher == 'ESP':
            self._esp_flasher(version, **kwargs)
        elif flasher == 'DFU':
            self._dfu_flasher(version, **kwargs)
        else:
            raise FlasherError("no flasher for '{}'".format(flasher))

    def _esp_flasher(self, version, **kwargs):
        """Flash firmware"""
        # flash command
        cmd = "esptool.py --port {} --baud {} {} {}".format(
            kwargs['port'],
            kwargs['baudrate'],
            kwargs['flash_options'],
            ' '.join(["0x{:x} {}".format(addr, file)
                      for addr, file in self.spec['partitions']])
        )
        try:
            with TemporaryDirectory() as dir:
                os.chdir(dir)
                # download firmware
                for p in self.spec['partitions']:
                    url = self.url + self.board + '/' + version + '/' + p[1]
                    qprint("download", url)
                    urlretrieve(url, p[1])
                # flash
                qprint("flashing ...", cmd)
                self._esptool(cmd)
        except PermissionError:
            # Windows throws error
            pass

    def _dfu_flasher(self, version, **kwargs):
        raise NotImplementedError("DFU flasher not implemented")

    def erase_flash(self, port):
        qprint("erasing flash ...")
        cmd = "esptool.py --port {} erase_flash".format(port)
        self._esptool(cmd)

    def versions(self):
        """Return list of available firmware versions."""
        return self.spec['versions']


if __name__ == "__main__":
    port = "/dev/cu.SLAB_USBtoUART"
    baud = 921600
    flash_options = "--chip esp32 " \
        "--before default_reset --after hard_reset " \
        "write_flash -z --flash_mode dio --flash_freq 40m --flash_size detect "
    version = "STABLE"
    board = "HUZZAH32"
    url = "https://people.eecs.berkeley.edu/~boser/iot49/firmware"
    f = Flasher(board=board, url=url)
    print("versions:")
    print('\n'.join(["{:8s} {}".format(v, d) for v, d in f.versions()]))
    print()
    f.erase_flash(port)
    print()
    f.flash(version, flash_options=flash_options, port=port, baudrate=baud)
