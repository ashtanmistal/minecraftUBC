"""
This script transforms a LiDAR dataset into a Minecraft world. It does this by breaking up the dataset into chunks
that correspond to Minecraft chunks, and calculating the convex hull of each chunk. This resultant convex hull is then
treated as a 2d mesh which is then voxelized and denoised. The voxelized mesh is then used as a mask with which to
place blocks. Height is determined by the LiDAR data, but if none exists, the height is calculated by a weighted average
of the three nearest points. Below the surface patch, the mesh is then closed by placing blocks all the way down to the
minimum y level in Minecraft.
"""
import time

import amulet
import numpy as np
from amulet.api.block import Block
from amulet.api.chunk import Chunk
from amulet.api.errors import ChunkDoesNotExist, ChunkLoadError
from amulet.utils import block_coords_to_chunk_coords
from scipy.spatial import QhullError, ConvexHull
from tqdm import tqdm

import scripts.helpers

DEFAULT_BLOCK = Block("minecraft", "stone")
GROUND_LABEL = 2


def get_convex_hull(chunk_data):
    """
    Calculates the convex hull of the given chunk data.
    :param chunk_data: the chunk data to calculate the convex hull of
    :return: the voxelized 2d convex hull of the given chunk data
    """
    hull = ConvexHull(chunk_data[:, [0, 2]])  # calculate the convex hull of the chunk data, ignoring height
    hull_vertices = hull.points[hull.vertices]
    points_inside = np.zeros((16, 16))
    for i in range(0, len(hull_vertices)):
        vertex = hull_vertices[i]
        next_vertex = hull_vertices[(i + 1) % len(hull_vertices)]
        line = scripts.helpers.bresenham_2d(vertex[0], vertex[1], next_vertex[0], next_vertex[1])
        for point in line:
            points_inside[point[0], point[1]] = 1
    # calculate the centroid of the convex hull; we will use this as a starting point for a flood fill algorithm
    # to fill in the rest of the points
    centroid = np.round(np.mean(hull_vertices, axis=0)).astype(int)
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
                    chunk.blocks[x, scripts.helpers.MIN_HEIGHT:y, z] = block_id
                else:
                    # calculate the weighted average of the 3 nearest points
                    nearest_points = data[np.argsort(np.linalg.norm(data[:, [0, 2]] - [x, z], axis=1))[:3], :]
                    weights = 1 / np.linalg.norm(nearest_points[:, [0, 2]] - [x, z], axis=1)
                    y = np.sum(nearest_points[:, 1] * weights) / np.sum(weights)
                    if np.isnan(y):
                        pass
                    else:
                        y = int(np.round(y))
                        chunk.blocks[x, scripts.helpers.MIN_HEIGHT:y, z] = block_id

    return chunk


def handle_chunk(chunk, lidar_chunk_data, block_id):
    """
    Handles the given chunk. If data is too sparse to create a convex hull, the points are placed without interpolation.
    :param block_id: the block id of default_block in this chunk
    :param lidar_chunk_data: the LiDAR data that is within the given chunk
    :param chunk: the chunk to handle
    :return: chunk
    """
    # shift the data such that x,z are local to the chunk
    offset_x, offset_z = chunk.cx * 16, chunk.cz * 16
    lidar_chunk_data[0] -= offset_x
    lidar_chunk_data[2] -= offset_z
    transposed_data = np.transpose(lidar_chunk_data)

    try:
        chunk = voxelize_patch(get_convex_hull(transposed_data), chunk, block_id, transposed_data)
    except QhullError:
        chunk = place_points_manually(chunk, transposed_data, block_id)

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
        chunk.blocks[x.astype(int), scripts.helpers.MIN_HEIGHT:y.astype(int), z.astype(int)] = block_id

    return chunk


def transform_dataset(ds, start_time):
    """
    Transforms the given dataset into a Minecraft world.
    :param ds: the LiDAR dataset to transform
    :param start_time: the start time of the program
    :return: None
    """
    if __name__ == '__main__':
        level = amulet.load_level(scripts.helpers.WORLD_DIRECTORY)
        max_x, max_z, min_x, min_z, x, y, z = scripts.helpers.preprocess_dataset(ds, GROUND_LABEL)
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
                    DEFAULT_BLOCK)
                block_id = level.block_palette.get_add_block(universal_block)

                chunk = handle_chunk(chunk, np.array([x[chunk_indices], y[chunk_indices], z[chunk_indices]]),
                                     block_id)
                level.put_chunk(chunk, "minecraft:overworld")
        print("done iterating through chunks", time.time() - start_time)
        level.save()
        level.close()
        print("Done saving level", time.time() - start_time)


if __name__ == "__main__":
    scripts.helpers.dataset_iterator(transform_dataset)
