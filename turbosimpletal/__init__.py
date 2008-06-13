from turbosimpletal import zptsupport

TurboZpt = zptsupport.TurboZpt

__all__ = ["TurboZpt"]

import logging
simpleTALLogger = logging.getLogger("simpleTAL")
simpleTALESLogger = logging.getLogger("simpleTALES")
simpleTALLogger.setLevel(logging.INFO)
simpleTALESLogger.setLevel(logging.INFO)
