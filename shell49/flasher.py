#! /usr/bin/env python3

from bs4 import BeautifulSoup
from urllib.request import Request, urlopen, urlretrieve
from tempfile import NamedTemporaryFile, TemporaryDirectory
from enum import Enum
from html import unescape
import urllib.parse
import os


class FlasherError(BaseException):
    pass


class FlasherFactory:
    """Repository for flashers for various architecturs and firmware."""

    _flashers = {}

    def addFlasher(flasher):
        """Register flasher"""
        FlasherFactory._flashers[flasher.firmware] = flasher

    def getFactory(firmware):
        """Get flasher for specified firmware"""
        return FlasherFactory._flashers[firmware]

    def list_flashers():
        """List all available flashers"""
        return list(FlasherFactory._flashers.keys())


class Flasher:

    def __init__(self, firmware):
        """Register flasher in FlasherFactory under descriptive firmware name"""
        self.firmware = firmware
        FlasherFactory.addFlasher(self)

    def flash(self, **kwargs):
        """Flash firmware, overridden in derived method"""
        raise FlasherError("flash() command not supported")

    def erase_flash(self, **kwargs):
        """Erase firmware of attached MCU"""
        raise FlasherError("erase_flash() command not supported")

    def versions(self):
        """Return list of available firmware versions. Overridden in derived class."""
        return [ 'latest' ]

    def release_notes(self):
        """Description of firmware"""
        return None


class Esp32Flasher(Flasher):

    """
    Flasher for standard MicroPython ESP32 firmware at http://www.micropython.org/download.
    """

    upy = "http://www.micropython.org/download"

    def __init__(self):
        """Create flasher and register in FlasherFactory"""
        super().__init__('ESP32')

    def flash(self, port="/dev/cu.SLAB_USBtoUART", baud=921600):
        """Download firmware from http://www.micropython.org/download
        and flash to ESP32 connected on specified port"""
        url = None
        req = Request(Esp32Flasher.upy)
        html_page = urlopen(req)
        soup = BeautifulSoup(html_page, "lxml")
        for link in soup.findAll('a'):
            h = link.get('href')
            if 'esp32-' in h and h.endswith('.bin'):
                url = h
        if not url:
            raise FlasherError("Cannot locate ESP32 firmware at {}".format(Esp32Flasher.upy))
        # Download to temporary location
        bin = NamedTemporaryFile(delete=False)
        print("Downloading {} to {}".format(url, bin.name))
        urlretrieve(url, bin.name)
        # Flash to Esp32
        cmd = "esptool.py " \
            "--chip esp32 --port {} --baud {} " \
            "--before default_reset --after hard_reset " \
            "write_flash -z --flash_mode dio --flash_freq 40m --flash_size detect " \
            "0x1000 {}".format(port, baud, bin.name)
        os.system(cmd)
        # Delete tempfile
        os.unlink(bin.name)

    def erase_flash(self):
        cmd = "esptool.py --port {} erase_flash".format(port)

    def release_notes(self):
        return "see {} section for ESP32".format(Esp32Flasher.upy)


class LoborisFlasher(Flasher):

    fw_url = "https://people.eecs.berkeley.edu/~boser/iot49/firmware/dual-core"

    def __init__(self):
        """Create flasher and register in FlasherFactory"""
        super().__init__('ESP32-Loboris')

    def flash(self, port="/dev/cu.SLAB_USBtoUART", baud=921600, version='latest'):
        """Download firmware from fw_url
        and flash to ESP32 connected on specified port"""
        v = list(filter(lambda s: version in s, self.versions()))
        if len(v) < 1:
            raise FlasherError("no firmware version {}".format(version))
        if len(v) > 1:
            raise FlasherError("ambiguous firmware version {}".format(version))
        with TemporaryDirectory() as dir:
            url = os.path.join(LoborisFlasher.fw_url, v[0])
            print("Downloading firmware from {} ...".format(url))
            os.system('wget -q -r -np -nH --cut-dirs=5 -R index.html -P "{}" "{}"'.format(dir, url))
            with open(os.path.join(dir, 'flash.sh')) as f:
                line = f.read()
                if 'esptool.py' in line: cmd = line
            cmd = cmd[cmd.find('0x1000'):]
            cmd = "esptool.py " \
                "--chip esp32 --port {} --baud {} " \
                "--before default_reset --after hard_reset write_flash " \
                "-z --flash_mode dio --flash_freq 40m --flash_size detect " \
                "{}".format(port, baud, cmd)
            cwd = os.getcwd()
            try:
                os.chdir(dir)
                os.system(cmd)
            finally:
                os.chdir(cwd)

    def erase_flash(self):
        """Erase ESP32 flash including filesystem"""
        cmd = "esptool.py --port {} erase_flash".format(port)

    def versions(self):
        """Return list of available firmware versions"""
        req = Request(LoborisFlasher.fw_url)
        html_page = urlopen(req)
        soup = BeautifulSoup(html_page, "lxml")
        versions = []
        for link in soup.findAll('a'):
            h = link.get('href')
            if h.startswith('V'):
                versions.append(urllib.parse.unquote(h).replace('/', ''))
        return versions

    def release_notes(self):
        """Return text description of firmware versions"""
        return urlopen(os.path.join(LoborisFlasher.fw_url, 'release_notes.txt')).read().decode('utf-8')


if __name__ == "__main__":
    FlasherFactory.addFlasher(Esp32Flasher())
    FlasherFactory.addFlasher(LoborisFlasher())
    # print("Flashers: {}".format(FlasherFactory.list_flashers()))
    f = FlasherFactory.getFactory('ESP32-Loboris')
    # print("versions:", f.versions())
    # print("release_notes:\n{}".format(f.release_notes()))
    f.flash()
    # f.erase_flash()
