import pandas as pd
from skimage import measure
import numpy as np
from sklearn import preprocessing
import os


def _measure_int_channel(dist_mark, img, bbox):
    data = []
    for i in range(1,dist_mark.max()):
        channels = []
        for ch in range(1, img.shape[1]):
            Ch_roi = img[:,ch,:,:][bbox[0]]
            dapi_label = measure.label(dist_mark==i)
            prop_ch = measure.regionprops(dapi_label, Ch_roi)
            values = []
            for prop in prop_ch:
                mean = prop.mean_intensity
                coord = prop.centroid
                values.append((i, ch, coord[0], coord[1], coord[2], mean))
            channels.append(np.asarray(values))
        data.append(np.vstack(channels))
    return np.vstack(data)

def create_table(dist_mark, img, bbox, file, save= True):
    data = _measure_int_channel(dist_mark, img, bbox)
    df = pd.DataFrame(data , columns = ['Distance from edges', 'channel', 'coord z',
                                    'coord x', 'coord y', 'mean intensity'])
    column_norm = []
    for i in range(1,img.shape[1]):
        x = df.loc[df['channel'] == i]['mean intensity'].values
        x_v = x.reshape(-1, 1)
        min_max_scaler = preprocessing.MinMaxScaler()
        x_scaled = min_max_scaler.fit_transform(x_v)
        column_norm.append(x_scaled)
    df["Normalized mean intensity"] = np.vstack(column_norm)
    df = df[['channel', 'Distance from edges', 'mean intensity',
         'Normalized mean intensity', 'coord z', 'coord x', 'coord y']]

    if save == True:
        path = os.path.dirname(file)
        df.to_csv(path + '/result.csv')
    return df
