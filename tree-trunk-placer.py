import math
import os
import time

import amulet
import numpy as np
import pylas
from PIL import Image
from amulet.api.block import Block
from amulet.api.chunk import Chunk
from amulet.api.errors import ChunkDoesNotExist, ChunkLoadError
from amulet.utils.world_utils import block_coords_to_chunk_coords
from amulet_nbt import StringTag
from tqdm import tqdm
import matplotlib.pyplot as plt

# import dbscan from scikit-learn
from sklearn.cluster import DBSCAN

start_time = time.time()
game_version = ("java", (1, 19, 4))

# coordinates of whatever we want to set as 0,0
x_offset = 480000
y_offset = 5455000
z_offset = 59

debug = True

spruce_log = Block("minecraft", "spruce_log")

# This is the same transformation that is applied to the LiDAR data in the previous script
rotation_degrees = 28.000
rotation = math.radians(rotation_degrees)
inverse_rotation_matrix = np.array([[math.cos(rotation), math.sin(rotation), 0],
                                    [-math.sin(rotation), math.cos(rotation), 0],
                                    [0, 0, 1]])


# The goal of this script is to take in a Minecraft world and some LiDAR data, and use DBSCAN to find all the trees
# in the world. Specifically, we will want to find the x,y coordinates of the base of the tree based on a weighted
# center of the leaves. The center will be weighted by the local height of the leaves: more (local) height means more
# weight. We will then want to place tree trunks in the Minecraft world at the x,y coordinates of the base of the tree
# all the way up to the height of the leaves. This will make sure that the tree trunks are always the correct height
# and that we are not removing any actual leaves from the world (as the leaves that are getting replaced are the ones
# that should be tree trunks anyway).

def perform_dbscan_dataset(ds):
    level = amulet.load_level("world/UBC")
    x, y, z, labels = ds.x, ds.y, ds.z, ds.classification
    # remove all data that is not class 5
    x = x[labels == 5]
    y = y[labels == 5]
    z = z[labels == 5]
    print("done filtering out non-tree data", time.time() - start_time)

    # if the arrays are empty, return
    if len(x) == 0 or len(y) == 0 or len(z) == 0:
        return

    # apply the same transformation to the LiDAR data as we did to the Minecraft world transformation script
    x, y, z = x - x_offset, y - y_offset, z - z_offset
    x, y, z = np.matmul(inverse_rotation_matrix, np.array([x, y, z]))

    print("done applying rotation matrix", time.time() - start_time)
    # sort by x, then y, then z. the colors should be sorted in the same way.
    sort_indices = np.lexsort((z, y, x))
    x, y, z, labels = x[sort_indices], y[sort_indices], z[sort_indices], labels[sort_indices]
    print("done sorting", time.time() - start_time)

    # removing data above the height of the world
    indices = np.where(z < 256)
    x, y, z, labels = x[indices], y[indices], z[indices], labels[indices]

    # the z axis (in Minecraft) was flipped last time, so we need to flip it back
    y = -y

    # next we need to iterate over these chunks.
    min_x, min_y, min_z = np.floor(np.min(x)), np.floor(np.min(y)), np.floor(np.min(z))
    max_x, max_y, max_z = np.ceil(np.max(x)), np.ceil(np.max(y)), np.ceil(np.max(z))

    # Now it's DBSCAN time. Unlike the previous script, we will beed to transform on the entire dataset at once
    # instead of on a per-chunk basis. This is because there are trees that span multiple chunks, and we need to
    # only place one tree trunk for a given tree (and ensure correct centroid placement).

    # DBSCAN parameters
    eps = 0.2
    min_samples = 10  # this is the minimum number of points in a cluster for it to be considered a tree
    # reshape the data into the correct format for DBSCAN
    data = np.array([x, y, z]).T

    # perform DBSCAN
    db = DBSCAN(eps=eps, min_samples=min_samples).fit(data)
    labels = db.labels_
    print("done DBSCAN", time.time() - start_time)

    # now for each cluster, we need to find the centroid of the leaves and place a tree trunk there
    # we will also need to find the height of the tree and place the tree trunk up to that height

    if debug:
        # plot the clusters
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(x, y, z, c=labels)

    # first, we need to find the unique labels
    unique_labels = set(labels)
    # remove the noise label
    unique_labels.remove(-1)
    # now we need to iterate over each label
    for label in tqdm(unique_labels):
        # find all the points that belong to this label
        indices = np.where(labels == label)
        # get the x, y, z coordinates of these points
        x, y, z = x[indices], y[indices], z[indices]
        # find the weighted centroid of the leaves
        # the weight is the z coordinate
        # the centroid is the average of the x and y coordinates
        # the height is the max z coordinate
        normalized_z = z - np.min(z)
        centroid_x = np.average(x, weights=normalized_z)
        centroid_y = np.average(y, weights=normalized_z)
        height = np.max(z) - np.min(z)
        # now we need to place the tree trunk
        if debug:
            # add the centroid to the plot
            ax.scatter(centroid_x, centroid_y, np.min(z), c="red")
        else:
            for i in range(int(height)):
                level.set_version_block(
                    centroid_x, np.min(z) + i, centroid_y,  # convert from LiDAR coord space to Minecraft coord space
                    "minecraft:overworld",
                    game_version,
                    spruce_log
                )
    if not debug:
        level.save()
        level.close()
    else:
        plt.show()


finished_datasets = []
for filename in os.listdir("LiDAR LAS Data/las/"):
    if filename.endswith(".las") and not filename[:-4] in finished_datasets:
        dataset = pylas.read("LiDAR LAS Data/las/" + filename)
        print("transforming chunks for", filename, time.time() - start_time)
        perform_dbscan_dataset(dataset)
        print("done transforming chunks for", filename, time.time() - start_time)
