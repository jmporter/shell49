import threading

"""
List of devices.

# managed by connect
DEFAULT_DEV = None
DEVS = []
DEV_IDX = 1
DEV_LOCK = threading.RLock()
"""

class Dev:

    def __init__(self):
        self.devs = {}

    def default_device(self, set=0):
        return None
