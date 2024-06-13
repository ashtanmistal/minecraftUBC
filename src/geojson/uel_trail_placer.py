"""
This script transforms the UEL trail data and places the trails in the Minecraft world.
"""
import json
import math
import os

import amulet
import numpy as np
from amulet.api.block import Block
from amulet.api.errors import ChunkDoesNotExist, ChunkLoadError
from amulet.utils import block_coords_to_chunk_coords
from tqdm import tqdm

import src.helpers

# path = "/resources/geojson_ubcv/context/geojson/ubcv_psrp_trail.geojson"
TRAIL_GEOJSON_PATH = os.path.join(src.helpers.PROJECT_DIRECTORY,
                                  "resources", "geojson_ubcv", "context", "geojson", "ubcv_psrp_trail.geojson")

DEFAULT_PATH_BLOCK = Block("minecraft", "dirt_path")
DEFAULT_PATH_WIDTH = 2

MIN_BOUND_X = 0
MAX_BOUND_X = 4608
MIN_BOUND_Z = -2304
MAX_BOUND_Z = 2816
MAX_HEIGHT = 80

SURFACEMAT_CONVERSION = {
    "-": DEFAULT_PATH_BLOCK,
    "Asphalt": Block("minecraft", "gray_concrete_powder"),
    "Gravel": Block("minecraft", "gravel"),
    "NA": DEFAULT_PATH_BLOCK,
    "Native Surface": None,
}


def convert_feature(feature, level):
    """
    Translates a feature in the geojson file to a trail in the Minecraft world.
    :param feature: a trail feature from the geojson file
    :param level: Amulet level object
    :return: None
    """
    coordinates, properties = feature["geometry"]["coordinates"], feature["properties"]
    surface_material = properties["SURFACEMAT"]
    if surface_material == "Native Surface":
        return  # skip this trail if it has no surface material
    line_segments = []
    for i in range(len(coordinates) - 1):
        x1, z1 = src.helpers.convert_lat_long_to_x_z(coordinates[i][1], coordinates[i][0])
        x2, z2 = src.helpers.convert_lat_long_to_x_z(coordinates[i + 1][1], coordinates[i + 1][0])
        # see if it's within the chunk bounds
        if x1 < MIN_BOUND_X or x1 > MAX_BOUND_X or z1 < MIN_BOUND_Z or z1 > MAX_BOUND_Z:
            continue
        line_segments.append((x1, z1, x2, z2))

    for line_segment in line_segments:
        place_line_segment(line_segment, level, surface_material)


def place_line_segment(line_segment, level, surface_material):
    """
    Places a line segment in the Minecraft world.
    :param line_segment: Set of coordinates representing a line segment
    :param level: Amulet level object
    :param surface_material: The surface material of the trail
    :return: None
    """
    intersecting_blocks = src.helpers.bresenham_2d(line_segment[0], line_segment[1], line_segment[2],
                                                   line_segment[3])
    for i in range(DEFAULT_PATH_WIDTH):
        angle = math.atan2(line_segment[3] - line_segment[1], line_segment[2] - line_segment[0])
        start_x_new = line_segment[0] + i * math.sin(angle)
        start_z_new = line_segment[1] + i * math.cos(angle)
        end_x_new = line_segment[2] + i * math.sin(angle)
        end_z_new = line_segment[3] + i * math.cos(angle)
        intersecting_blocks.extend(src.helpers.bresenham_2d(start_x_new, start_z_new, end_x_new, end_z_new))
    for block in intersecting_blocks:
        cx, cz = block_coords_to_chunk_coords(block[0], block[1])
        try:
            chunk = level.get_chunk(cx, cz, "minecraft:overworld")
        except ChunkDoesNotExist:
            return

        blocks = chunk.blocks
        height = np.max(np.nonzero(
            blocks[block[0] % 16, src.helpers.MIN_HEIGHT:MAX_HEIGHT, block[1] % 16])) + src.helpers.MIN_HEIGHT
        if height is None:
            continue
        else:
            level.set_version_block(
                block[0],
                height,
                block[1],
                "minecraft:overworld",
                src.helpers.GAME_VERSION,
                SURFACEMAT_CONVERSION[surface_material]
            )


def place_trails(world_directory):
    """
    Places the trails in the Minecraft world.
    :return: None
    """
    level = amulet.load_level(world_directory)
    with open(TRAIL_GEOJSON_PATH) as f:
        data = json.load(f)
    for feature in tqdm(data["features"]):
        try:
            convert_feature(feature, level)
        except ChunkDoesNotExist:
            continue  # some of the trails are outside the bounds of the world
        except ChunkLoadError:
            continue
        except ValueError:
            continue
    level.save()
    level.close()


if __name__ == "__main__":
    place_trails(src.helpers.WORLD_DIRECTORY)
