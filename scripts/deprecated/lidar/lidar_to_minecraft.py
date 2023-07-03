# lidar_to_minecraft.py
# author: Ashtan Mistal
import math
import os
import time

import amulet
import numpy as np
import pylas
from PIL import Image
from amulet.api.block import Block
from amulet.api.chunk import Chunk
from amulet.api.errors import ChunkDoesNotExist, ChunkLoadError
from amulet.utils.world_utils import block_coords_to_chunk_coords
from amulet_nbt import StringTag
from tqdm import tqdm

# This is a simple Python script that transforms a chunk (16m x 16m) of data and transforms it into a Minecraft chunk.
# It processes the entire chunk but breaks it down into meter-by-meter blocks.

start_time = time.time()
game_version = ("java", (1, 19, 4))

# coordinates of whatever we want to set as 0,0
x_offset = 480000
y_offset = 5455000
z_offset = 59

allowed_blocks = {  # class 2. Looks like these are roads and stuff
    "dirt": Block("minecraft", "dirt"),
    "stone": Block("minecraft", "stone"),
    "moss block": Block("minecraft", "moss_block"),
}

allowed_vegetation = {  # class 3
    "moss block": Block("minecraft", "moss_block")  # only allowing moss as that doesn't allow for shadows to appear
}

allowed_trees = {  # class 5
    "oak leaves": Block("minecraft", "oak_leaves", {"persistent": StringTag("true")}),
    "spruce leaves": Block("minecraft", "spruce_leaves", {"persistent": StringTag("true")}),
    "birch leaves": Block("minecraft", "birch_leaves", {"persistent": StringTag("true")}),
}

allowed_building_blocks = {  # class 6
    "bricks": Block("minecraft", "bricks"),
    "block of iron": Block("minecraft", "iron_block"),
    "stone bricks": Block("minecraft", "stone_bricks"),
    "deepslate tiles": Block("minecraft", "deepslate_tiles"),
    "oak planks": Block("minecraft", "oak_planks"),
}

# next we need to get the textures for each Minecraft block, and get the average rgb value for each texture
texture_location = "resources/block"


def get_average_rgb(block_object):
    try:
        texture = Image.open(texture_location + "/" + block_object.base_name + ".png").convert("RGB")
    except FileNotFoundError:
        texture = Image.open(texture_location + "/" + block_object.base_name + "_top.png").convert("RGB")
        print("top texture used for", block_object.base_name)

    return texture.resize((1, 1), resample=Image.BILINEAR).getpixel((0, 0))


if __name__ == '__main__':
    allowed_blocks_texture = {block: get_average_rgb(block_object) for block, block_object in allowed_blocks.items()}
    allowed_vegetation_texture = {block: get_average_rgb(block_object) for block, block_object in
                                  allowed_vegetation.items()}
    allowed_trees_texture = {block: get_average_rgb(block_object) for block, block_object in allowed_trees.items()}
    allowed_building_blocks_texture = {block: get_average_rgb(block_object) for block, block_object in
                                       allowed_building_blocks.items()}
    print("done computing average rgb values for textures", time.time() - start_time)
    rotation_degrees = 28.000
    rotation = math.radians(rotation_degrees)
    inverse_rotation_matrix = np.array([[math.cos(rotation), math.sin(rotation), 0],
                                        [-math.sin(rotation), math.cos(rotation), 0],
                                        [0, 0, 1]])


def transform_chunk(data, level):
    # We will break it up into 16 1m x 1m "sticks" that span the entire chunk.
    # Whatever data is in that stick tells is what blocks to place in that stick.
    # as there's likely to be more than one block per stick, we want to place all of them.

    # Labels:
    # 1. unclassified; there looks to be enough classified data that we can ignore this and remove it
    # 2. we will want to color match
    # 3. Low vegetation
    # 5. High vegetation
    # 6. Buildings
    # 9. Noise

    x, y, z, red, green, blue, labels = data

    if len(x) == 0 or len(y) == 0 or len(z) == 0:
        return  # no need to save if there's no data
    x, y, z = np.floor(x), np.floor(y), np.floor(z)

    # now group together the data points that have the same x, y, and z coordinates
    # average the rgb values for each group
    # compare with the rgb values for each Minecraft block texture, and choose the closest one
    # place the block in the chunk

    unique_x, x_indices = np.unique(x, return_index=True)
    unique_y, y_indices = np.unique(y, return_index=True)
    unique_z, z_indices = np.unique(z, return_index=True)

    cx, cz = block_coords_to_chunk_coords(np.min(unique_x), np.min(unique_y))
    new_chunk = False
    try:
        chunk = level.get_chunk(cx, cz, "minecraft:overworld")
    except ChunkDoesNotExist:
        chunk = Chunk(cx, cz)
        new_chunk = True
    except ChunkLoadError:
        print("Chunk load error at", cx, cz)
        raise ChunkLoadError

    for i, j, k in np.ndindex(len(unique_x), len(unique_y), len(unique_z)):

        # For each unique x, y, z coordinate, we want to get the average rgb value for all the data points that have
        # that coordinate. Red, green, and blue are all one-dimensional arrays.
        matching_indices = np.where((x == unique_x[i]) & (y == unique_y[j]) & (z == unique_z[k]))
        if matching_indices[0].size == 0 or matching_indices[0].size == 1:
            continue  # removing sparse data points
        avg_red = np.average(red[matching_indices])
        avg_green = np.average(green[matching_indices])
        avg_blue = np.average(blue[matching_indices])
        avg_class = np.median(labels[matching_indices])  # the most common class in the group

        if avg_class == 2:
            mapped_texture = min(allowed_blocks_texture, key=lambda g: np.linalg.norm(
                allowed_blocks_texture[g] - np.array([avg_red, avg_green, avg_blue])))
            selected_block = allowed_blocks[mapped_texture]
        elif avg_class == 3:
            mapped_texture = min(allowed_vegetation_texture, key=lambda g: np.linalg.norm(
                allowed_vegetation_texture[g] - np.array([avg_red, avg_green, avg_blue])))
            selected_block = allowed_vegetation[mapped_texture]
        elif avg_class == 5:
            # de-noise the trees a bit. If the number of points is too small, then we should ignore it
            if matching_indices[0].size < 3:
                continue
            mapped_texture = min(allowed_trees_texture, key=lambda g: np.linalg.norm(
                allowed_trees_texture[g] - np.array([avg_red, avg_green, avg_blue])))
            selected_block = allowed_trees[mapped_texture]
        elif avg_class == 6:
            mapped_texture = min(allowed_building_blocks_texture, key=lambda g: np.linalg.norm(
                allowed_building_blocks_texture[g] - np.array(
                    [avg_red, avg_green, avg_blue])))
            selected_block = allowed_building_blocks[mapped_texture]
        else:
            selected_block = Block("minecraft", "air")
        # block_id = level.block_palette.get_add_block(selected_block)
        offset_x = unique_x[i] - 16 * cx
        offset_y = unique_y[j] - 16 * cz
        universal_block, universal_block_entity, universal_extra = level.translation_manager.get_version("java", (
            1, 19, 4)).block.to_universal(selected_block)
        block_id = level.block_palette.get_add_block(universal_block)
        chunk.blocks[offset_x.astype(int), unique_z[k].astype(int), offset_y.astype(int)] = block_id
    if new_chunk:
        level.put_chunk(chunk, "minecraft:overworld")
    chunk.changed = True
    # level.save()


def delete_indices(blue, green, labels, noise_indices, red, x, y, z):
    x, y, z = np.delete(x, noise_indices), np.delete(y, noise_indices), np.delete(z, noise_indices)
    red, green, blue = np.delete(red, noise_indices), np.delete(green, noise_indices), np.delete(blue, noise_indices)
    labels = np.delete(labels, noise_indices)
    return blue, green, labels, red, x, y, z


def perform_dataset_transformation(ds):
    level = amulet.load_level("../world/UBC")
    x, y, z, red, green, blue, labels = ds.x, ds.y, ds.z, ds.red, ds.green, ds.blue, ds.classification
    # denoise: remove all labels that are not 2, 3, 5, or 6
    noise_indices = np.where((labels == 1) | (labels == 9) | (labels == 7) | (labels == 4) | (labels == 8))
    blue, green, labels, red, x, y, z = delete_indices(blue, green, labels, noise_indices, red, x, y, z)
    # apply the inverse rotation matrix to the x and y coordinates, but first apply the offset
    x, y, z = x - x_offset, y - y_offset, z - z_offset

    print("Done denoising", time.time() - start_time)
    x, y, z = np.matmul(inverse_rotation_matrix, np.array([x, y, z]))

    print("done applying rotation matrix", time.time() - start_time)

    # convert rgb from 0-65535 to 0-255
    red, green, blue = (red / 256).astype(int), (green / 256).astype(int), (blue / 256).astype(int)

    # sort by x, then y, then z. the colors should be sorted in the same way.
    sort_indices = np.lexsort((z, y, x))
    x, y, z, red, green, blue, labels = x[sort_indices], y[sort_indices], z[sort_indices], red[sort_indices], green[
        sort_indices], \
        blue[sort_indices], labels[sort_indices]

    print("done sorting data", time.time() - start_time)

    # remove data points that are above 256m

    indices = np.where(z < 256)
    x, y, z, red, green, blue, labels = x[indices], y[indices], z[indices], red[indices], green[indices], \
        blue[indices], labels[indices]

    # the z axis (in Minecraft) was flipped last time, so we need to flip it back
    y = -y

    # next we need to iterate over these chunks.
    min_x, min_y, min_z = np.floor(np.min(x)), np.floor(np.min(y)), np.floor(np.min(z))
    max_x, max_y, max_z = np.ceil(np.max(x)), np.ceil(np.max(y)), np.ceil(np.max(z))

    # Next, the script that we will be using to transform the chunk into a Minecraft chunk.
    # Data will be passed in as an array of data points to be treated as LIDAR data.

    # now we need to iterate over the chunks. We'll do this by iterating over the x and y coordinates of the chunks

    # round min and max to the lower and upper 16s and set as integers (quantize to chunks to avoid setting multiple
    # chunks during a single operation)
    min_x, min_y, max_x, max_y = np.floor(min_x), np.floor(min_y), np.ceil(max_x), np.ceil(max_y)

    for cx in tqdm(range(min_x.astype(int), max_x.astype(int), 16)):
        for cy in range(min_y.astype(int), max_y.astype(int), 16):
            # get the data points that are in this chunk
            chunk_indices = np.where((x >= cx) & (x < cx + 16) & (y >= cy) & (y < cy + 16))
            chunk_data = np.array(
                [x[chunk_indices], y[chunk_indices], z[chunk_indices], red[chunk_indices], green[chunk_indices],
                 blue[chunk_indices], labels[chunk_indices]])
            transform_chunk(chunk_data, level)
    level.save()
    level.close()


finished_datasets = []
# finished_datasets = ["480000_5455000", "480000_5456000", "480000_5457000",
#                      "481000_5454000", "481000_5455000", "481000_5456000", "481000_5457000", "481000_5458000",
#                      "482000_5454000", "482000_5455000", "482000_5456000", "482000_5457000"]
datasets = []

print("done loading level", time.time() - start_time)
for filename in os.listdir("../LiDAR LAS Data/las/"):
    if filename.endswith(".las") and not filename[:-4] in finished_datasets:
        dataset = pylas.read("LiDAR LAS Data/las/" + filename)
        print("transforming chunks for", filename, time.time() - start_time)
        perform_dataset_transformation(dataset)
        print("done transforming chunks for", filename, time.time() - start_time)
#         break  # for now, just do one dataset
