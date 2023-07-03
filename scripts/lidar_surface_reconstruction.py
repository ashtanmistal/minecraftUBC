# Lidar surface reconstruction
"""
This script transforms a LiDAR dataset into a Minecraft world. It does this by breaking up the dataset into chunks that correspond to Minecraft chunks, and performing Delaunay triangulation on each chunk. This resultant triangulation is then used as a surface mesh to calculate the height of each block in the chunk though barycentric interpolation where there exists an intersecting face. Below the surface patch, the mesh is closed by placing blocks all the way down to the minimum y level in Minecraft. No additional mesh data is needed for below the surface. All of this processing is done in parallel to speed up the process, but the Minecraft chunks must be placed in series given the level lock on the Minecraft world. Because we've rotated the dataset, some chunks may already have data in it from a previous dataset; we need to keep this data. As a result before creation of a new thread, we check if the chunk already exists in the Minecraft world and if so, we take the existing chunk and add data to it before saving it back to the world.
"""
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
import multiprocessing as mp
from deprecated.lidar.lidar_to_minecraft import x_offset, y_offset, z_offset

# Imports
from scipy.spatial import Delaunay


min_height = -64
default_block = Block("minecraft", "stone")
game_version = ("java", (1, 19, 4))

def rotate_dataset(dataset):
    rotation_degrees = 28.000
    rotation = math.radians(rotation_degrees)
    # NOTE this assumes x,y as terrain and z as height, something that is different from Minecraft (but is the default
    # for the LiDAR data)
    inverse_rotation_matrix = np.array([[math.cos(rotation), math.sin(rotation), 0],
                                        [-math.sin(rotation), math.cos(rotation), 0],
                                        [0, 0, 1]])
    return np.matmul(inverse_rotation_matrix, dataset)


def triangulate_chunk(chunk_data):
    """
    Triangulates the given chunk data using Delaunay triangulation.
    :param chunk_data: [x,y,z] data for the chunk
    :return: the triangulation
    """
    # TODO: implement this
    pass

def get_height(x, z, patch):
    """
    Gets the height of the given x,z pair in the patch using barycentric interpolation.
    :param x: x coordinate (integer)
    :param z: z coordinate (integer)
    :param patch: the triangulation with which to calculate the height
    :return: the height of the given x,z pair (integer)
    """
    return 0  # TODO implement this



def voxelize_patch(patch, chunk):
    """
    Voxelize the given patch. Patch is in the form of a Delaunay triangulation.
    :param patch: the patch to voxelize
    :param chunk: the Minecraft chunk to place voxels into
    :return: chunk with voxels placed (has not been placed into the Minecraft world yet)
    """
    # this function does not have any steps that require any lock handling and can be parallelized
    # NOTE this means that all the level checking to see if we should create a new chunk or use an existing one
    # is done elsewhere
    # All that this function does is just take the Delaunay triangulation, determine the height of each x,z pair
    # and then place blocks in the chunk accordingly as denoted in the script comments
    for x in range(0,16):
        for z in range(0, 16):
            # get the height of that given block through barycentric interpolation
            height = get_height(x, z, patch)
            chunk.blocks[x, min_height:height, z] = default_block
    return chunk

def handle_chunk(chunk, data):
    """
    Handles the given chunk. This function is called in parallel.
    :param chunk: the chunk to handle
    :return: chunk
    """
    return voxelize_patch(triangulate_chunk(data), chunk)




def main():
    level = amulet.load_level("../world/UBC")
    x, y, z, labels = ds.x, ds.y, ds.z, ds.classification
    # remove anything that is not ground terrain
    indices_to_delete = np.where(labels != 2)
    x, y, z, labels = np.delete(x, indices_to_delete), np.delete(y, indices_to_delete), np.delete(z, indices_to_delete), np.delete(labels, indices_to_delete)
    # rotate the dataset
    dataset = rotate_dataset(np.array([x - x_offset, y - y_offset, z - z_offset]))
    x, z, y = dataset[0], dataset[1], dataset[2]
    z = -z # flip z axis to properly align
    min_x, min_y, min_z = np.floor(np.min(x)), np.floor(np.min(y)), np.floor(np.min(z))
    max_x, max_y, max_z = np.ceil(np.max(x)), np.ceil(np.max(y)), np.ceil(np.max(z))

    # set up async pool
    pool = mp.Pool(mp.cpu_count())
    # iterate through chunks
    for cx in tqdm(range(min_x.astype(int), max_x.astype(int), 16)):
        for cz in tqdm(range(min_z.astype(int), max_z.astype(int), 16)):
            # check if the chunk already exists in the Minecraft world
            try:
                chunk = level.get_chunk(cx, cz, "minecraft:overworld")
            except ChunkDoesNotExist:
                chunk = Chunk(cx, cz, "minecraft:overworld", game_version)
            except ChunkLoadError:
                print("Chunk load error at {}, {}".format(cx, cz))
                continue
            # triangulate and voxelize the patch asynchronously, returning the chunk so it can be placed in the world with the primary level object
            pool.apply_async(voxelize_patch, args=(triangulate_chunk(dataset[:, np.where((x >= cx) & (x < cx + 16) & (z >= cz) & (z < cz + 16))]), chunk), callback=lambda c: level.put_chunk(c))
    pool.close()
    pool.join()
    level.save()
    level.close()



