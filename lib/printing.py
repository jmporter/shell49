import sys

# Attributes
# 0 Reset all attributes
# 1 Bright
# 2 Dim
# 4 Underscore
# 5 Blink
# 7 Reverse
# 8 Hidden

LT_BLACK = "\x1b[1;30m"
LT_RED = "\x1b[1;31m"
LT_GREEN = "\x1b[1;32m"
LT_YELLOW = "\x1b[1;33m"
LT_BLUE = "\x1b[1;34m"
LT_MAGENTA = "\x1b[1;35m"
LT_CYAN = "\x1b[1;36m"
LT_WHITE = "\x1b[1;37m"

DK_BLACK = "\x1b[2;30m"
DK_RED = "\x1b[2;31m"
DK_GREEN = "\x1b[2;32m"
DK_YELLOW = "\x1b[2;33m"
DK_BLUE = "\x1b[2;34m"
DK_MAGENTA = "\x1b[2;35m"
DK_CYAN = "\x1b[2;36m"
DK_WHITE = "\x1b[2;37m"

NO_COLOR = "\x1b[0m"
BG_LT_BLACK = "\x1b[1;40m"
BG_LT_RED = "\x1b[1;41m"
BG_LT_GREEN = "\x1b[1;42m"
BG_LT_YELLOW = "\x1b[1;43m"
BG_LT_BLUE = "\x1b[1;44m"
BG_LT_MAGENTA = "\x1b[1;45m"
BG_LT_CYAN = "\x1b[1;46m"
BG_LT_WHITE = "\x1b[1;47m"

BG_DK_BLACK = "\x1b[2;40m"
BG_DK_RED = "\x1b[2;41m"
BG_DK_GREEN = "\x1b[2;42m"
BG_DK_YELLOW = "\x1b[2;43m"
BG_DK_BLUE = "\x1b[2;44m"
BG_DK_MAGENTA = "\x1b[2;45m"
BG_DK_CYAN = "\x1b[2;46m"
BG_DK_WHITE = "\x1b[2;47m"

DIR_COLOR = LT_CYAN
PROMPT_COLOR = LT_YELLOW
MPY_COLOR = LT_GREEN
END_COLOR = NO_COLOR
DEBUG_COLOR = DK_MAGENTA
ERR_COLOR = LT_RED
QUIET_COLOR = DK_BLUE
OUTPUT_COLOR = LT_MAGENTA

DEBUG = False
QUIET = False

def debug(enable=None):
    """Set/get debug flag"""
    global DEBUG
    if enable is not None:
        DEBUG = enable
    return DEBUG


def quiet(enable=None):
    """Set/get quiet flag"""
    global QUIET
    if enable is not None:
        QUIET = enable
    return QUIET


def nocolor():
    """Disable output coloring"""
    global DIR_COLOR, PROMPT_COLOR, MPY_COLOR, END_COLOR
    global DEBUG_COLOR, ERR_COLOR, QUIET_COLOR, OUTPUT_COLOR, NO_COLOR
    DIR_COLOR = ''
    PROMPT_COLOR = ''
    MPY_COLOR = ''
    END_COLOR = ''
    DEBUG_COLOR = ''
    ERR_COLOR = ''
    QUIET_COLOR = ''
    OUTPUT_COLOR = ''
    NO_COLOR = ''
    END_COLOR = ''


def cprint(*a, color=NO_COLOR, file=sys.stdout, **kw):
    """Same as print but with optional color parameter,"""
    print(color, end='', file=file)
    print(*a, **kw, file=file)
    print(END_COLOR, end='', file=file)


def oprint(*a, **kw):
    """Command output"""
    cprint(*a, color=OUTPUT_COLOR, **kw)


def mprint(*a, **kw):
    """Micropython output"""
    cprint(*a, color=MPY_COLOR, **kw)

def eprint(*a, **kw):
    """Same as print, but prints to stder and sets color to ERR_COLOR."""
    a = list(a)
    if a and len(a) > 0 and isinstance(a[0], str):
        if not a[0].startswith('*'):
            a = list(a)
            a[0] = "*** " + a[0]
    cprint(*a, color=ERR_COLOR, **kw)


def dprint(*a, **kw):
    """Debug messages"""
    if DEBUG:
        cprint(*a, color=DEBUG_COLOR, **kw)


def qprint(*a, **kw):
    """Prints only when quiet is set to false."""
    if not QUIET:
        cprint(*a, color=QUIET_COLOR, **kw)
