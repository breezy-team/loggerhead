'''Profiling tools for Loggerhead.'''


def tabulate(cells):
    """Format a list of lists of strings in a table.

    The 'cells' are centered.

    >>> print ''.join(tabulate(
    ...     [['title 1', 'title 2'],
    ...      ['short', 'rather longer']]))
     title 1     title 2
      short   rather longer
    """
    widths = {}
    for row in cells:
        for col_index, cell in enumerate(row):
            widths[col_index] = max(len(cell), widths.get(col_index, 0))
    result = []
    for row in cells:
        result_row = ''
        for col_index, cell in enumerate(row):
            result_row += cell.center(widths[col_index] + 2)
        result.append(result_row.rstrip() + '\n')
    return result


def memory_profile_debug(app):
    '''Wrap `app` to provide memory profiling information for loggerhead.'''
    def wrapped(environ, start_response):
        if environ['PATH_INFO'] != '/memory-usage':
            return app(environ, start_response)
        else:
            start_response('200 Ok', [])
            return 'Memory Profiling'
    return wrapped

