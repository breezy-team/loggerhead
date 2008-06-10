from turbosimpletal import zptsupport

TurboZpt = zptsupport.TurboZpt

__all__ = ["TurboZpt"]

from turbogears.view import engines, stdvars

engines['zpt'] = TurboZpt(stdvars)

import logging
simpleTALLogger = logging.getLogger("simpleTAL")
simpleTALESLogger = logging.getLogger("simpleTALES")
simpleTALLogger.setLevel(logging.INFO)
simpleTALESLogger.setLevel(logging.INFO)
