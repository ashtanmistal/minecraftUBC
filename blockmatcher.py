# blockmatcher.py
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
from amulet.utils.world_utils import block_coords_to_chunk_coords

# This is a simple Python script that transforms a chunk (16m x 16m) of data and transforms it into a Minecraft chunk.
# It processes the entire chunk but breaks it down into meter-by-meter blocks.

start_time = time.time()
# load the level
level = amulet.load_level("world/UBC")  # TODO replace with path to the Minecraft world folder
game_version = ("java", (1, 19, 4))

# coordinates of what we want to set as 0,0
x_offset = 482000
y_offset = 5457000
z_offset = 55

allowed_blocks = {
    "grass block": Block("minecraft", "grass_block"),
    "dirt": Block("minecraft", "dirt"),
    "dirt path": Block("minecraft", "dirt_path"),
    "sand": Block("minecraft", "sand"),
    "gravel": Block("minecraft", "gravel"),
    "stone": Block("minecraft", "stone"),
    "stone bricks": Block("minecraft", "stone_bricks"),
    "cracked stone bricks": Block("minecraft", "cracked_stone_bricks"),
    "polished blackstone": Block("minecraft", "polished_blackstone"),
    "granite": Block("minecraft", "granite"),
    "cut sandstone": Block("minecraft", "cut_sandstone"),
    "cut red sandstone": Block("minecraft", "cut_red_sandstone"),
    "quartz block": Block("minecraft", "quartz_block"),
    "spruce log": Block("minecraft", "spruce_log"),
    "oak log": Block("minecraft", "oak_log"),
    "oak planks": Block("minecraft", "oak_planks"),
    "spruce planks": Block("minecraft", "spruce_planks"),
    "birch planks": Block("minecraft", "birch_planks"),
    "oak leaves": Block("minecraft", "oak_leaves"),
    "spruce leaves": Block("minecraft", "spruce_leaves"),
    "grass": Block("minecraft", "grass"),
    "white concrete": Block("minecraft", "white_concrete"),
    "light gray concrete": Block("minecraft", "light_gray_concrete"),
    "gray concrete": Block("minecraft", "gray_concrete"),
    "black concrete": Block("minecraft", "black_concrete"),
    "brown concrete": Block("minecraft", "brown_concrete"),
    "red concrete": Block("minecraft", "red_concrete"),
    "orange concrete": Block("minecraft", "orange_concrete"),
    "yellow concrete": Block("minecraft", "yellow_concrete"),
    "lime concrete": Block("minecraft", "lime_concrete"),
    "green concrete": Block("minecraft", "green_concrete"),
    "cyan concrete": Block("minecraft", "cyan_concrete"),
    "light blue concrete": Block("minecraft", "light_blue_concrete"),
    "blue concrete": Block("minecraft", "blue_concrete"),
    "purple concrete": Block("minecraft", "purple_concrete"),
    "magenta concrete": Block("minecraft", "magenta_concrete"),
    "pink concrete": Block("minecraft", "pink_concrete"),
    "bricks": Block("minecraft", "bricks"),
    "mud bricks": Block("minecraft", "mud_bricks"),
    "nether bricks": Block("minecraft", "nether_bricks"),
}

# next we need to get the textures for each Minecraft block, and get the average rgb value for each texture
texture_location = "resources/block"

texture_average_rgb = {}

for block, block_object in allowed_blocks.items():
    try:
        texture = Image.open(texture_location + "/" + block_object.base_name + ".png").convert("RGB")
    except FileNotFoundError:
        texture = Image.open(texture_location + "/" + block_object.base_name + "_top.png").convert("RGB")

    # get the average rgb value for the whole texture
    texture_average_rgb[block] = texture.resize((1, 1), resample=Image.BILINEAR).getpixel((0, 0))

rotation_degrees = 29.5
rotation = math.radians(rotation_degrees)
inverse_rotation_matrix = np.array([[math.cos(rotation), math.sin(rotation), 0],
                                    [-math.sin(rotation), math.cos(rotation), 0],
                                    [0, 0, 1]])

# the files we want to look at are in the "LiDAR LAS Data/las/" folder. We want to care only about the files that
# end in ".las" (not ".laz").

print("done computing average rgb values for textures", time.time() - start_time)

# load the data
datasets = []
for filename in os.listdir("LiDAR LAS Data/las/"):
    if filename.endswith(".las"):
        datasets.append(pylas.read("LiDAR LAS Data/las/" + filename))

print("done loading data", time.time() - start_time)

x = np.array([])
y = np.array([])
z = np.array([])
red = np.array([])
green = np.array([])
blue = np.array([])
for ds in datasets:
    x = np.append(x, ds.x)
    y = np.append(y, ds.y)
    z = np.append(z, ds.z)
    red = np.append(red, ds.red)
    green = np.append(green, ds.green)
    blue = np.append(blue, ds.blue)

# apply the inverse rotation matrix to the x and y coordinates
x = x - x_offset
y = y - y_offset
z = z - z_offset
x, y, z = np.matmul(inverse_rotation_matrix, np.array([x, y, z]))

print("done applying rotation matrix", time.time() - start_time)

# next we need to iterate over these chunks.
min_x, min_y, min_z = np.floor(np.min(x)), np.floor(np.min(y)), np.floor(np.min(z))
max_x, max_y, max_z = np.ceil(np.max(x)), np.ceil(np.max(y)), np.ceil(np.max(z))

# convert rgb from 0-65535 to 0-255
red = red / 256
green = green / 256
blue = blue / 256
red = red.astype(int)
green = green.astype(int)
blue = blue.astype(int)

# sort by x, then y, then z. the colors should be sorted in the same way.
sort_indices = np.lexsort((z, y, x))
x, y, z, red, green, blue = x[sort_indices], y[sort_indices], z[sort_indices], red[sort_indices], green[sort_indices], \
blue[sort_indices]

print("done sorting data", time.time() - start_time)


# remove data points that are above 256m

# Next, the script that we will be using to transform the chunk into a Minecraft chunk.
# Data will be passed in as an array of data points to be treated as LIDAR data.


def transformChunk(data, cx, cy):
    # We will break it up into 16 1m x 1m "sticks" that span the entire chunk.
    # Whatever data is in that stick tells is what blocks to place in that stick.
    # as there's likely to be more than one block per stick, we want to place all of them.

    x, y, z, red, green, blue = data
    x, y, z = np.floor(x), np.floor(y), np.floor(z)
    # get the chunk coordinates (minimum x, minimum z)
    chunk = Chunk(math.floor(cx), math.floor(cy))

    # now group together the data points that have the same x, y, and z coordinates
    # average the rgb values for each group
    # compare with the rgb values for each Minecraft block texture, and choose the closest one
    # place the block in the chunk (can set it all at once)
    unique_x, x_indices = np.unique(x, return_inverse=True)
    unique_y, y_indices = np.unique(y, return_inverse=True)
    unique_z, z_indices = np.unique(z, return_inverse=True)

    avg_red = np.zeros((len(unique_x), len(unique_y), len(unique_z)))
    avg_green = np.zeros((len(unique_x), len(unique_y), len(unique_z)))
    avg_blue = np.zeros((len(unique_x), len(unique_y), len(unique_z)))

    for i, j, k in np.ndindex(avg_red.shape):
        mask = (x_indices == i) & (y_indices == j) & (z_indices == k)
        avg_red[i, j, k] = np.average(red[mask])
        avg_green[i, j, k] = np.average(green[mask])
        avg_blue[i, j, k] = np.average(blue[mask])

    # compare with the rgb values for each Minecraft block texture, and choose the closest one
    # place the block in the chunk (can set it all at once)
    closest_block = np.zeros((len(unique_x), len(unique_y), len(unique_z)))
    for i, j, k in np.ndindex(closest_block.shape):
        closest_block[i, j, k] = min(texture_average_rgb, key=lambda x: np.linalg.norm(
            texture_average_rgb[x] - np.array([avg_red[i, j, k], avg_green[i, j, k], avg_blue[i, j, k]])))

    # place the block in the chunk
    chunk_coords_x, chunk_coords_z = block_coords_to_chunk_coords(unique_x, unique_y)
    chunk_coords_y = unique_z
    # Minecraft uses a different coordinate system than we do. We need to flip the y and z coordinates.

    # flip the closest_block y and z coordinates
    closest_block = np.flip(closest_block, axis=1)

    chunk[chunk_coords_x, chunk_coords_y, chunk_coords_z] = closest_block

    level.put_chunk(chunk, "minecraft:overworld")
    chunk.changed = True
    level.save()


# now we need to iterate over the chunks. We'll do this by iterating over the x and y coordinates of the chunks.

for cx in range(min_x, max_x, 16):
    for cy in range(min_y, max_y, 16):
        # get the data points that are in this chunk
        chunk_indices = np.where((x >= cx) & (x < cx + 16) & (y >= cy) & (y < cy + 16))
        chunk_data = np.array(
            [x[chunk_indices], y[chunk_indices], z[chunk_indices], red[chunk_indices], green[chunk_indices],
             blue[chunk_indices]], cx, cy)
        transformChunk(chunk_data, cx, cy)

print("done transforming chunks", time.time() - start_time)

level.close()

print("done", time.time() - start_time)
