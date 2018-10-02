from __future__ import division, print_function

import os
import numpy as np
import lsst.afw.coord as afwCoord
import lsst.afw.geom as afwGeom
from . import DEFAULT_RERUN

__all__ = ['project_dir', 'make_afw_coords', 'get_psf', 
           'sky_cone', 'tracts_n_patches']
           
project_dir = os.path.dirname(os.path.dirname(__file__))


def make_afw_coords(coord_list):
    """
    Convert list of ra and dec to lsst.afw.coord.IcrsCoord.
    Parameters
    ----------
    coord_list : list of tuples or tuple
        ra and dec in degrees.
    Returns
    -------
    afw_coords : list of lsst.afw.coord.IcrsCoord
    """
    if type(coord_list[0]) in (float, int, np.float64):
        ra, dec = coord_list
        afw_coords = afwGeom.SpherePoint(afwGeom.Angle(ra, afwGeom.degrees),
                                         afwGeom.Angle(dec, afwGeom.degrees))
    else:
        afw_coords = [
            afwGeom.SpherePoint(afwGeom.Angle(ra, afwGeom.degrees),
            afwGeom.Angle(dec, afwGeom.degrees)) for ra, dec in coord_list]
    return afw_coords


def get_psf(exp, coord=None):
    """Get the coadd PSF image."""
    psf = exp.getPsf()
    if coord is not None:
        if type(coord)!=afwGeom.SpherePoint:
            coord = make_afw_coords(coord)
        wcs = exp.getWcs()
        coord = wcs.skyToPixel(coord)
        try:
            psf_img = psf.computeKernelImage(coord)
            return psf_img
        except Exception:
            print('**** Cannot compute PSF Image at coord *****')
            return None
    else:
        return psf


def sky_cone(ra_c, dec_c, theta, steps=50, include_center=True):
    """
    Get ra and dec coordinates of a cone on the sky.
    
    Parameters
    ----------
    ra_c, dec_c: float
        Center of cone in degrees.
    theta: astropy Quantity, float, or int
        Angular radius of cone. Must be in arcsec
        if not a Quantity object.
    steps: int, optional
        Number of steps in the cone.
    include_center: bool, optional
        If True, include center point in cone.
    
    Returns
    -------
    ra, dec: ndarry
        Coordinates of cone.
    """
    from spherical_geometry.polygon import SphericalPolygon
    if type(theta)==float or type(theta)==int:
        theta = theta*u.arcsec
    cone = SphericalPolygon.from_cone(
        ra_c, dec_c, theta.to('deg').value, steps=steps)
    ra, dec = list(cone.to_lonlat())[0]
    ra = np.mod(ra - 360., 360.0)
    if include_center:
        ra = np.concatenate([ra, [ra_c]])
        dec = np.concatenate([dec, [dec_c]])
    return ra, dec


def tracts_n_patches(coord_list, skymap=None, data_dir=DEFAULT_RERUN):
    """
    Find the tracts and patches that overlap with the 
    coordinates in coord_list. Pass the four corners of 
    a rectangle to get all tracts and patches that overlap
    with this region.
    Parameters
    ----------
    coord_list : list (tuples or lsst.afw.coord.IcrsCoord)
        ra and dec of region
    data_dir : string, optional
        Rerun directory. 
    skymap : lsst.skymap.ringsSkyMap.RingsSkyMap, optional
        The lsst/hsc skymap. If None, it will be created.
    Returns
    -------
    region_ids : structured ndarray
        Tracts and patches that overlap coord_list.
    tract_patch_dict : dict
        Dictionary of dictionaries, which takes a tract 
        and patch and returns a patch info object.
    """
    if type(coord_list[0])==float or type(coord_list[0])==int:
        coord_list = [make_afw_coords(coord_list)]
    elif type(coord_list[0])!=afwGeom.SpherePoint:
        coord_list = make_afw_coords(coord_list)

    if skymap is None:
        import lsst.daf.persistence
        butler = lsst.daf.persistence.Butler(data_dir)
        skymap = butler.get('deepCoadd_skyMap', immediate=True)

    tract_patch_list = skymap.findTractPatchList(coord_list)

    ids = []
    tract_patch_dict = {}
    for tract_info, patch_info_list in tract_patch_list:
        patch_info_dict = {}
        for patch_info in patch_info_list:
            patch_index = patch_info.getIndex()
            patch_id = str(patch_index[0])+','+str(patch_index[1])
            ids.append((tract_info.getId(), patch_id))
            patch_info_dict.update({patch_id:patch_info})
        tract_patch_dict.update({tract_info.getId():patch_info_dict})
    region_ids = np.array(ids, dtype=[('tract', int), ('patch', 'S4')])
    return region_ids, tract_patch_dict
