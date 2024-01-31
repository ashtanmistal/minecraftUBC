"""
This script removes any tree trunks that intersect a hard landscaping feature. This removes most of the incorrectly
placed trunks on campus.
"""

import json
import os

import amulet
import numpy as np
from amulet.api.errors import ChunkDoesNotExist
from amulet.utils import block_coords_to_chunk_coords
from tqdm import tqdm

import src.helpers
from src.geojson.polygon_divider import polygon_divider
from src.lidar.tree_trunk_placer import TRUNK_BLOCK

LANDSCAPE_HARD_FILE = os.path.join(src.helpers.PROJECT_DIRECTORY,
                                   r"resources\geojson_ubcv\landscape\geojson\ubcv_landscape_hard.geojson")


def convert_feature(feature, level, trunk_block_id):
    """
    Calls the geometry handler on a feature. If the feature is a multipolygon, it will call the geometry handler on each
    polygon.
    :param feature: geojson feature to convert
    :param level: Amulet level object
    :param trunk_block_id: ID of the trunk block
    :return: None
    """
    try:
        if feature["geometry"]["type"] == "Polygon":
            coordinates, properties = feature["geometry"]["coordinates"], feature["properties"]
            geometry_handler(coordinates, level, trunk_block_id)
        elif feature["geometry"]["type"] == "MultiPolygon":
            # if it's a multipolygon, we need to iterate through each polygon
            coordinates, properties = feature["geometry"]["coordinates"], feature["properties"]
            for polygon in coordinates:
                geometry_handler(polygon, level, trunk_block_id)
        else:
            raise TypeError("Invalid geometry type")
    except TypeError:
        print(feature)


def geometry_handler(coordinates, level, trunk_block_id):
    """
    Converts a polygon to a numpy array and then iterates through each chunk in the polygon, replacing any intersecting
    tree trunks with air.
    :param coordinates: coordinates of the polygon
    :param level: Amulet level object
    :param trunk_block_id: ID of the trunk block to replace
    :return: None
    """
    matrix, min_x, min_z = polygon_divider(coordinates)
    for cx in range(0, matrix.shape[0], 16):
        for cz in range(0, matrix.shape[1], 16):
            matrix_slice = matrix[cx:cx + 16, cz:cz + 16]

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

                for x in range(16):
                    for z in range(16):
                        if matrix_slice[x, z]:
                            try:
                                # see if there are any trunk blocks in this column
                                # If there are, replace them with air
                                column = chunk.blocks[x, src.helpers.MIN_HEIGHT:src.helpers.MAX_HEIGHT, z]
                                np.array(column).flatten()
                                trunk_block_indices = np.where(column == trunk_block_id)
                                if len(trunk_block_indices[1]) > 0:
                                    indices_to_replace = trunk_block_indices[1] + src.helpers.MIN_HEIGHT
                                    for index in indices_to_replace:
                                        chunk.blocks[x, index, z] = 0
                            except ValueError:
                                pass
                chunk.changed = True
            except ChunkDoesNotExist:
                continue


def convert_features(features, level, trunk_block_id):
    """
    Calls the convert_feature function on each feature in the list. If the feature fails to convert, it will be skipped.
    :param features:
    :param level:
    :param trunk_block_id:
    :return:
    """
    for feature in tqdm(features):
        try:
            convert_feature(feature, level, trunk_block_id)
        except ValueError:
            pass


def convert_features_from_file(file, level):
    """
    Loads the features from a file and calls the convert_features function on them.
    :param file: the file to load the features from
    :param level: Amulet level object
    :return: None
    """
    trunk_block_universal, _, _ = level.translation_manager.get_version("java", (1, 20, 4)).block.to_universal(
        TRUNK_BLOCK)
    trunk_block_id = level.block_palette.get_add_block(trunk_block_universal)
    with open(file, "r") as f:
        features = json.load(f)
    features = features["features"]
    convert_features(features, level, trunk_block_id)


def main():
    """
    Main function. Loads the level, converts the features, and saves the level.
    :return: None
    """
    level = amulet.load_level(src.helpers.WORLD_DIRECTORY)
    convert_features_from_file(LANDSCAPE_HARD_FILE, level)
    print(f"Finished removing trees in hard landscaping")
    level.save()
    level.close()
    print("Saved")


if __name__ == "__main__":
    main()
