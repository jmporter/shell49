import sys
import calendar

# BINARY_XFER, BUFFER_SIZE, TIME_OFFSET
# Properties of the architectures and particular upy implementations
# Make properties of Device, not globals of the shell
BINARY_XFER = True
BUFFER_SIZE = 512

# CPython uses Jan 1, 1970 as the epoch, where MicroPython uses Jan 1, 2000
# as the epoch. TIME_OFFSET is the constant number of seconds needed to
# convert from one timebase to the other.
#
# We use UTC time for doing our conversion because MicroPython doesn't really
# understand timezones and has no concept of daylight savings time. UTC also
# doesn't daylight savings time, so this works well.
TIME_OFFSET = calendar.timegm((2000, 1, 1, 0, 0, 0, 0, 0, 0))



# It turns out that just because pyudev is installed doesn't mean that
# it can actually be used. So we only bother to try is we're running
# under linux.
USE_AUTOCONNECT = sys.platform == 'linux'
