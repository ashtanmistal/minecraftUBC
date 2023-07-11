"""
This script handles the streetlight geojson file, which contains the location of streetlights in the landscape.
The data is given in EPSG:26910 (UTM zone 10N) coordinates, so it is converted to the Minecraft coordinate system
by adjusting the offsets and applying the rotation matrix. Afterwards, the terrain height is determined and the preset
streetlight configuration is placed in the world dependent on the LAYER attribute of the feature.
"""

import json
import math

import amulet
import numpy as np
from amulet import Block
from amulet.utils import block_coords_to_chunk_coords
from tqdm import tqdm
from amulet_nbt import StringTag

json_path = "../../resources/streetlights_json.geojson"
min_height = -20
max_height = 45
game_version = ("java", (1, 19, 4))
x_offset = 480000
z_offset = 5455000

standard_light = [
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "redstone_lamp"),
    Block("minecraft", "daylight_detector", {"inverted": StringTag("true")}),
]

bollard_light = [
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "lantern")
]

tall_light = [
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "redstone_lamp"),
    Block("minecraft", "daylight_detector", {"inverted": StringTag("true")}),
]

LAYER_conversion = {
    "E-LITE-BOLLARD": bollard_light,
    "E-LITE-POLE_LAMP": tall_light,
    "E-LITE-STANDARD": standard_light,
    "E-LITE-STANDARD_LAMP": standard_light,
    "E-LITE-SYMB": standard_light
}


def streetlight_handler():
    """
    This function handles the streetlight geojson file, which contains the location of streetlights in the landscape.
    The data is given in EPSG:26910 (UTM zone 10N) coordinates, so it is converted to the Minecraft coordinate system
    by adjusting the offsets and applying the rotation matrix. Afterwards, the terrain height is determined and the preset
    streetlight configuration is placed in the world dependent on the LAYER attribute of the feature.
    :return: None
    """
    # load the geojson file
    with open(json_path) as f:
        data = json.load(f)

    level = amulet.load_level("../../world/UBC")
    # iterate through the features
    for feature in tqdm(data["features"]):
        # get the layer attribute
        layer = feature["properties"]["LAYER"]

        # get the coordinates of the feature
        coords = feature["geometry"]["coordinates"]

        # convert the coordinates using x_offset, z_offset and the rotation matrix
        rotation_degrees = 28.000  # This is the rotation of UBC's roads relative to true north.
        # After converting lat/lon to metres and subtracting the offset, the roads are rotated 28 degrees clockwise.
        rotation = math.radians(rotation_degrees)
        inverse_rotation_matrix = np.array([[math.cos(rotation), math.sin(rotation), 0],
                                            [-math.sin(rotation), math.cos(rotation), 0],
                                            [0, 0, 1]])
        x, z = coords
        x = x - x_offset
        z = z - z_offset
        x, z, _ = np.matmul(inverse_rotation_matrix, np.array([x, z, 0]))
        z = -z
        y = get_height(x, z, level)
        place_streetlight(level, x, y, z, layer)
    level.save()
    level.close()


def get_height(x, z, level):
    """
    This function determines the height of the terrain at the given x and z coordinates.
    :param x: x coordinate
    :param z: z coordinate
    :param level: amulet level object
    :return: height of the terrain at the given coordinates
    """
    # get the chunk coordinates
    chunk_x, chunk_z = block_coords_to_chunk_coords(x, z)

    # get the chunk
    chunk = level.get_chunk(chunk_x, chunk_z, "minecraft:overworld")

    # get the block coordinates
    block_x = math.floor(x % 16)
    block_z = math.floor(z % 16)

    # get the height of the terrain at the given coordinates
    for y in range(max_height, min_height, -1):
        block = chunk.blocks[block_x, y, block_z]
        if block == 0:
            continue
        else:
            return y
    return None


def place_streetlight(level, x, y, z, layer):
    """
    This function places the streetlight in the world dependent on the LAYER attribute of the feature.
    :param level: amulet level object
    :param x: x coordinate
    :param y: y coordinate
    :param z: z coordinate
    :param layer: LAYER attribute of the feature
    :return: None
    """
    # get the streetlight configuration
    streetlight = LAYER_conversion[layer]

    # place the streetlight
    for i, block in enumerate(streetlight):
        level.set_version_block(int(x), int(y) + i + 1, int(z), "minecraft:overworld", game_version, block)


if __name__ == "__main__":
    streetlight_handler()
