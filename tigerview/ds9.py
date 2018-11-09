import numpy as np
import lsst.pipe.base
import lsst.afw.image
import lsst.afw.display
import lsst.afw.geom
import lsst.daf.persistence

from . import DEFAULT_RERUN 
from . import utils
from .tiger_cutout import make_cutout


class Viewer(object):

    def __init__(self, butler=None, skymap=None, rerun=DEFAULT_RERUN, 
                 coadd_label='deepCoadd_calexp'):

        self._butler = butler
        self._skymap = skymap
        self.rerun = rerun 
        self.coadd_label = coadd_label
        self.frame = {}
        self.patch = {}
        self.exp = {}

    @property
    def butler(self):
        """
        The Butler.
        """
        if self._butler is None:
            import lsst.daf.persistence
            self._butler = lsst.daf.persistence.Butler(self.rerun)
        return self._butler

    @property
    def skymap(self):
        """
        The Skymap.
        """
        if self._skymap is None:
            self._skymap = self.butler.get('deepCoadd_skyMap', immediate=True)
        return self._skymap

    def _radec_to_patch(self, ra, dec):
        ids, _ = utils.tracts_n_patches([ra, dec], 
                                        skymap=self.skymap, 
                                        data_dir=self.rerun)
        tract = ids['tract'][0] # using first tract/patch for now
        patch = ids['patch'][0] # is there a better way to choose?
        return tract, patch

    def display_patch(self, tract=None, patch=None, band='i', 
                      ra=None, dec=None, frame=1, mask_trans=100,
                      scale=['linear', 'zscale']):

        if tract is None:
            assert ra is not None and dec is not None
            tract, patch = self._radec_to_patch(ra, dec)
        else:
            assert patch is not None

        if type(patch) == bytes or type(patch) == np.bytes_:
            patch = patch.decode("utf-8")

        data_id = dict(tract=tract, patch=patch, filter='HSC-'+band.upper())
        exp = self.butler.get(self.coadd_label, data_id, immediate=True)
        self.exp[frame] = exp
        disp = lsst.afw.display.Display(frame)
        disp.mtv(exp)
        disp.setMaskTransparency(mask_trans)
        disp.scale(*scale)
        self.frame[frame] = lsst.pipe.base.Struct(disp=disp, exp=exp)

    def display_cutout(self, ra, dec, radius, band='i', frame=1, zoom=1, 
                       mask_trans=100, scale=['linear', 'zscale']):

        cutout = make_cutout(ra, dec, radius, band, skymap=self.skymap,
                             rerun=self.rerun, butler=self.butler, 
                             coadd_label=self.coadd_label)
        self.cutout[frame] = cutout
        disp = lsst.afw.display.Display(frame)
        disp.mtv(cutout)
        disp.setMaskTransparency(mask_trans)
        disp.zoom(zoom)
        disp.scale(*scale)
        self.frame[frame] = lsst.pipe.base.Struct(disp=disp, exp=cutout)

    def display_source(self, ra, dec, radius, theta=0.0, ellip=None, 
                       frame=1, color='green'):

        if ellip is None:
            marker = 'o'
        else:
            a = radius
            b = a * (1 - ellip)
            shape = dict(a=a, b=b, theta=np.deg2rad(theta))
            marker = lsst.afw.geom.ellipses.Axes(**shape)

        coord = utils.make_afw_coords([ra, dec])
        x, y = self.exp[frame].getWcs().skyToPixel(coord)
        self.frame[frame].disp.dot(marker, x, y, ctype=color, size=radius)
