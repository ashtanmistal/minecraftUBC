import json
import math

import amulet
import numpy as np
from amulet.api.block import Block
from amulet.api.errors import ChunkDoesNotExist, ChunkLoadError
from amulet.utils import block_coords_to_chunk_coords
from tqdm import tqdm

from scripts.geojson.helpers import bresenham_2d, convert_lat_long_to_x_z

"""
This script transforms the UEL trail data and places the trails in the Minecraft world. It also places signs
at the beginning of each trail, denoting the trail name. 
"""

path = "../../resources/geojson_ubcv/context/geojson/ubcv_psrp_trail.geojson"
game_version = ("java", (1, 19, 4))
x_offset = 480000
z_offset = 5455000

path_block = Block("minecraft", "dirt_path")
path_width = 2

x_bound_min = 0
x_bound_max = 4608
z_bound_min = -2304
z_bound_max = 2816
min_height = -64
max_height = 80

SURFACEMAT_conversion = {
    "-": path_block,
    "Asphalt": Block("minecraft", "gray_concrete_powder"),
    "Gravel": Block("minecraft", "gravel"),
    "NA": path_block,
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
        x1, z1 = convert_lat_long_to_x_z(coordinates[i][1], coordinates[i][0])
        x2, z2 = convert_lat_long_to_x_z(coordinates[i + 1][1], coordinates[i + 1][0])
        # see if it's within the chunk bounds
        if x1 < x_bound_min or x1 > x_bound_max or z1 < z_bound_min or z1 > z_bound_max:
            continue
        line_segments.append((x1, z1, x2, z2))

    for line_segment in line_segments:
        place_line_segment(line_segment, level, surface_material)


def place_line_segment(line_segment, level, surface_material):
    intersecting_blocks = bresenham_2d(line_segment[0], line_segment[1], line_segment[2], line_segment[3])
    for i in range(path_width):
        angle = math.atan2(line_segment[3] - line_segment[1], line_segment[2] - line_segment[0])
        start_x_new = line_segment[0] + i * math.sin(angle)
        start_z_new = line_segment[1] + i * math.cos(angle)
        end_x_new = line_segment[2] + i * math.sin(angle)
        end_z_new = line_segment[3] + i * math.cos(angle)
        intersecting_blocks.extend(bresenham_2d(start_x_new, start_z_new, end_x_new, end_z_new))
    for block in intersecting_blocks:
        cx, cz = block_coords_to_chunk_coords(block[0], block[1])
        try:
            chunk = level.get_chunk(cx, cz, "minecraft:overworld")
        except ChunkDoesNotExist:
            return

        blocks = chunk.blocks
        height = np.max(np.nonzero(blocks[block[0] % 16, min_height:max_height, block[1] % 16])) + min_height
        if height is None:
            continue
        else:
            level.set_version_block(
                block[0],
                height,
                block[1],
                "minecraft:overworld",
                game_version,
                SURFACEMAT_conversion[surface_material]
            )


def place_trails():
    level = amulet.load_level("../../world/UBC")
    with open(path) as f:
        data = json.load(f)
    for feature in tqdm(data["features"]):
        try:
            convert_feature(feature, level)
        except ChunkDoesNotExist:
            continue
        except ChunkLoadError:
            continue
        except ValueError:
            continue
    level.save()
    level.close()


if __name__ == "__main__":
    place_trails()
