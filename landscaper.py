"""
This script iterates through the polygons defined in the geojson file, voxelizes them through polygon_divider.py, and
utilizes various attributes of the feature to place blocks in the world.
"""
import json
import random

import amulet
import numpy as np
from amulet import Block
from amulet.api.errors import ChunkDoesNotExist
from tqdm import tqdm

from polygon_divider import polygon_divider
from amulet.utils import block_coords_to_chunk_coords
import sidewalk_placer
import streetlight_handler

min_height = -63
max_height = 45
game_version = ("java", (1, 19, 4))
default_block = Block("minecraft", "stone")

LSHARD_TYPE_conversion = {
    "Concrete": {
        "block": Block("minecraft", "gray_concrete_powder"),
        "depth": 2,
    },
    "Road": {
        "block": Block("minecraft", "gray_concrete_powder"),
        "depth": 2,
    },
    "Pedestrian": {
        "block": Block("minecraft", "andesite"),
        "depth": 2,
    },
    "Parking": {
        "block": Block("minecraft", "gray_concrete"),
        "depth": 1,
    },
    "Driveway": {
        "block": Block("minecraft", "gray_concrete"),
        "depth": 1,
    },
}

LSSOFT_TYPE_conversion = {
    "Wild": {
        "block": random.choices(
            [Block("minecraft", "moss_block"), Block("minecraft", "dirt"), Block("minecraft", "grass_block")],
            weights=[0.7, 0.2, 0.1],
            k=1
        )[0],
        "depth": 3,
    },
    "PlantingBed": {
        "block": Block("minecraft", "moss_block"),
        "depth": 1,
    },
    "OSPlantingBed": {
        "block": Block("minecraft", "moss_block"),
        "depth": 1,
    },
    "Lawn": {
        "block": Block("minecraft", "grass_block"),
        "depth": 2,
    },
    "Garden": {
        "block": random.choices(
            [Block("minecraft", "dirt"), Block("minecraft", "coarse_dirt")],
            weights=[0.7, 0.3],
            k=1
        )[0],
        "depth": 1,
    },
    "Field": {
        "block": Block("minecraft", "grass_block"),
        "depth": 2,
    },
    "Farm": {
        "block": Block("minecraft", "farmland"),
        "depth": 1,
    },
    "Crop": {
        "block": Block("minecraft", "farmland"),
        "depth": 1,
    }
}

FID_LANDUS_conversion = {
    "ROAD": {
        "block": Block("minecraft", "gray_concrete_powder"),
        "depth": 2,
    },
    "BLDG": {  # This is the space that the buildings are but not actually the buildings themselves
        "block": Block("minecraft", "grass_block"),  # most of the space are lawns
        "depth": 2,
    },
    "GRASS": {  # This is where the golf course is
        "block": Block("minecraft", "grass_block"),
        "depth": 2,
    },
}


def convert_feature(feature, level, landscape_type, block_override=None, depth_override=None):
    # if the geometry type is a polygon, that's fine
    try:
        if feature["geometry"]["type"] == "Polygon":
            coordinates, properties = feature["geometry"]["coordinates"], feature["properties"]
            # get the ls type
            geometry_handler(block_override, coordinates, depth_override, landscape_type, level, properties)
        elif feature["geometry"]["type"] == "MultiPolygon":
            coordinates, properties = feature["geometry"]["coordinates"], feature["properties"]
            for polygon in coordinates:
                geometry_handler(block_override, polygon, depth_override, landscape_type, level, properties)
        else:
            raise TypeError("Invalid geometry type")
    except TypeError:
        print(feature)


def geometry_handler(block_override, coordinates, depth_override, landscape_type, level, properties):
    if landscape_type == "uel":
        if properties["FID_LANDUS"] == "IGNORE":
            return

    # get the flooded matrix
    matrix, min_x, min_z = polygon_divider(coordinates)
    for cx in range(0, matrix.shape[0], 16):
        for cz in range(0, matrix.shape[1], 16):
            matrix_slice = matrix[cx:cx + 16, cz:cz + 16]
            # if the matrix slide is all 0, skip it
            if np.all(matrix_slice == 0):
                continue
            # if it's not exactly 16 by 16, pad on the right and bottom
            if matrix_slice.shape != (16, 16):
                matrix_slice = np.pad(matrix_slice, ((0, 16 - matrix_slice.shape[0]), (0, 16 - matrix_slice.shape[1])))
            chunk_x, chunk_z = block_coords_to_chunk_coords(cx + min_x, cz + min_z)
            try:
                chunk = level.get_chunk(chunk_x, chunk_z, "minecraft:overworld")
                blocks = chunk.blocks
                if blocks is None:
                    continue

                universal_default_block, _, _ = level.translation_manager.get_version("java",
                                                                                      (1, 19, 4)).block.to_universal(
                    default_block)
                default_block_id = level.block_palette.get_add_block(universal_default_block)
                for x in range(16):
                    for z in range(16):
                        if matrix_slice[x, z]:
                            try:
                                block, depth = get_block_type(block_override, depth_override, landscape_type,
                                                              properties)
                                universal_block, _, _ = level.translation_manager.get_version("java", (
                                    1, 19, 4)).block.to_universal(block)
                                block_id = level.block_palette.get_add_block(universal_block)
                                height = min_height + np.max(np.where(blocks[x, min_height:, z] == default_block_id))
                                chunk.blocks[x, int(height - depth):int(height) + depth, z] = block_id
                            except ValueError:
                                pass
                level.put_chunk(chunk, "minecraft:overworld")
                chunk.changed = True
            except ChunkDoesNotExist:
                continue


def get_block_type(block_override, depth_override, landscape_type, properties):
    if landscape_type == "hard":
        ls_type = properties["LSHARD_TYPE"]
        block, depth = LSHARD_TYPE_conversion[ls_type]["block"], LSHARD_TYPE_conversion[ls_type]["depth"]
    elif landscape_type == "soft":
        ls_type = properties["LSSOFT_TYPE"]
        block, depth = LSSOFT_TYPE_conversion[ls_type]["block"], LSSOFT_TYPE_conversion[ls_type]["depth"]
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
        if properties["FID_LANDUS"] == "IGNORE":
            raise ValueError("This should have been caught earlier")
        block, depth = FID_LANDUS_conversion[properties["FID_LANDUS"]]["block"], \
            FID_LANDUS_conversion[properties["FID_LANDUS"]]["depth"]
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
    failed_features = []
    for feature in tqdm(features):
        try:
            convert_feature(feature, level, landscape_type, block_override, depth_override)
        except ValueError:
            pass
        #     failed_features.append(feature)
    return failed_features


def convert_features_from_file(file, level, landscape_type, block_override=None, depth_override=None):
    with open(file, "r") as f:
        features = json.load(f)
    features = features["features"]
    failed = convert_features(features, level, landscape_type, block_override, depth_override)
    # write failed to a file
    with open(file + ".failed", "w") as f:
        json.dump(failed, f)


def main():
    files = [
        "resources/geojson_ubcv/landscape/geojson/ubcv_landscape_soft.geojson",
        "resources/geojson_ubcv/landscape/geojson/ubcv_landscape_hard.geojson",
        "resources/geojson_ubcv/landscape/geojson/ubcv_municipal_waterfeatures.geojson",
        "resources/geojson_ubcv/context/geojson/ubcv_beach.geojson",
        "resources/geojson_ubcv/context/geojson/ubcv_psrp.geojson",
        "resources/geojson_ubcv/context/geojson/ubcv_uel.geojson"
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
        level = amulet.load_level("world/UBC")
        convert_features_from_file(file, level, landscape_type)
        print(f"Finished {landscape_type}")
        level.save()
        level.close()
        print("Saved")


if __name__ == "__main__":
    main()
    sidewalk_placer.main()
    streetlight_handler.streetlight_handler()
