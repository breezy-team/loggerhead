import os
import turbozpt
from turbozpt.template import PageTemplate

_base = os.path.dirname(__file__)
def _pt(name):
    return PageTemplate(os.path.join(_base, 'templates', name + '.pt'))


def file_change_summary(url, entry):
    pt = _pt('revisionfilechanges')
    return pt.render(dict(url=url, entry=entry))

def revisioninfo(url, branch, entry, includefilechanges=False):
    from loggerhead import util
    pt = _pt('revisioninfo')
    return pt.render(
        dict(url=url, change=entry, branch=branch, util=util,
             includefilechanges=False,
             file_change_summary=file_change_summary))

