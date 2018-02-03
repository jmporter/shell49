class AutoBool(object):
    """A simple class which allows a boolean to be set to False in conjunction
       with a with: statement.
    """

    def __init__(self):
        self.value = False

    def __enter__(self):
        self.value = True

    def __exit__(self, type, value, traceback):
        self.value = False

    def __call__(self):
        return self.value

    def set(self, v):
        self.value = v
