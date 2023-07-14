"""
This script removes any tree trunks that intersect a hard landscaping feature. This removes most of the incorrectly
placed trunks on campus.
"""

import json

import amulet
import numpy as np
from amulet import Block
from amulet.api.errors import ChunkDoesNotExist
from amulet.utils import block_coords_to_chunk_coords
from tqdm import tqdm

from scripts.geojson.polygon_divider import polygon_divider

trunk_block = Block("minecraft", "spruce_log")

min_height = -64
max_height = 100


def convert_feature(feature, level, trunk_block_id):
    # if the geometry type is a polygon, that's fine
    try:
        if feature["geometry"]["type"] == "Polygon":
            coordinates, properties = feature["geometry"]["coordinates"], feature["properties"]
            # get the ls type
            geometry_handler(coordinates, level, trunk_block_id)
        elif feature["geometry"]["type"] == "MultiPolygon":
            coordinates, properties = feature["geometry"]["coordinates"], feature["properties"]
            for polygon in coordinates:
                geometry_handler(polygon, level, trunk_block_id)
        else:
            raise TypeError("Invalid geometry type")
    except TypeError:
        print(feature)


def geometry_handler(coordinates, level, trunk_block_id):
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
                                column = chunk.blocks[x, min_height:max_height, z]
                                np.array(column).flatten()
                                trunk_block_indices = np.where(column == trunk_block_id)
                                if len(trunk_block_indices[1]) > 0:
                                    indices_to_replace = trunk_block_indices[1] + min_height
                                    for index in indices_to_replace:
                                        chunk.blocks[x, index, z] = 0
                            except ValueError:
                                pass
                chunk.changed = True
            except ChunkDoesNotExist:
                continue


def convert_features(features, level, trunk_block_id):
    failed_features = []
    for feature in tqdm(features):
        try:
            convert_feature(feature, level, trunk_block_id)
        except ValueError:
            pass
        #     failed_features.append(feature)
    return failed_features


def convert_features_from_file(file, level):
    trunk_block_universal, _, _ = level.translation_manager.get_version("java", (1, 19, 4)).block.to_universal(
        trunk_block)
    trunk_block_id = level.block_palette.get_add_block(trunk_block_universal)
    with open(file, "r") as f:
        features = json.load(f)
    features = features["features"]
    failed = convert_features(features, level, trunk_block_id)
    # write failed to a file
    with open(file + ".failed", "w") as f:
        json.dump(failed, f)


def main():
    file = r"C:\Users\Ashtan\OneDrive - UBC\School\2023S\minecraftUBC\resources\geojson_ubcv\landscape\geojson\ubcv_landscape_hard.geojson"
    level = amulet.load_level(r"C:\Users\Ashtan\OneDrive - UBC\School\2023S\minecraftUBC\world\UBC")
    convert_features_from_file(file, level)
    print(f"Finished removing trees in hard landscaping")
    level.save()
    level.close()
    print("Saved")


if __name__ == "__main__":
    main()
