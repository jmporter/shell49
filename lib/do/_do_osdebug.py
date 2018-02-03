def do_osdebug(self, line):
    """osdebug  [ none (default) | error | warning | info | debug | verbose ]

    Sets debug level on ESP32. Does nothing on architectures that do not
    implement esp.osdebug().
    """
    if line is '':
        line = 'none'
    level = self.boards.default.remote(osdebug, line)
    print("set debug level to {}".format(level.decode('utf-8')), end='')


def osdebug(level):
    """osdebug on standard MicroPython firmware"""
    try:
        import esp
        l = esp.LOG_ERROR
        if level:
            if level is 'error':
                l = esp.LOG_ERROR
            elif level is 'warning':
                l = esp.LOG_WARNING
            elif level is 'info':
                l = esp.LOG_INFO
            elif level is 'debug':
                l = esp.LOG_DEBUG
            elif level is 'verbose':
                l = esp.LOG_VERBOSE
            else:
                level = 'none'
        esp.osdebug('', l)
        return level
    except:
        return "*** Cannot set osdebug level"
