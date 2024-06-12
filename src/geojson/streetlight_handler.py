"""
This script handles the streetlight geojson file, which contains the location of streetlights in the landscape.
The data is given in EPSG:26910 (UTM zone 10N) coordinates, so it is converted to the Minecraft coordinate system
by adjusting the offsets and applying the rotation matrix. After, the terrain height is determined and the preset
streetlight configuration is placed in the world dependent on the LAYER attribute of the feature.
"""

import json
import math
import os

import amulet
import numpy as np
from amulet import Block
from amulet.utils import block_coords_to_chunk_coords
from amulet_nbt import StringTag
from tqdm import tqdm
from src.helpers import WORLD_DIRECTORY, PROJECT_DIRECTORY

import src.helpers

STREETLIGHT_JSON_PATH = os.path.join(src.helpers.PROJECT_DIRECTORY, "resources", "streetlights_json.geojson")

MIN_HEIGHT = -20
MAX_HEIGHT = 45

STANDARD_LIGHT_CONFIGURATION = [
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

BOLLARD_LIGHT_CONFIGURATION = [
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "lantern")
]

TALL_LIGHT_CONFIGURATION = [
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

LAYER_CONVERSION = {
    "E-LITE-BOLLARD": BOLLARD_LIGHT_CONFIGURATION,
    "E-LITE-POLE_LAMP": TALL_LIGHT_CONFIGURATION,
    "E-LITE-STANDARD": STANDARD_LIGHT_CONFIGURATION,
    "E-LITE-STANDARD_LAMP": STANDARD_LIGHT_CONFIGURATION,
    "E-LITE-SYMB": STANDARD_LIGHT_CONFIGURATION
}


def streetlight_handler(world_directory):
    """
    This function handles the streetlight geojson file, which contains the location of streetlights in the landscape.
    The data is given in EPSG:26910 (UTM zone 10N) coordinates, so it is converted to the Minecraft coordinate system
    by adjusting the offsets and applying the rotation matrix. After, the terrain height is determined and the
    preset streetlight configuration is placed in the world dependent on the LAYER attribute of the feature.
    :return: None
    """
    # load the geojson file
    with open(STREETLIGHT_JSON_PATH) as f:
        data = json.load(f)

    level = amulet.load_level(world_directory)
    # iterate through the features
    for feature in tqdm(data["features"]):
        layer = feature["properties"]["LAYER"]
        coords = feature["geometry"]["coordinates"]
        coords_x, coords_z = coords
        x, z, _ = np.matmul(src.helpers.INVERSE_ROTATION_MATRIX,
                            np.array(
                                [coords_x - src.helpers.BLOCK_OFFSET_X, coords_z - src.helpers.BLOCK_OFFSET_Z,
                                 0]))
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
    for y in range(MAX_HEIGHT, MIN_HEIGHT, -1):
        block = chunk.blocks[block_x, y, block_z]
        if block == 0:
            continue
        else:
            return y

    return None  # no terrain found


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
    streetlight = LAYER_CONVERSION[layer]
    for i, block in enumerate(streetlight):
        level.set_version_block(int(x), int(y) + i + 1, int(z), "minecraft:overworld", src.helpers.GAME_VERSION,
                                block)


if __name__ == "__main__":
    streetlight_handler()
