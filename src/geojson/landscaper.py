"""
This script iterates through the polygons defined in the geojson file, voxelizes them through polygon_divider.py, and
utilizes various attributes of the feature to place blocks in the world.
"""
import amulet
import json
import numpy as np
import os
import random
from amulet import Block
from amulet.api.errors import ChunkDoesNotExist
from amulet.utils import block_coords_to_chunk_coords
from tqdm import tqdm
from rasterio.features import rasterize
import shapely.geometry

import src.helpers
from src.geojson import streetlight_handler, sidewalk_placer
from src.geojson.polygon_divider import polygon_divider

MIN_HEIGHT = -63
MAX_HEIGHT = 50
DEFAULT_BLOCK = Block("minecraft", "stone")

# TODO remove Block from the type conversions and just use the color and the color-to-block dictionary for consistency
LSHARD_TYPE_CONVERSION = {
    "Concrete": {
        "block": Block("minecraft", "gray_concrete_powder"),
        "color": "#808080",  # This is the color used in the rasterization (and thus as a mapping from color -> block)
        "depth": 2,
    },
    "Road": {
        "block": Block("minecraft", "gray_concrete_powder"),
        "color": "#808080",
        "depth": 2,
    },
    "Pedestrian": {
        "block": Block("minecraft", "andesite"),
        "color": "#aaaaaa",
        "depth": 2,
    },
    "Parking": {
        "block": Block("minecraft", "gray_concrete"),
        "color": "#6a6a6a",
        "depth": 1,
    },
    "Driveway": {
        "block": Block("minecraft", "gray_concrete"),
        "color": "#6a6a6a",
        "depth": 1,
    },
}

LSSOFT_TYPE_CONVERSION = {
    "Wild": {
        "block": random.choices(
            [Block("minecraft", "moss_block"), Block("minecraft", "dirt"), Block("minecraft", "grass_block")],
            weights=[0.7, 0.2, 0.1],
            k=1
        )[0],
        "color": "#007600",
        "depth": 3,
    },
    "PlantingBed": {
        "block": Block("minecraft", "moss_block"),
        "color": "#00c900",
        "depth": 1,
    },
    "OSPlantingBed": {
        "block": Block("minecraft", "moss_block"),
        "color": "#00c900",
        "depth": 1,
    },
    "Lawn": {
        "block": Block("minecraft", "grass_block"),
        "color": "#00a500",
        "depth": 2,
    },
    "Garden": {
        "block": random.choices(
            [Block("minecraft", "dirt"), Block("minecraft", "coarse_dirt")],
            weights=[0.7, 0.3],
            k=1
        )[0],
        "color": "#9b6127",
        "depth": 1,
    },
    "Field": {
        "block": Block("minecraft", "grass_block"),
        "color": "#00a500",
        "depth": 2,
    },
    "Farm": {
        "block": Block("minecraft", "farmland"),
        "color": "#a4591d",
        "depth": 1,
    },
    "Crop": {
        "block": Block("minecraft", "farmland"),
        "color": "#a4591d",
        "depth": 1,
    }
}

FID_LANDUS_CONVERSION = {
    "ROAD": {
        "block": Block("minecraft", "gray_concrete_powder"),
        "color": "#808080",
        "depth": 2,
    },
    "BLDG": {  # This is the space that the buildings are but not actually the buildings themselves
        "block": Block("minecraft", "grass_block"),  # most of the space are lawns
        "color": "#00a500",
        "depth": 2,
    },
    "GRASS": {  # This is where the golf course is
        "block": Block("minecraft", "grass_block"),
        "color": "#00a500",
        "depth": 2,
    },
}

BUILDING_CONVERSION = {
    # This needs to be visually distinct from the rest of the landscape bus still make sense as a building floor
    "block": Block("minecraft", "oak_planks"),
    "color": "#fcd46e",
    "depth": 1,
}

WATER_CONVERSION = {
    "block": Block("minecraft", "water"),
    "color": "#0000ff",
    "depth": 1,
}

BEACH_CONVERSION = {
    "block": Block("minecraft", "sand"),
    "color": "#ffff00",
    "depth": 2,
}

PSRP_CONVERSION = {
    "block": random.choices(
        [Block("minecraft", "moss_block"),
         Block("minecraft", "dirt"),
         Block("minecraft", "grass_block"),
         Block("minecraft", "coarse_dirt")],
        weights=[0.6, 0.2, 0.15, 0.05],
        k=1
    )[0],
    "color": "#28872f",
    "depth": 2,
}

COLOR_TO_BLOCK = {
    "#808080": Block("minecraft", "gray_concrete_powder"),
    "#aaaaaa": Block("minecraft", "andesite"),
    "#6a6a6a": Block("minecraft", "gray_concrete"),
    "#007600": Block("minecraft", "moss_block"),
    "#00c900": Block("minecraft", "moss_block"),
    "#00a500": Block("minecraft", "grass_block"),
    "#9b6127": Block("minecraft", "dirt"),
    "#a4591d": Block("minecraft", "farmland"),
    "#fcd46e": Block("minecraft", "oak_planks"),
    "#0000ff": Block("minecraft", "water"),
    "#ffff00": Block("minecraft", "sand"),
    "#28872f": Block("minecraft", "moss_block"),
}

COLOR_TO_DEPTH = {
    "#808080": 2,
    "#aaaaaa": 2,
    "#6a6a6a": 1,
    "#007600": 3,
    "#00c900": 1,
    "#00a500": 2,
    "#9b6127": 1,
    "#a4591d": 1,
    "#fcd46e": 1,
    "#0000ff": 1,
    "#ffff00": 2,
    "#28872f": 2,
}


def convert_feature(feature, level, landscape_type, block_override=None, depth_override=None):
    """
    This function takes a feature from the geojson file and converts it into blocks in the world.
    :param feature: Geojson feature object
    :param level: Amulet level object
    :param landscape_type: Type of landscape to convert
    :param block_override: Manual override of the block to place instead of the feature default conversion
    :param depth_override: Manual override of the depth to place instead of the feature default conversion
    :return: None
    """
    if feature["geometry"] is None:
        return
    if feature["geometry"]["type"] == "Polygon":
        coordinates, properties = feature["geometry"]["coordinates"], feature["properties"]
        geometry_handler(block_override, coordinates, depth_override, landscape_type, level, properties)
    elif feature["geometry"]["type"] == "MultiPolygon":
        coordinates, properties = feature["geometry"]["coordinates"], feature["properties"]
        for polygon in coordinates:
            geometry_handler(block_override, polygon, depth_override, landscape_type, level, properties)
    else:
        raise TypeError("Invalid geometry type")


def geometry_handler(block_override, coordinates, depth_override, landscape_type, level, properties):
    """
    This function takes a polygon and converts it into blocks in the Minecraft world.
    :param block_override: manual override of the block to place instead of the feature default conversion
    :param coordinates: Vertices of the polygon
    :param depth_override: manual override of block depth
    :param landscape_type: Type of landscape to convert
    :param level: Amulet level object
    :param properties: Properties of the feature - this was manually entered into the json for features we wanted to
    ignore in the UEL landscape
    :return: None
    """
    if landscape_type == "uel":
        if properties["FID_LANDUS"] == "IGNORE":
            return

    universal_default_block, _, _ = level.translation_manager.get_version("java",
                                                                          (1, 20, 4)).block.to_universal(
        DEFAULT_BLOCK)
    default_block_id = level.block_palette.get_add_block(universal_default_block)

    # get the flooded matrix
    matrix, min_x, min_z = polygon_divider(coordinates)  # TODO see if this can be replaced with a rasterization library
    for cx in range(0, matrix.shape[0], 16):
        for cz in range(0, matrix.shape[1], 16):
            matrix_slice = matrix[cx:cx + 16, cz:cz + 16]
            if np.all(matrix_slice == 0):
                continue
            if matrix_slice.shape != (16, 16):
                matrix_slice = np.pad(matrix_slice, ((0, 16 - matrix_slice.shape[0]), (0, 16 - matrix_slice.shape[1])))
            chunk_x, chunk_z = block_coords_to_chunk_coords(cx + min_x, cz + min_z)
            try:
                chunk = level.get_chunk(chunk_x, chunk_z, "minecraft:overworld")
                blocks = chunk.blocks
                if blocks is None:
                    continue
                for x in range(16):
                    for z in range(16):
                        if matrix_slice[x, z]:
                            try:
                                block, depth = get_block_type(block_override, depth_override, landscape_type,
                                                              properties)
                                universal_block, _, _ = level.translation_manager.get_version("java", (
                                    1, 20, 4)).block.to_universal(block)
                                block_id = level.block_palette.get_add_block(universal_block)
                                height = MIN_HEIGHT + np.max(np.where(blocks[x, MIN_HEIGHT:, z] == default_block_id))
                                chunk.blocks[x, int(height - depth):int(height) + depth, z] = block_id
                            except ValueError:
                                pass
                level.put_chunk(chunk, "minecraft:overworld")
                chunk.changed = True
            except ChunkDoesNotExist:
                continue


def get_block_type(block_override, depth_override, landscape_type, properties):
    """
    Converts the landscape type to a block and depth
    :param block_override: Manual override of default block conversion
    :param depth_override: Manual override of default depth conversion
    :param landscape_type: Type of landscape to convert
    :param properties: Properties of the feature
    :return: None
    """
    # TODO this function ought to be a constant dictionary lookup
    if landscape_type == "hard":
        ls_type = properties["LSHARD_TYPE"]
        block, depth = LSHARD_TYPE_CONVERSION[ls_type]["block"], LSHARD_TYPE_CONVERSION[ls_type]["depth"]
    elif landscape_type == "soft":
        ls_type = properties["LSSOFT_TYPE"]
        block, depth = LSSOFT_TYPE_CONVERSION[ls_type]["block"], LSSOFT_TYPE_CONVERSION[ls_type]["depth"]
    elif landscape_type == "beach":
        block = random.choices(
            [Block("minecraft", "sand"), Block("minecraft", "sandstone")],
            weights=[0.7, 0.3],
            k=1
        )[0]
        depth = 2
    elif landscape_type == "water":
        block = Block("minecraft", "water")
        depth = 1
    elif landscape_type == "psrp":
        block = random.choices(
            [Block("minecraft", "moss_block"),
             Block("minecraft", "dirt"),
             Block("minecraft", "grass_block"),
             Block("minecraft", "coarse_dirt")],
            weights=[0.6, 0.2, 0.15, 0.05],
            k=1
        )[0]
        depth = 2
    elif landscape_type == "uel":
        block, depth = FID_LANDUS_CONVERSION[properties["FID_LANDUS"]]["block"], \
            FID_LANDUS_CONVERSION[properties["FID_LANDUS"]]["depth"]
    else:
        raise ValueError("Invalid landscape type")
    if block_override is not None:
        block = block_override
        if depth_override is not None:
            depth = depth_override
        else:
            raise ValueError("If block_override is not None, depth_override must also be not None")
    else:
        if depth_override is not None:
            depth = depth_override  # it's okay to have a depth override without a block override

    return block, depth


def convert_features(features, level, landscape_type, block_override=None, depth_override=None):
    """
    Converts a list of features into blocks in the Minecraft world
    :param features: List of features to convert
    :param level: Amulet level object
    :param landscape_type: Type of landscape to convert
    :param block_override: manual block override
    :param depth_override: manual depth override
    :return: None
    """
    for feature in tqdm(features):
        try:
            convert_feature(feature, level, landscape_type, block_override, depth_override)
        except ValueError:
            pass


def convert_features_from_file(file, level, landscape_type, block_override=None, depth_override=None):
    """
    Loads a json file and places corresponding blocks in the Minecraft world
    :param file: string path to json file
    :param level: Amulet level object
    :param landscape_type: Type of landscape to convert
    :param block_override: Manual block override
    :param depth_override: Manual depth override
    :return: None
    """
    with open(file, "r") as f:
        features = json.load(f)
    convert_features(features["features"], level, landscape_type, block_override, depth_override)


def main():
    """
    Main function to convert all the geojson files into blocks in the Minecraft world
    :return: None
    """
    geojson_directory = os.path.join(src.helpers.PROJECT_DIRECTORY, "resources", "geojson_ubcv")
    files = [
        os.path.join(geojson_directory, "landscape", "geojson", "ubcv_landscape_soft.geojson"),
        os.path.join(geojson_directory, "landscape", "geojson", "ubcv_landscape_hard.geojson"),
        os.path.join(geojson_directory, "landscape", "geojson", "ubcv_municipal_waterfeatures.geojson"),
        os.path.join(geojson_directory, "context", "geojson", "ubcv_beach.geojson"),
        os.path.join(geojson_directory, "context", "geojson", "ubcv_psrp.geojson"),
        os.path.join(geojson_directory, "context", "geojson", "ubcv_uel.geojson")
    ]
    landscape_types = [
        "soft",
        "hard",
        "water",
        "beach",
        "psrp",
        "uel"
    ]
    for file, landscape_type in zip(files, landscape_types):
        level = amulet.load_level(src.helpers.WORLD_DIRECTORY)
        convert_features_from_file(file, level, landscape_type)
        print(f"Finished {landscape_type}")
        level.save()
        level.close()
        print("Saved")
