# Lidar surface reconstruction
"""
This script transforms a LiDAR dataset into a Minecraft world. It does this by breaking up the dataset into chunks
that correspond to Minecraft chunks, and calculating the convex hull of each chunk. This resultant convex hull is then
treated as a 2d mesh which is then voxelized and denoised. The voxelized mesh is then used as a mask with which to
place blocks. Height is determined by the LiDAR data, but if none exists, the height is calculated by a weighted average
of the three nearest points. Below the surface patch, the mesh is closed by placing blocks all the way down to the
minimum y level in Minecraft.
"""
import math
import time

import amulet
import numpy as np
from amulet.api.block import Block
from amulet.api.chunk import Chunk
from amulet.api.errors import ChunkDoesNotExist, ChunkLoadError
from amulet.utils import block_coords_to_chunk_coords
from scipy.spatial import QhullError, ConvexHull
from tqdm import tqdm

from scripts.helpers import bresenham_2d, dataset_iterator

min_height = -64
default_block = Block("minecraft", "stone")
x_offset = 480000
y_offset = 5455000
z_offset = 59


def rotate_dataset(dataset):
    rotation_degrees = 28.000
    rotation = math.radians(rotation_degrees)
    # NOTE this assumes x,y as terrain and z as height, something that is different from Minecraft (but is the default
    # for the LiDAR data)
    inverse_rotation_matrix = np.array([[math.cos(rotation), math.sin(rotation), 0],
                                        [-math.sin(rotation), math.cos(rotation), 0],
                                        [0, 0, 1]])
    return np.matmul(inverse_rotation_matrix, dataset)


def get_convex_hull(chunk_data):
    """
    Calculates the convex hull of the given chunk data.
    :param chunk_data: the chunk data to calculate the convex hull of
    :return: the voxelized 2d convex hull of the given chunk data
    """
    chunk_data = chunk_data[:, [0, 2]]  # get rid of the height data (y)
    hull = ConvexHull(chunk_data)
    vertices = hull.points[hull.vertices]
    points_inside = np.zeros((16, 16))
    for i in range(0, len(vertices)):
        vertex = vertices[i]
        next_vertex = vertices[(i + 1) % len(vertices)]
        line = bresenham_2d(vertex[0], vertex[1], next_vertex[0], next_vertex[1])
        for point in line:
            points_inside[point[0], point[1]] = 1
    # calculate the centroid of the convex hull; we will use this as a starting point for a flood fill algorithm
    # to fill in the rest of the points
    centroid = np.round(np.mean(vertices, axis=0)).astype(int)
    queue = [centroid]
    while len(queue) > 0:
        point = queue.pop()
        if points_inside[point[0], point[1]] == 0:
            points_inside[point[0], point[1]] = 1
            queue.append(point + np.array([1, 0]))
            queue.append(point + np.array([-1, 0]))
            queue.append(point + np.array([0, 1]))
            queue.append(point + np.array([0, -1]))

    # We now need to denoise the points_inside array; there will be some points that are not part of the convex hull
    # but should be. A lot of this is speckle noise on chunk edges.
    # we'll first test by seeing if the total number of points that are 0 is less than 16. If so, we'll just set all
    # the points to 1
    # For further denoising, see fill_region.py for a region flood fill algorithm
    if np.sum(points_inside == 0) < 16:
        points_inside = np.ones((16, 16))  # this might not look the best near the beach, but it's better than nothing
    return points_inside


def voxelize_patch(points_inside, chunk, block_id, data):
    """
    Voxelize the given patch. Interpolates the three nearest neighbours if no height data for a given point.
    :param block_id: the block id of default_block in this chunk
    :param points_inside: the points inside the convex hull of the flattened chunk
    :param chunk: the chunk to voxelize
    :param data: the LiDAR data that is within the given chunk
    :return: chunk object with the height data filled in
    """
    # we need to iterate through points_inside. If height data is available for a given x and z, we use that
    # otherwise we need to calculate using a weighted average of the 3 nearest points
    for x in range(0, 16):
        for z in range(0, 16):
            if points_inside[x, z] == 1:
                indices = np.where((data[:, 0] >= x) & (data[:, 0] < x + 1) & (data[:, 2] >= z) & (data[:, 2] < z + 1))
                sliced_data = data[indices]
                if len(sliced_data) > 0:
                    y = np.max(sliced_data[:, 1]).astype(int)
                    chunk.blocks[x, min_height:y, z] = block_id
                else:
                    # calculate the weighted average of the 3 nearest points
                    nearest_points = data[np.argsort(np.linalg.norm(data[:, [0, 2]] - [x, z], axis=1))[:3], :]
                    weights = 1 / np.linalg.norm(nearest_points[:, [0, 2]] - [x, z], axis=1)
                    y = np.sum(nearest_points[:, 1] * weights) / np.sum(weights)
                    if np.isnan(y):
                        pass
                    else:
                        y = int(np.round(y))
                        chunk.blocks[x, min_height:y, z] = block_id
    return chunk


def handle_chunk(chunk, data, block_id):
    """
    Handles the given chunk. If data is too sparse to create a convex hull, the points are placed without interpolation.
    :param block_id: the block id of default_block in this chunk
    :param data: the LiDAR data that is within the given chunk
    :param chunk: the chunk to handle
    :return: chunk
    """
    # shift the data such that x,z are local to the chunk
    offset_x, offset_z = chunk.cx * 16, chunk.cz * 16
    data[0] -= offset_x
    data[2] -= offset_z
    data = np.transpose(data)

    try:
        chunk = voxelize_patch(get_convex_hull(data), chunk, block_id, data)
    except QhullError:
        chunk = place_points_manually(chunk, data, block_id)

    return chunk


def place_points_manually(chunk, data, block_id):
    """
    Places the given points into the given chunk without interpolation. This is intended for use where there are not
    enough data points to calculate the convex hull.
    :param block_id: the block id of default_block in this chunk
    :param data: the LiDAR data that is within the given chunk
    :param chunk: the chunk to handle
    :return: chunk with data placed
    """
    for x, y, z in data:
        chunk.blocks[x.astype(int), min_height:y.astype(int), z.astype(int)] = block_id
    return chunk


def transform_dataset(ds, start_time):
    """
    Transforms the given dataset into a Minecraft world.
    :param ds: the LiDAR dataset to transform
    :param start_time: the start time of the program
    :return: None
    """
    if __name__ == '__main__':
        level = amulet.load_level("/world/UBC")
        x, y, z, labels = ds.x, ds.y, ds.z, ds.classification
        # remove anything that is not ground terrain
        indices_to_delete = np.where(labels != 2)
        x, y, z, labels = np.delete(x, indices_to_delete), \
            np.delete(y, indices_to_delete), \
            np.delete(z, indices_to_delete), \
            np.delete(labels, indices_to_delete)
        dataset = rotate_dataset(np.array([x - x_offset, y - y_offset, z - z_offset]))
        x, z, y = dataset[0], dataset[1], dataset[2]
        z = -z  # flip z axis to properly align with Minecraft's north orientation

        x = np.floor(x)
        y = np.floor(y)
        z = np.floor(z)
        # remove duplicate points (considering x, y, z pairs)
        unique_indices = np.unique(np.array([x, y, z]), axis=1, return_index=True)[1]
        x, y, z = x[unique_indices], y[unique_indices], z[unique_indices]

        min_x, min_y, min_z = np.floor(np.min(x)), np.floor(np.min(y)), np.floor(np.min(z))
        max_x, max_y, max_z = np.ceil(np.max(x)), np.ceil(np.max(y)), np.ceil(np.max(z))
        print("done transforming and sorting dataset", time.time() - start_time)
        min_x, min_z = np.floor(min_x / 16) * 16, np.floor(min_z / 16) * 16
        max_x, max_z = np.ceil(max_x / 16) * 16, np.ceil(max_z / 16) * 16
        for ix in tqdm(range(min_x.astype(int), max_x.astype(int), 16)):
            for iz in range(min_z.astype(int), max_z.astype(int), 16):
                chunk_indices = np.where((x >= ix) & (x < ix + 16) & (z >= iz) & (z < iz + 16))
                cx, cz = block_coords_to_chunk_coords(ix, iz)
                try:
                    chunk = level.get_chunk(cx, cz, "minecraft:overworld")
                except ChunkDoesNotExist:
                    chunk = Chunk(cx, cz)
                except ChunkLoadError:
                    continue
                if len(chunk_indices[0]) == 0:
                    level.put_chunk(chunk, "minecraft:overworld")  # save the chunk if it is empty to avoid terrain gen
                    continue
                # find the unique block_id of default_block in the chunk
                universal_block, _, _ = level.translation_manager.get_version("java", (1, 19, 4)).block.to_universal(
                    default_block)
                block_id = level.block_palette.get_add_block(universal_block)

                chunk = handle_chunk(chunk, np.array([x[chunk_indices], y[chunk_indices], z[chunk_indices]]),
                                     block_id)
                level.put_chunk(chunk, "minecraft:overworld")
        print("done iterating through chunks", time.time() - start_time)
        level.save()
        level.close()
        print("Done saving level", time.time() - start_time)


if __name__ == "__main__":
    lidar_path = "/resources/LiDAR LAS Data/las"
    dataset_iterator(lidar_path, transform_dataset)
