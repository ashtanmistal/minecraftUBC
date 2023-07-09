import math
import os
import time

import amulet
import numpy as np
import pylas
from PIL import Image
from amulet.api.block import Block
from amulet.utils.world_utils import block_coords_to_chunk_coords, chunk_coords_to_block_coords
from amulet_nbt import StringTag
from tqdm import tqdm

game_version = ("java", (1, 19, 4))

x_offset = 480000
y_offset = 5455000
z_offset = 59

blocks = {
    "bricks": Block("minecraft", "bricks"),
    "stone bricks": Block("minecraft", "stone_bricks"),
    "iron_block": Block("minecraft", "iron_block"),
    "deepslate tiles": Block("minecraft", "deepslate_tiles"),
}

rotation_degrees = 28.000
rotation = math.radians(rotation_degrees)
inverse_rotation_matrix = np.array([[math.cos(rotation), math.sin(rotation), 0],
                                    [-math.sin(rotation), math.cos(rotation), 0],
                                    [0, 0, 1]])

texture_location = "resources/block"


def get_average_rgb(block_object):
    texture = Image.open(texture_location + "/" + block_object.base_name + ".png").convert("RGB")

    return texture.resize((1, 1), resample=Image.BILINEAR).getpixel((0, 0))


block_textures = {
    block: get_average_rgb(block_object)
    for block, block_object in blocks.items()
}


def transform_chunk(data, level):
    """
    This transforms a slice of LiDAR data that is particular to a given chunk, estimates the best block to place for a
    given square meter, and places it.
    :param data: The LiDAR data to transform
    :param level: Amulet level object
    :return: None
    """
    x, y, z, red, green, blue = data
    if len(x) == 0 or len(y) == 0 or len(z) == 0:
        return
    # x, y, z = np.round(x).astype(int), np.round(y).astype(int), np.round(z).astype(int)

    # now we need to group the data into meter sized cubes
    unique_x, x_indices = np.unique(x, return_index=True)
    unique_y, y_indices = np.unique(y, return_index=True)
    unique_z, z_indices = np.unique(z, return_index=True)
    cx, cz = block_coords_to_chunk_coords(unique_x[0], unique_z[0])
    chunk = level.get_chunk(cx, cz, "minecraft:overworld")

    for i, j, k in np.ndindex(len(unique_x), len(unique_y), len(unique_z)):
        matching_indices = np.where((x == unique_x[i]) & (y == unique_y[j]) & (z == unique_z[k]))
        offset_x, offset_z = unique_x[i] - cx * 16, unique_z[k] - cz * 16
        if matching_indices[0].size == 0 or chunk.blocks[int(offset_x), int(unique_y[j]), int(offset_z)] != 0:
            continue
        # now we have all the points that are in the same meter cube
        # we need to find the average color, but this time we'll normalize the color to get rid of shadows
        # this average color will be matched to a block from the selection above
        average_color = np.mean(np.array([red[matching_indices], green[matching_indices], blue[matching_indices]]),
                                axis=1)
        mapped_color = min(block_textures, key=lambda b: np.linalg.norm(block_textures[b] - average_color))
        mapped_block = blocks[mapped_color]

        universal_block, universal_block_entity, universal_extra = level.translation_manager.get_version("java", (
            1, 19, 4)).block.to_universal(mapped_block)
        block_id = level.block_palette.get_add_block(universal_block)
        chunk.blocks[int(offset_x), int(unique_y[j]), int(offset_z)] = block_id
    chunk.changed = True


def transform_dataset(ds):
    level = amulet.load_level("world/UBC")
    x, y, z, r, g, b, c = ds.x, ds.y, ds.z, ds.red, ds.green, ds.blue, ds.classification
    x, y, z = np.matmul(inverse_rotation_matrix, np.array([x - x_offset, y - y_offset, z - z_offset]))
    r, g, b = (r / 256).astype(int), (g / 256).astype(int), (b / 256).astype(int)
    z, y = y, z  # translating from lidar coordinates to minecraft coordinates
    indices = np.where((y < 256) & (y >= -64) & (c == 6))
    if len(indices[0]) == 0:
        return
    x, y, z, r, g, b = x[indices], y[indices], z[indices], r[indices], g[indices], b[indices]
    z = -z
    min_x, min_y, min_z = np.floor(np.min(x)), np.floor(np.min(y)), np.floor(np.min(z))
    max_x, max_y, max_z = np.ceil(np.max(x)), np.ceil(np.max(y)), np.ceil(np.max(z))
    # round all the points to the nearest meter
    x, y, z = np.round(x).astype(int), np.round(y).astype(int), np.round(z).astype(int)
    # round to nearest chunk
    min_x, min_z = min_x - min_x % 16, min_z - min_z % 16
    max_x, max_z = max_x - max_x % 16, max_z - max_z % 16
    for cx in tqdm(range(min_x.astype(int), max_x.astype(int), 16)):
        for cz in range(min_z.astype(int), max_z.astype(int), 16):
            chunk_indices = np.where((x >= cx) & (x < cx + 16) & (z >= cz) & (z < cz + 16))
            chunk_data = np.array(
                [x[chunk_indices], y[chunk_indices], z[chunk_indices], r[chunk_indices], g[chunk_indices],
                 b[chunk_indices]])
            transform_chunk(chunk_data, level)
    level.save()
    level.close()


if __name__ == "__main__":
    start_time = time.time()
    lidar_dir = "LiDAR LAS Data/las"
    for filename in os.listdir(lidar_dir):
        if filename.endswith(".las"):
            dataset = pylas.read(os.path.join(lidar_dir, filename))
            print("transforming chunks for", filename, time.time() - start_time)
            transform_dataset(dataset)
            print("done transforming chunks for", filename, time.time() - start_time)
