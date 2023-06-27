import math
import os
import time

import amulet
import numpy as np
import pylas
from amulet.api.block import Block
from matplotlib import pyplot as plt
from tqdm import tqdm
from sklearn.cluster import MeanShift

start_time = time.time()
game_version = ("java", (1, 19, 4))

# coordinates of whatever we want to set as 0,0
x_offset = 480000
y_offset = 5455000
z_offset = 59

debug = True

spruce_log = Block("minecraft", "spruce_log")
air = Block("minecraft", "air")

# This is the same transformation that is applied to the LiDAR data in the previous script
rotation_degrees = 28.000
rotation = math.radians(rotation_degrees)
inverse_rotation_matrix = np.array([[math.cos(rotation), math.sin(rotation), 0],
                                    [-math.sin(rotation), math.cos(rotation), 0],
                                    [0, 0, 1]])


# The goal of this script is to take in a Minecraft world and some LiDAR data, and use mean shift clustering to find
# all the trees in the world. Specifically, we will want to find the x,y coordinates of the base of the tree based on
# a weighted center of the leaves. The center will be weighted by the local height of the leaves: more (local) height
# means more weight. We will then want to place tree trunks in the Minecraft world at the x,y coordinates of the base
# of the tree all the way up to the height of the leaves. This will make sure that the tree trunks are always the
# correct height and that we are not removing any actual leaves from the world (as the leaves that are getting
# replaced are the ones that should be tree trunks anyway).

def perform_tree_clustering(ds):
    level = amulet.load_level("world/UBC")
    x, y, z, labels = ds.x, ds.y, ds.z, ds.classification
    # remove all data that is not class 5
    x, y, z = x[labels == 5], y[labels == 5], z[labels == 5]
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
    x, y, z = x[sort_indices], y[sort_indices], z[sort_indices]
    print("done sorting", time.time() - start_time)

    # removing data above the height of the world
    indices = np.where(z < 256)
    x, y, z = x[indices], y[indices], z[indices]

    # the z axis (in Minecraft) was flipped last time, so we need to flip it back
    y = -y
    # change from lidar coordinates to minecraft coordinates (flip the y and z axes)
    x, y, z = x, z, y

    min_bin_freq = 5  # minimum number of points in a bin to be considered a cluster
    n_jobs = -1

    ms = MeanShift(bandwidth=2, min_bin_freq=min_bin_freq, n_jobs=n_jobs)
    meanshift_labels = ms.fit_predict(np.array([x, y, z]).T)
    cluster_centers = ms.cluster_centers_
    print("done clustering", time.time() - start_time)

    # Now that we have the candidate tree clusters we need to perform vertical strata analysis to categorize the
    # following: 1. Ground residuals 2. tree clusters 3. crown clusters

    # A vertical gap is an opening that is greater than 30% of the *cluster*'s maximum height. (30% determined by
    # the study - and may not be the best value) Points above this vertical gap are considered to be part of the
    # crown cluster; points below are ground residuals and are to be removed.

    # iterate through each cluster
    non_ground_points = []
    crown_clusters = []
    crown_cluster_centers = []
    tree_clusters = []
    tree_cluster_centers = []
    for cluster in tqdm(np.unique(meanshift_labels)):
        cluster_indices = np.where(meanshift_labels == cluster)
        cluster_x, cluster_y, cluster_z = x[cluster_indices], y[cluster_indices], z[cluster_indices]
        vertical_gap_z = np.max(cluster_z) * 0.3  # TODO magic number
        non_ground_indices = np.where(cluster_z > vertical_gap_z)
        # we can ignore the ground residuals now. We just want to keep the crown and stem points
        non_ground_points.append(
            np.array([cluster_x[non_ground_indices], cluster_y[non_ground_indices], cluster_z[non_ground_indices]]))

        # Now we need to determine if this is a crown cluster or a tree cluster. To do this we analyze the vertical
        # length ratio of the cluster.
        vlr = (np.max(cluster_z) - np.min(cluster_z)) / np.max(cluster_z)
        # A high VLR cluster is a tree cluster, a low VLR cluster is a crown cluster
        cutoff = 0.7  # TODO magic number - Not much we can do about this one, it's based on the study
        if vlr < cutoff:
            crown_clusters.append(cluster)  # crown cluster. We need to assign these points to the nearest tree
            # cluster within 5m
            crown_cluster_centers.append(cluster_centers[cluster])
        else:
            tree_clusters.append(cluster)
            tree_cluster_centers.append(cluster_centers[cluster])
    print("done vertical strata analysis", time.time() - start_time)
    # Now we need to assign the crown clusters to the nearest tree cluster
    for cluster in tqdm(crown_clusters):
        cluster_indices = np.where(meanshift_labels == cluster)
        cluster_x, cluster_y, cluster_z = non_ground_points[cluster]
        # For each point in the cluster, find the nearest tree cluster within 5m of the crow cluster center
        candidate_clusters = []
        candidate_cluster_centers = []
        for tree_cluster, tree_cluster_center in zip(tree_clusters, tree_cluster_centers):
            if np.linalg.norm(tree_cluster_center - cluster_centers[cluster]) < 5:
                candidate_clusters.append(tree_cluster)
                candidate_cluster_centers.append(tree_cluster_center)
        for point in np.array([cluster_x, cluster_y, cluster_z]).T:
            # find the nearest tree cluster
            nearest_cluster = candidate_clusters[
                np.argmin(np.linalg.norm(np.array(candidate_cluster_centers) - point, axis=1))]
            # assign the point to that cluster
            meanshift_labels[cluster_indices] = nearest_cluster
    print("done assigning crown clusters", time.time() - start_time)
    # Re-calculate the cluster centers
    cluster_centers = []
    for cluster in tqdm(np.unique(meanshift_labels)):
        cluster_indices = np.where(meanshift_labels == cluster)
        cluster_x, cluster_y, cluster_z = x[cluster_indices], y[cluster_indices], z[cluster_indices]
        cluster_centers.append(np.array([np.average(cluster_x), np.average(cluster_y), np.average(cluster_z)]))
    cluster_centers = np.array(cluster_centers)
    print("done re-calculating cluster centers", time.time() - start_time)

    # now we need to place the tree trunks at the given cluster centers. We can utilize the x,y values of the cluster
    # centers, but we need to find the z value. We'll do this based on the actual Minecraft blocks that are in the
    # area. we can start at the z value of the cluster center, go up until we no longer have any leaves,
    # and then place the trunk there. We then go down until we hit the ground. But we're not guaranteed that there's
    # any ground values there, so we'll need to set a maximum threshold based on the tall trees. This will lead to
    # some tree trunks beginning beneath the ground but that's not really a problem. The tallest trees are around 60
    # blocks in total from the ground to the top of the leaves. We'll set the threshold to that. We'll also set the
    # minimum y value to y=-57 (the lowest point in the world) so that we don't go below the ground. This is a
    # safeguard.

    if debug:  # just visualizing the clusters
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(x, y, c=meanshift_labels, cmap='tab20')
        plt.show()
    else:
        # placing the tree trunks in Minecraft
        # TODO we have since flipped y and z
        for cluster_center in tqdm(cluster_centers):
            level.get_block(cluster_center[0], cluster_center[1], cluster_center[2], "minecraft:overworld")
            # go up until we no longer have any leaves
            max_leaf_height = None
            max_air_values = 10
            for z in range(int(cluster_center[2]), 256):
                if level.get_block(cluster_center[0], cluster_center[1], z, "minecraft:overworld") != air:
                    max_leaf_height = z
                    break
                else:
                    max_air_values -= 1
                if z - cluster_center[2] > max_air_values:
                    break
            # go down until we hit the ground
            min_ground_height = None
            for z in range(int(cluster_center[2]), -57, -1):
                # check a range of the 8 neighboring blocks to see if any of them are ground blocks
                for x in range(int(cluster_center[0]) - 1, int(cluster_center[0]) + 2):
                    for y in range(int(cluster_center[1]) - 1, int(cluster_center[1]) + 2):
                        if level.get_block(x, y, z, "minecraft:overworld") != air:
                            min_ground_height = z
                            break
                    if min_ground_height is not None:
                        break
                if min_ground_height is not None:
                    break
            # now we have the min and max heights of the tree trunk
            # so we need to place tree trunks from the min to the max
            for z in range(min_ground_height, max_leaf_height + 1):
                level.set_version_block(cluster_center[0], cluster_center[1], z,
                                        "minecraft:overworld", game_version, spruce_log)
        level.save()
        level.close()


finished_datasets = ["480000_5455000"]
for filename in os.listdir("LiDAR LAS Data/las/"):
    if filename.endswith(".las") and not filename[:-4] in finished_datasets:
        dataset = pylas.read("LiDAR LAS Data/las/" + filename)
        print("transforming chunks for", filename, time.time() - start_time)
        perform_tree_clustering(dataset)
        print("done transforming chunks for", filename, time.time() - start_time)
