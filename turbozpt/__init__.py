from turbozpt import zptsupport

TurboZpt = zptsupport.TurboZpt

__all__ = ["TurboZpt"]

from turbogears.view import engines, stdvars

engines['zpt'] = TurboZpt(stdvars)
