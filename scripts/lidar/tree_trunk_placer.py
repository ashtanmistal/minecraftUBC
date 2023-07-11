"""
This script transforms the tree data within the LiDAR dataset. It divides the tree data into Minecraft chunks,
and performs a horizontal mean shift clustering algorithm with vertical strata analysis to determine the tree
trunk locations. The tree trunk locations are then saved both into the world and to an array, where we'll use the trunks
and the corresponding leaves to cluster the leaves and place branches outwards from the trunks.
"""

import amulet
import numpy as np
import pylas
from amulet.api.block import Block
from amulet.api.chunk import Chunk
from amulet.api.errors import ChunkDoesNotExist, ChunkLoadError
from amulet.utils import block_coords_to_chunk_coords
import math
import os
import time
from tqdm import tqdm
from scripts.lidar.lidar_surface_reconstruction import rotate_dataset, x_offset, y_offset, z_offset
from sklearn.cluster import MeanShift

MIN_BIN_FREQUENCY = 5
N_JOBS = -1


def transform_dataset(ds, start_time):
    """
    Transforms the given dataset by filtering out non-tree elements, dividing into chunks,
    and calling the chunk processor on each chunk.
    :param ds: the LiDAR dataset to transform
    :param start_time: the start time of the program
    :return: None
    """

    level = amulet.load_level("../../world/UBC")
    x, y, z, red, green, blue, labels = ds.x, ds.y, ds.z, ds.red, ds.green, ds.blue, ds.labels
    # class 5 is tall vegetation; the data we want to keep
    not_tree = np.where(labels != 5)
    x, y, z = np.delete(x, not_tree), np.delete(y, not_tree), np.delete(z, not_tree)
    labels = np.delete(labels, not_tree)
    red, green, blue = np.delete(red, not_tree), np.delete(green, not_tree), np.delete(blue, not_tree)
    dataset = rotate_dataset(np.array([x - x_offset, y - y_offset, z - z_offset]))
    x, z, y = dataset[0], dataset[1], dataset[2]
    red, green, blue = (red / 256).astype(int), (green / 256).astype(int), (blue / 256).astype(int)
    z = -z  # flip z axis to match Minecraft
    x = np.round(x).astype(int)
    y = np.round(y).astype(int)
    z = np.round(z).astype(int)

    min_x, min_y, min_z = np.floor(np.min(x)), np.floor(np.min(y)), np.floor(np.min(z))
    max_x, max_y, max_z = np.ceil(np.max(x)), np.ceil(np.max(y)), np.ceil(np.max(z))
    min_x, min_z = np.floor(min_x / 16) * 16, np.floor(min_z / 16) * 16
    max_x, max_z = np.ceil(max_x / 16) * 16, np.ceil(max_z / 16) * 16

    for ix in tqdm(range(min_x.astype(int), max_x.astype(int), 16)):
        for iz in range(min_z.astype(int), max_z.astype(int), 16):
            chunk_indices = np.where((x >= ix) & (x < ix + 16) & (z >= iz) & (z < iz + 16))
            cx, cz = block_coords_to_chunk_coords(ix, iz)
            if len(chunk_indices[0]) == 0:
                continue
            chunk = level.get_chunk(cx, cz, "minecraft:overworld")
            chunk = handle_chunk(chunk, x[chunk_indices], y[chunk_indices], z[chunk_indices],
                                 red[chunk_indices], green[chunk_indices], blue[chunk_indices])
            level.put_chunk(chunk, "minecraft:overworld")
    print("Time taken: " + str(time.time() - start_time))
    level.save()
    level.close()
    print("Saved: " + str(time.time() - start_time))


def handle_chunk(chunk, x, y, z, red, green, blue):
    """
    Handles the given chunk by performing the horizontal mean shift clustering algorithm with vertical strata analysis
    to determine the tree trunk locations. The tree trunk locations are then saved both into the world and to an array,
    where we'll use the trunks and the corresponding leaves to cluster the leaves and place branches outwards from the
    trunks.
    :param chunk: the chunk to handle
    :param x: the x coordinates of the chunk
    :param y: the y coordinates of the chunk
    :param z: the z coordinates of the chunk
    :param red: the red values of the chunk
    :param green: the green values of the chunk
    :param blue: the blue values of the chunk
    :return: the chunk with the tree trunks, branches, and leaves placed
    """

    # perform horizontal mean shift clustering algorithm with vertical strata analysis
    # to determine the tree trunk locations
    # the tree trunk locations are then saved both into the world and to an array,
    # where we'll use the trunks and the corresponding leaves to cluster the leaves and place branches outwards from the
    # trunks
    ms = MeanShift(bin_seeding=True, min_bin_freq=MIN_BIN_FREQUENCY, n_jobs=N_JOBS)
    # Because we want to perform horizontal mean shift clustering, this means that we'll need to convert our data into a
    # 16x16 grid where each cell value is the count of points in that cell.
    offset_x, offset_z = chunk.cx * 16, chunk.cz * 16
    x, z = x - offset_x, z - offset_z
    x, z = np.round(x).astype(int), np.round(z).astype(int)


def main():
    lidar_path = "../../resources/LiDAR LAS Data/las"
    start_time = time.time()
    for filename in os.listdir(lidar_path):
        if filename.endswith(".las"):
            dataset = pylas.read(os.path.join(lidar_path, filename))
            print("transforming chunks for", filename, time.time() - start_time)
            transform_dataset(dataset, start_time)
            print("done transforming chunks for", filename, time.time() - start_time)


if __name__ == "__main__":
    main()
