#  Ground denoising algorithm for pre-existing Minecraft world
#  written by: Ashtan Mistal

import amulet
import numpy as np
from amulet.api.block import Block
from amulet.api.chunk import Chunk
from amulet.api.errors import ChunkDoesNotExist, ChunkLoadError
from amulet.utils.world_utils import block_coords_to_chunk_coords
import math
from tqdm import tqdm
from bresenham import get_intersecting_block_coords
from sidewalk_placer import get_height_of_point, MAX_SEARCH_RADIUS, min_y, max_y

"""This algorithm takes in a Minecraft world and a range of x and z coordinates to denoise. It denoises only the 
ground terrain, and leaves all other blocks untouched. It does this by first getting the current chunk, 
then iterating through all x,z coordinates in the chunk that do not have any ground terrain blocks. It then searches 
the neighbouring x,z blocks until it finds an appropriate height. Then, it searches in a spherical fashion until it 
finds 4 blocks of ground terrain. These coordinates are then used to create a plane, which is then used to fill in 
the missing ground terrain. This process is repeated for all chunks in the given range of x and z coordinates."""

terrain_blocks = {
    "moss_block": Block("minecraft", "moss_block"),
    "stone": Block("minecraft", "stone"),
    "white_concrete": Block("minecraft", "white_concrete"),
    "light_gray_concrete": Block("minecraft", "light_gray_concrete"),
    "grass_block": Block("minecraft", "grass_block"),
    "dirt": Block("minecraft", "dirt"),
    "andesite": Block("minecraft", "andesite"),
    "dirt_path": Block("minecraft", "dirt_path")
}

game_version = ("java", (1, 19, 4))


# The current chunk, mi, and the 8 surrounding chunks, ul, um, ur, le, ri, ll, lm, lr

def is_terrain_block(x, z, level):
    """
    Determines whether the given block is a ground block.
    :param level: the Minecraft level object
    :param x: the x coordinate of the block
    :param z: the z coordinate of the block
    :return: True if the block is a ground block, False otherwise
    """
    return any(level.get_version_block(x, y, z, "minecraft:overworld", game_version)[0].base_name
               in terrain_blocks for y in range(min_y, max_y))


def make_plane(control_points):
    """
    Creates a plane from the given control points.
    :param control_points: the control points to use (not in any particular order)
    :return: A list of x,y,z coordinates that make up the plane
    """
    # To do this, we need to basically find every Minecraft block that lies in the plane within the control points.
    # We can do this with what is basically a 3D version of the Bresenham line algorithm, adapted for planes.
    # We have an implementation of the 3d line algorithm in the bresenham.py file, so we can use that.
    # We'll need to pick two of the control points (the ones that are furthest apart) and use those to create a line.
    # We will then use the third control point and use that to create a line that intersects the first line (iterating
    # through each block coordinate in the first line and using that as a coordinate in the second line). We will then
    # store all coordinates that are found from the second line in a list, and then repeat the process for the next
    # control point from the first line. We will then have a list of all coordinates that lie in the plane.


def denoise_chunk(chunk_coords, level, max_search_radius=MAX_SEARCH_RADIUS):
    """
    Denoises the given chunk in the given Minecraft level.
    :param chunk_coords: the chunk coordinates
    :param level: the Minecraft level object
    :param max_search_radius: the maximum search radius for the denoising algorithm
    :return: None
    """
    # Iterate through all blocks in the chunk
    for cx in range(16):
        for cz in range(16):
            # If it's not a ground block, we need to denoise it
            x, z = chunk_coords[0] * 16 + cx, chunk_coords[1] * 16 + cz
            if not is_terrain_block(x, z, level):
                # Search for a ground block in the neighbouring chunks
                height, _, search_radius = get_height_of_point(cx, cz, 0, level, max_search_radius, True)
                # now let's search outwards starting with the given radius, until we find 3 control points
                # these will be the points with which to create a plane
                control_points = []
                while len(control_points) < 3:
                    # search in a "spherical" fashion for the next control point
                    for x in range(-search_radius, search_radius):
                        for z in range(-search_radius, search_radius):
                            # if the block is a ground block, add it to the list of control points
                            if is_terrain_block(x, z, level):
                                control_points.append((x, z))
                    # if we didn't find enough control points, increase the search radius and try again
                    search_radius += 1
                    if search_radius > max_search_radius:
                        # we've searched too far this is likely under a building
                        break
                # now we have 3 control points, we can create a plane. To do so we will need to determine what points
                # we should draw a line between to create the plane. We want to avoid line intersections with other
                # lines, so we will need to do some math to determine which points to use to create the plane.
                if len(control_points) < 3:
                    # we didn't find enough control points, so we can't create a plane
                    continue
                blocks = make_plane(control_points)
                # now we have the blocks that make up the plane, we can fill them in
                for block in blocks:
                    level.set_version_block(block[0], block[1], block[2],
                                            "minecraft:overworld", game_version, terrain_blocks["moss_block"])
                # now we have filled in the plane, we can move on to the next block


def denoise_range(level, x_min, x_max, z_min, z_max, max_search_radius=MAX_SEARCH_RADIUS):
    """
    Denoises the given range of x and z coordinates in the given Minecraft level.
    :param level: the Minecraft level object
    :param x_min: the minimum x coordinate to denoise
    :param x_max: the maximum x coordinate to denoise
    :param z_min: the minimum z coordinate to denoise
    :param z_max: the maximum z coordinate to denoise
    :param max_search_radius: the maximum search radius for the denoising algorithm
    :return: None
    """
    # Iterate through all chunks in the given range
    for cx in tqdm(range(math.floor(x_min / 16), math.ceil(x_max / 16))):
        for cz in range(math.floor(z_min / 16), math.ceil(z_max / 16)):
            denoise_chunk((cx, cz), level, max_search_radius)


level = amulet.load_level("../world/UBC")
denoise_range(level, -100, 100, -100, 100)
level.save()
level.close()
