from shell import Shell

def do_help(self, line):
    """help [COMMAND]

    List available commands with no arguments, or detailed help when
    a command is provided.
    """
    # We provide a help function so that we can trim the leading spaces
    # from the docstrings. The builtin help function doesn't do that.
    if not line:
        super(Shell, self).do_help(line)
        print("Use Control-D to exit shell49.")
        return
    if line == 'all':
        for k in dir(self):
            if k.startswith('do_'):
                print('-'*80)
                super(Shell, self).do_help(k[3:])
        return
    # check if we have a parser for this command
    parser = self.create_argparser(line)
    if parser:
        parser.print_help()
    else:
        # no parser, use built-in help
        super(Shell, self).do_help(line)
