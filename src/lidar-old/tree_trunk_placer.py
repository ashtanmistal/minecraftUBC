"""
This script transforms the tree data within the LiDAR dataset. It divides the tree data into Minecraft chunks,
and performs a horizontal mean shift clustering algorithm with vertical strata analysis to determine the tree
trunk locations. The tree trunk locations are then saved both into the world and to an array, where we'll use the trunks
and the corresponding leaves to cluster the leaves and place branches outwards from the trunks.
"""

import time

import amulet
import numpy as np
from amulet import Block
from amulet.utils import block_coords_to_chunk_coords
from amulet_nbt import StringTag
from sklearn.cluster import MeanShift, DBSCAN
from tqdm import tqdm

import src.helpers

MIN_BIN_FREQUENCY = 4
TRUNK_BLOCK = Block("minecraft", "spruce_log")
LEAVES_BLOCK = Block("minecraft", "spruce_leaves", {"persistent": StringTag("true")})
TALL_VEGETATION_LABEL = 5


def transform_dataset(ds, start_time):
    """
    Transforms the given dataset by filtering out non-tree elements, dividing into chunks,
    and calling the chunk processor on each chunk.
    :param ds: the LiDAR dataset to transform
    :param start_time: the start time of the program
    :return: None
    """
    level = amulet.load_level(src.helpers.WORLD_DIRECTORY)
    max_x, max_z, min_x, min_z, x, y, z = src.helpers.preprocess_dataset(ds, TALL_VEGETATION_LABEL)

    trunk_block_universal, _, _ = level.translation_manager.get_version("java", (1, 20, 4)).block.to_universal(
        TRUNK_BLOCK)
    trunk_block_id = level.block_palette.get_add_block(trunk_block_universal)
    leaves_block_universal, _, _ = level.translation_manager.get_version("java", (1, 20, 4)).block.to_universal(
        LEAVES_BLOCK)
    leaves_block_id = level.block_palette.get_add_block(leaves_block_universal)

    print("Finished preprocessing. Starting chunk processing.", time.time() - start_time)

    for ix in tqdm(range(min_x.astype(int), max_x.astype(int), 16)):
        for iz in range(min_z.astype(int), max_z.astype(int), 16):
            chunk_indices = np.where((x >= ix) & (x < ix + 16) & (z >= iz) & (z < iz + 16))
            cx, cz = block_coords_to_chunk_coords(ix, iz)
            if len(chunk_indices[0]) == 0:
                continue
            chunk = level.get_chunk(cx, cz, "minecraft:overworld")
            chunk = handle_chunk(chunk, x[chunk_indices], y[chunk_indices], z[chunk_indices], trunk_block_id,
                                 leaves_block_id)
            level.put_chunk(chunk, "minecraft:overworld")
    print("Time taken: " + str(time.time() - start_time))
    level.save()
    level.close()
    print("Saved: " + str(time.time() - start_time))


def handle_chunk(chunk, x, y, z, trunk_block_id, leaves_block_id):
    """
    Handles the given chunk by performing the horizontal mean shift clustering algorithm with vertical strata analysis
    to determine the tree trunk locations. The tree trunk locations are then saved both into the world and to an array,
    where we'll use the trunks and the corresponding leaves to cluster the leaves and place branches outwards from the
    trunks.
    :param chunk: the chunk to handle
    :param x: the x data within the chunk
    :param y: the y data within the chunk
    :param z: the z data within the chunk
    :param trunk_block_id: the block ID of the trunk block
    :param leaves_block_id: the block ID of the leaves block
    :return: the chunk with the tree trunks, branches, and leaves placed
    """

    # First, we need to do some data pre-processing. Right now, the level object has the Minecraft world data,
    # and that is effectively the DEM of the surface. As a result, we need to convert the height of each point into
    # an above-ground height; i.e. subtracting the current height of the surface at that point from the height of the
    # point.
    cx, cz = chunk.cx, chunk.cz
    original_y = y
    ground_heights = np.zeros((16, 16))
    for ix in range(16):
        for iz in range(16):
            indices = np.where((x >= cx * 16 + ix) & (x < cx * 16 + ix + 1) & (z >= cz * 16 + iz) & (
                    z < cz * 16 + iz + 1))
            column = chunk.blocks[ix, src.helpers.MIN_HEIGHT:src.helpers.MAX_HEIGHT, iz]
            column = np.array(column).flatten()
            non_air_indices = np.where(column != 0)
            if len(non_air_indices[0]) == 0:
                return chunk
            dem_height = np.max(non_air_indices) + src.helpers.MIN_HEIGHT
            y[indices] -= dem_height
            ground_heights[ix, iz] = dem_height
    # We should remove outliers now. Any point with a height of less than or equal to 2 is too close to the ground to be
    # useful to us. This does impact hedges a bit - as those are classified as trees for some reason - but that is only
    # an issue off-campus.
    delete_indices = np.where(y <= 2)
    x, y, z = np.delete(x, delete_indices), np.delete(y, delete_indices), np.delete(z, delete_indices)
    original_y = np.delete(original_y, delete_indices)
    if len(x) == 0 or len(y) == 0 or len(z) == 0:
        return chunk

    # The study we're basing this off of also removed points with an above-ground height greater than three standard
    # deviations above the mean. We don't need to do the same, as the LiDAR dataset we're working with has sufficient
    # denoising already done.

    # Now the horizontal mean shift clustering means that instead of providing the heights of the points, we need to
    # just provide the x and z axes. The MeanShift algorithm itself performs the binning and density estimation.

    chunk = place_leaves(chunk, cx, cz, ground_heights, leaves_block_id, x, y, z)
    try:
        ms = MeanShift(bin_seeding=True, min_bin_freq=MIN_BIN_FREQUENCY, cluster_all=False, max_iter=127, n_jobs=6)
        ms.fit(np.array([x, z]).T)
        ms_labels = ms.labels_
        cluster_centers = ms.cluster_centers_
    except ValueError:
        # We should only perform mean shift if the number of points is enough to actually perform the algorithm.
        # Otherwise, we will just return the chunk with the leaves placed.
        return chunk

    # Now we need to do the vertical strata analysis.
    crown_clusters, non_ground_points, tree_cluster_centers, tree_clusters = vertical_strata_analysis(cluster_centers,
                                                                                                      ms_labels,
                                                                                                      x, y, z)

    # Now we need to assign the crown clusters to the nearest tree cluster
    # If there are no tree clusters then we can just skip this step
    if len(tree_clusters) > 0:
        for cluster in crown_clusters:
            cluster_indices = np.where(ms_labels == cluster)
            cluster_x, cluster_y, cluster_z = non_ground_points[cluster]
            for point in np.array([cluster_x, cluster_y, cluster_z]).T:
                # find the nearest tree cluster
                comparison_point = np.array([point[0], point[2]])
                nearest_cluster = tree_clusters[
                    np.argmin(np.linalg.norm(np.array(tree_cluster_centers) - comparison_point, axis=1))]
                # assign the point to that cluster
                ms_labels[cluster_indices] = nearest_cluster
        # re-calculating the cluster centers and calculating the height of each tree
        cluster_centers = []
        cluster_heights = []
        for cluster in np.unique(ms_labels):
            cluster_indices = np.where(ms_labels == cluster)
            cluster_x, cluster_y, cluster_z = x[cluster_indices], y[cluster_indices], z[cluster_indices]
            cluster_centers.append(np.array([np.average(cluster_x), np.average(cluster_z)]))
            cluster_heights.append(np.max(cluster_y))
        cluster_centers = np.array(cluster_centers)
        cluster_heights = np.array(cluster_heights)

        # let's place the trunks into the world
        for cluster_center, cluster_height in zip(cluster_centers, cluster_heights):
            ix, iz = int(cluster_center[0] - cx * 16), int(cluster_center[1] - cz * 16)
            dem_height = ground_heights[ix, iz].astype(int)
            column = chunk.blocks[ix, src.helpers.MIN_HEIGHT:src.helpers.MAX_HEIGHT, iz]
            column = np.array(column).flatten()
            leaf_block_indices = np.where(column == leaves_block_id)
            if len(leaf_block_indices[0]) > 0:
                max_leaf_height = np.max(leaf_block_indices) + src.helpers.MIN_HEIGHT
                chunk.blocks[ix, int(dem_height):max_leaf_height, iz] = trunk_block_id
        # Now it's time to create tree branches. The best way to do this is via DBSCAN. This will be done per tree,
        # so we'll need to iterate over each tree cluster and call a helper function to do the DBSCAN on it and
        # parameterize the lines. That function will return a tuple of vertices for each branch line - One point on
        # the tree trunk, and the cluster center.
        chunk = create_branches(x, original_y, z, ms_labels, cluster_centers, cluster_heights, chunk, trunk_block_id,
                                leaves_block_id, ground_heights)

    return chunk


def place_leaves(chunk, cx, cz, ground_heights, leaves_block_id, x, y, z):
    for x_point, y_point, z_point in zip(x, y, z):
        if y_point <= 2:
            continue
        ix, iz = int(x_point - cx * 16), int(z_point - cz * 16)
        chunk.blocks[ix, int(y_point + ground_heights[ix, iz]), iz] = leaves_block_id
    chunk.changed = True
    return chunk


def create_branches(x, y, z, ms_labels, cluster_centers, cluster_heights, chunk, trunk_block_id, leaves_block_id,
                    dem_heights):
    """
    This function creates the branches for each tree in the chunk through a combination of DBSCAN and constrained
    optimization.
    :param x: array of the LiDAR x coordinates in the chunk
    :param y: array of the LiDAR y coordinates in the chunk
    :param z: array of the LiDAR z coordinates in the chunk
    :param ms_labels: array of labels for each point corresponding to the cluster it belongs to
    :param cluster_centers: centers of each tree trunk (x and z coordinates)
    :param cluster_heights: heights of each tree trunk
    :param chunk: the chunk object that we are editing
    :param trunk_block_id: the block id of the trunk
    :param leaves_block_id: the block id of the leaves
    :param dem_heights: the heights of the DEM at each point in the chunk
    :return: The chunk object with the branches added.
    """
    cx, cz = chunk.cx, chunk.cz
    for cluster, cluster_center, cluster_height in zip(np.unique(ms_labels), cluster_centers, cluster_heights):
        cluster_indices = np.where(ms_labels == cluster)
        cluster_x, cluster_y, cluster_z = x[cluster_indices], y[cluster_indices], z[cluster_indices]
        # now we need to perform DBSCAN on the cluster.
        min_samples = 7  # this is the minimum number of points required to form a branch. We can change this later.
        epsilon = 2
        if len(cluster_x) > min_samples:
            # we want to perform a 3d DBSCAN on the cluster
            cluster_points = np.array([cluster_x, cluster_y, cluster_z]).T
            db = DBSCAN(eps=epsilon, min_samples=min_samples, metric='euclidean', n_jobs=6).fit(cluster_points)
            labels = db.labels_
            core_samples = db.core_sample_indices_
            # Now for every unique label that's not -1, we want to get the core points that correspond to it
            # Those core points are what we'll use to calculate the cluster center.
            core_sample_labels = labels[core_samples]
            tree_height = dem_heights[int(cluster_center[0] - cx * 16), int(cluster_center[1] - cz * 16)]
            for label in np.unique(core_sample_labels):
                centroid = np.average(cluster_points[np.where(core_sample_labels == label)], axis=0)
                points_in_cluster = cluster_points[np.where(labels == label)]  # these are the points that we want to
                # use in our constrained optimization
                # We will use a more simplified version of the optimization problem given we will eventually be
                # truncating to Minecraft blocks anyway. This will save a lot of time.
                # As such we just need to draw a line between the centroid and the trunk (with the height on the trunk
                # being the variable to optimize)
                distances = []
                for height in np.arange(centroid[2] - 2, centroid[2] + 2, 1):  # Even more constrained for speed
                    # the first vertex is just the centroid itself
                    # the second vertex is the trunk point
                    trunk_point = np.array([cluster_center[0], height, cluster_center[1]])
                    # now it's time to calculate the distance between all the points in the cluster and the line
                    # between the trunk point and the centroid
                    distance = np.linalg.norm(np.cross(points_in_cluster - trunk_point, points_in_cluster - centroid),
                                              axis=1) / np.linalg.norm(centroid - trunk_point)
                    distances.append(np.sum(distance))
                best_height = np.argmin(distances)
                offset_x, offset_z = -cx * 16, -cz * 16
                # The max/min bounding below is resultant from debugging out-of-bounds errors. Not sure if they're
                # necessary anymore.
                cluster_center_x = max(0, min(int(cluster_center[0] + offset_x), 15))
                cluster_center_z = max(0, min(int(cluster_center[1] + offset_z), 15))
                centroid_x = max(0, min(int(centroid[0] + offset_x), 15))
                centroid_z = max(0, min(int(centroid[2] + offset_z), 15))
                branch_blocks = src.helpers.bresenham_3d(cluster_center_x, int(best_height + tree_height),
                                                         cluster_center_z, centroid_x,
                                                         int(centroid[1] + tree_height), centroid_z)
                if len(branch_blocks) > 7:  # Removing long branches due to the inherent errors in selecting a maximum
                    # window size for the horizontal mean shift clustering: crown clusters are assigned to the closest
                    # tree *in the same chunk* which may not be the actual closest tree.
                    continue
                for block in branch_blocks:
                    column = chunk.blocks[block[0], src.helpers.MIN_HEIGHT:src.helpers.MAX_HEIGHT, block[2]]
                    column = np.array(column).flatten()
                    leaf_block_indices = np.where(column == leaves_block_id)
                    if len(leaf_block_indices[0]) > 0:  # if there exists a leaf block in the column, we're under a tree
                        # and it makes sense to place a branch. Otherwise, it was an error, and we shouldn't place one.
                        # Again a resultant error from large constraints placed on the horizontal mean shift clustering.
                        chunk.blocks[block[0], block[1], block[2]] = trunk_block_id
                chunk.changed = True

    return chunk


def vertical_strata_analysis(cluster_centers, meanshift_labels, x, y, z):
    """
    This function performs the vertical strata analysis on the clusters to determine which clusters are crown clusters
    :param cluster_centers: mean shift cluster centers
    :param meanshift_labels: array of labels for each point
    :param x: Array of x coordinates in the chunk
    :param y: Array of y coordinates in the chunk (height)
    :param z: Array of z coordinates in the chunk
    :return: crown_clusters (list of cluster indices), non_ground_points (list of arrays of non-ground points),
    tree_cluster_centers (list of tree cluster centers), tree_clusters (list of tree cluster indices)
    """
    non_ground_points = []
    crown_clusters = []
    crown_cluster_centers = []
    tree_clusters = []
    tree_cluster_centers = []
    for cluster in np.unique(meanshift_labels):
        # if the label is -1, continue
        if cluster == -1:
            continue
        cluster_indices = np.where(meanshift_labels == cluster)
        cluster_x, cluster_y, cluster_z = x[cluster_indices], y[cluster_indices], z[cluster_indices]
        vertical_gap_y = np.max(cluster_y) * 0.3  # this 0.3 is based on the study
        non_ground_indices = np.where(cluster_y > vertical_gap_y)
        # we can ignore the ground residuals now. We just want to keep the crown and stem points
        non_ground_points.append(
            np.array([cluster_x[non_ground_indices], cluster_y[non_ground_indices], cluster_z[non_ground_indices]]))

        # Now we need to determine if this is a crown cluster or a tree cluster. To do this we analyze the vertical
        # length ratio of the cluster.
        vlr = (np.max(cluster_y) - np.min(cluster_y)) / np.max(cluster_y)
        # A high VLR cluster is a tree cluster, a low VLR cluster is a crown cluster
        cutoff = 0.62  # Modified cutoff value from the study to try and get more tree clusters given the fact that we
        # a. are taking into account less data points, and b. are limiting the meanshift to a per-chunk basis
        if vlr < cutoff:
            crown_clusters.append(cluster)  # crown cluster. We need to assign these points to the nearest tree
            # cluster later.
            crown_cluster_centers.append(cluster_centers[cluster])
        else:
            tree_clusters.append(cluster)
            tree_cluster_centers.append(cluster_centers[cluster])

    return crown_clusters, non_ground_points, tree_cluster_centers, tree_clusters


if __name__ == "__main__":
    finished_datasets = ["480000_5454000.las", "480000_5455000.las", "480000_5456000.las", "480000_5457000.las",
                         "481000_5454000.las", "481000_5455000.las", "481000_5456000.las", "481000_5457000.las",
                         "481000_5458000.las", "482000_5454000.las", "482000_5455000.las", "482000_5456000.las",
                         "482000_5457000.las", "482000_5458000.las", "483000_5454000.las", "483000_5455000.las",
                         "483000_5456000.las", "483000_5457000.las"]
    src.helpers.dataset_iterator(transform_dataset, finished_datasets)
