def add_arg(*args, **kwargs):
    """Used for shell argument parsing"""
    return (args, kwargs)


def escape(str):
    """Precede all special characters with a backslash."""
    out = ''
    for char in str:
        if char in '\\ ':
            out += '\\'
        out += char
    return out


def unescape(str):
    """Undoes the effects of the escape() function."""
    out = ''
    prev_backslash = False
    for char in str:
        if not prev_backslash and char == '\\':
            prev_backslash = True
            continue
        out += char
        prev_backslash = False
    return out


def align_cell(fmt, elem, width):
    """Returns an aligned element."""
    if fmt == "<":
        return elem + ' ' * (width - len(elem))
    if fmt == ">":
        return ' ' * (width - len(elem)) + elem
    return elem


def column_print(fmt, rows, print_func):
    """Prints a formatted list, adjusting the width so everything fits.
    fmt contains a single character for each column. < indicates that the
    column should be left justified, > indicates that the column should
    be right justified. The last column may be a space which imples left
    justification and no padding.

    """
    # Figure out the max width of each column
    num_cols = len(fmt)
    width = [max(0 if isinstance(row, str) else len(row[i]) for row in rows)
             for i in range(num_cols)]
    for row in rows:
        if isinstance(row, str):
            # Print a seperator line
            print_func('  '.join([row * width[i] for i in range(num_cols)]))
        else:
            print_func('  '.join([align_cell(fmt[i], row[i], width[i])
                                  for i in range(num_cols)]))
