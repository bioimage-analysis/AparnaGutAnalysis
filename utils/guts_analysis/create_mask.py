from skimage import io, filters, feature, measure, morphology, util
import numpy as np
from skimage.draw import polygon
from scipy import ndimage
from skimage.external.tifffile import TiffFile
import re
import alphashape
from joblib import Parallel, delayed


def bounding_box(viewer, img, DAPI_Ch=0):
    z,x,y = img.shape[0], img.shape[2], img.shape[3]
    mask = np.zeros((x,y), dtype = np.bool)
    rr, cc = polygon(viewer.layers[1].data[0][:,0], viewer.layers[1].data[0][:,1], mask.shape)
    mask[rr, cc] = 1
    mask_3D = np.zeros((z,x,y), dtype = np.bool)
    mask_3D[:] = mask
    DAPI = img[:,DAPI_Ch,:,:]
    DAPI[~mask_3D] = 0
    bbox = ndimage.find_objects(mask_3D)
    DAPI_roi = DAPI[bbox[0]]

    return DAPI_roi, bbox

def _metadata(file):
    with TiffFile(file) as tif:
        meta = tif.info()

    metadata = {}
    for line in meta.splitlines():
        _, _, key_x = line.partition('x_resolution (2I)')
        _, _, key_y = line.partition('y_resolution (2I)')
        _, _, key_z = line.partition('spacing:')
        _, _, key_unit = line.partition('unit:')
        if key_x:
            x_data = [int(x.group()) for x in re.finditer(r'\d+', key_x)]
            x_resolution = 1/(x_data[0]/x_data[1])
            metadata['x_resolution'] = x_resolution
        if key_y:
            y_data = [int(x.group()) for x in re.finditer(r'\d+', key_y)]
            y_resolution = 1/(y_data[0]/y_data[1])
            metadata['y_resolution'] = y_resolution

        if key_z:
            metadata['z_resolution'] = float(key_z)
        if key_unit:
            metadata['unit'] = key_unit
    return metadata

def _gaussian_blur(file, DAPI_roi):
    metadata = _metadata(file)
    # The microscope reports the following spacing
    original_spacing = np.array([metadata['z_resolution'], metadata['x_resolution'], metadata['y_resolution']])
    base_sigma = 2.0
    sigma = base_sigma / original_spacing
    gaussian_to_seg = filters.gaussian(DAPI_roi, multichannel=False, sigma=sigma)
    return gaussian_to_seg

def _roll_ball(file, DAPI_roi, size =20):
    blured = _gaussian_blur(file, DAPI_roi)
    result = np.empty(blured.shape)
    # Background substraction
    background = ndimage.minimum_filter(blured, size = 8)
    result = blured-background
    return(result)

def _binary(file, DAPI_roi, size =20):
    back_sub = _roll_ball(file, DAPI_roi, size =20)
    threshold_triangle = filters.threshold_triangle(back_sub)
    binary_DAPI = back_sub > threshold_triangle
    return binary_DAPI, back_sub

def _create_mask(binary_data, slices = 0):
    result = np.zeros(binary_data[slices].shape)

    coord_x, coord_y = np.where(binary_data[slices]>0)
    lst_pts = np.concatenate((coord_x[:, np.newaxis], coord_y[:, np.newaxis]), axis=1)

    alpha_shape = alphashape.alphashape(lst_pts[::16], 0.1)

    if alpha_shape.type == 'MultiPolygon':
        for alpha in alpha_shape:
            if alpha.area > 20000:
                x, y = alpha.exterior.coords.xy
                rr, cc = polygon(np.asarray(x, dtype=np.int),np.asarray(y, dtype=np.int))
                result[rr, cc] = 1
    elif alpha_shape.type == 'GeometryCollection':
        pass

    else:
        x, y = alpha_shape.exterior.coords.xy
        rr, cc = polygon(np.asarray(x, dtype=np.int),np.asarray(y, dtype=np.int))
        result[rr, cc] = 1
    return result

def mask_guts(file, DAPI_roi, size =20):

    binary_DAPI, back_sub = _binary(file, DAPI_roi, size =20)
    res_paral = Parallel(n_jobs=-1)(delayed(_create_mask)(binary_DAPI, slices) for slices in range(len(binary_DAPI)))
    mask = np.asarray(res_paral)
    border = mask - morphology.erosion(mask, morphology.ball(1))
    return mask, border, back_sub
