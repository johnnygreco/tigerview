import lsst.log
Log = lsst.log.Log()
Log.setLevel(lsst.log.ERROR)

DEFAULT_RERUN = '/tigress/HSC/DR/s18a_wide'

from . import ds9 
from . import utils
