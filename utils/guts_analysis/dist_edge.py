from sklearn.neighbors import KDTree
import numpy as np
from skimage import feature, morphology
import matplotlib.pyplot as plt


def _ditance_edges(back_sub, border):
    #Find coordinates of the different nucleus
    coord = feature.peak_local_max(back_sub,
                                   threshold_abs=np.quantile(back_sub, 0.9),
                                   footprint=np.ones((8, 8, 8), dtype=np.bool),
                                   indices=True)
    # Reshape border to be [n_samples (number of pixels), n_features (number of dimension)]
    border_reshape = np.squeeze(np.dstack(np.where(border>0)))
    #Create a KDTree
    tree = KDTree(border_reshape)
    #Find shortest distance of these coordinates to the edge of the guts
    distance_membrane = np.empty((len(coord), 4))
    for i, coo in enumerate(coord):
        closest_dist, closest_id = tree.query(coo[np.newaxis, :] , k=1)
        distance_membrane[i,0] = closest_dist
        distance_membrane[i,1] = coo[0]
        distance_membrane[i,2] = coo[1]
        distance_membrane[i,3] = coo[2]

    return distance_membrane

def nucleus_vs_dist_guts(back_sub, border, plot=True):
    distance_membrane = _ditance_edges(back_sub, border)
    #Creating an image with markers of nucleus color coded base on the distance
    #to the edge of the guts
    dist_mark = np.zeros(back_sub.shape, dtype=np.int)
    dist_mark[distance_membrane[:,1].astype(np.int),
              distance_membrane[:,2].astype(np.int),
              distance_membrane[:,3].astype(np.int)] = distance_membrane[:,0]+1
    dist_mark = morphology.dilation(dist_mark, morphology.ball(4))
    dist_mark = morphology.dilation(dist_mark, morphology.ball(4))
    #Histogram of the result
    if plot:
        cm = plt.cm.get_cmap('plasma')
        n, bins, patches = plt.hist(distance_membrane[:,0], color="green")

        bin_centers = 0.5 * (bins[:-1] + bins[1:])

        # scale values to interval [0,1]
        col = bin_centers - min(bin_centers) + 0.1
        col /= max(col)

        for c, p in zip(col, patches):
            plt.setp(p, 'facecolor', cm(c))
        plt.xlabel('distance from edge in px')
        plt.ylabel('Number of cells')
        plt.show()
    return dist_mark
