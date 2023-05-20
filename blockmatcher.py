# blockmatcher.py
# author: Ashtan Mistal
import math
import os

# This is a simple Python script that transforms a chunk (16m x 16m) of data and transforms it into a Minecraft chunk.
# It processes the entire chunk but breaks it down into meter-by-meter blocks.

import amulet
from PIL import Image
from PIL import Resampling
from amulet.api.block import Block
from amulet.utils.world_utils import block_coords_to_chunk_coords
from amulet_nbt import StringTag, IntTag
from amulet.api.chunk import Chunk
from amulet.api.errors import ChunkLoadError, ChunkDoesNotExist
import matplotlib.pyplot as plt
import numpy as np

import pylas

# load the level
level = amulet.load_level("UBC")  # TODO replace with path to the Minecraft world folder
game_version = ("java", (1, 19, 4))

# coordinates of what we want to set as 0,0
# {"coordinates":[[[-123.24741269459518,49.265497418209144],[-123.24745768052215,49.274492527936644],[-123.23371015526665,49.27452115209688],[-123.23366766847829,49.265526033342084],[-123.24741269459518,49.265497418209144]]],"type":"Polygon"}
x_offset = 482000
height_offset = 0  # pretty sure we don't need to change the height but it does depend on the minimum / maximum height of the chunk
z_offset = 5457000
lat_to_m = 111111  # 1 degree of latitude is 111111 meters
long_to_m = 111111  # 1 degree of longitude is 111111 meters
# TODO double check that scaling... do NOT want to mess that up

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
        texture = Image.open(texture_location + "/" + block_object.base_name + ".png")
    except FileNotFoundError:
        texture = Image.open(texture_location + "/" + block_object.base_name + "_top.png")

    # get the average rgb value for the whole texture
    texture_average_rgb[block] = texture.resize((1, 1), resample=Resampling.BILINEAR).getpixel((0, 0))

# now let's perform a texture gradient analysis for the Minecraft textures. If the LiDAR data has enough points,
# this is what we'll use to determine the block type. (otherwise we'll just use the average rgb value)

# first, we need to get the texture gradients for each texture
# texture_gradients = {}
#
# for block, block_object in allowed_blocks.items():
#     texture = Image.open(texture_location + "/" + block_object.base_name + ".png")
#     # calculate the gradient for each pixel: Following Leung and Malik (2001)
#
#     # calculate the first derivative of the Gaussian in the x direction using Sobel operator
#     kernel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]) / 8
#     # calculate the first derivative of the Gaussian in the y direction using Sobel operator
#     kernel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]]) / 8
#

# we won't do the above for now; we'll just use the average rgb value for each texture. We'll come back to this later if we can.

rotation_degrees = 29.5
rotation = math.radians(rotation_degrees)
inverse_rotation_matrix = np.array([[math.cos(rotation), math.sin(rotation), 0],
                                    [-math.sin(rotation), math.cos(rotation), 0],
                                    [0, 0, 1]])

# the files we want to look at are in the "LiDAR LAS Data/las/" folder. We want to care only about the files that
# end in ".las" (not ".laz").

# load the data
datasets = []
for filename in os.listdir("LiDAR LAS Data/las/"):
    if filename.endswith(".las"):
        datasets.append(pylas.read("LiDAR LAS Data/las/" + filename))

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

x, y, z = np.matmul(inverse_rotation_matrix, np.array([x, y, z]))

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
x, y, z, red, green, blue = x[sort_indices], y[sort_indices], z[sort_indices], red[sort_indices], green[sort_indices], blue[sort_indices]

# Next, the script that we will be using to transform the chunk into a Minecraft chunk.
# Data will be passed in as an array of data points to be treated as LIDAR data.

def setBlocksInChunk(stick_data, chunk):
    x, y, z, red, green, blue = stick_data
    # break up by the z coordinate (1m blocks)
    # get the average rgb value for each block
    # compare with the closest average rgb value for each block
    # return the block type

    # break up by the z coordinate into 1m blocks
    # sort by z
    sort_indices = np.argsort(z)
    x, y, z, red, green, blue = x[sort_indices], y[sort_indices], z[sort_indices], red[sort_indices], green[sort_indices], blue[sort_indices]
    cur_z = math.floor(z[0])
    while cur_z < math.ceil(z[-1]):
        # get the data points that are in this block
        block_indices = np.where((z >= cur_z) & (z < cur_z + 1))
        block_data = np.array([x[block_indices], y[block_indices], z[block_indices], red[block_indices], green[block_indices], blue[block_indices]])
        # get the average rgb value for this block
        block_average_rgb = np.average(block_data, axis=1)
        # compare with the closest average rgb value for each block
        closest_block = min(texture_average_rgb, key=lambda x: np.linalg.norm(texture_average_rgb[x] - block_average_rgb))

        # place the block in the chunk
        chunk_offset_x = math.floor(x[0]) - chunk.x * 16
        chunk_offset_y = math.floor(y[0]) - chunk.z * 16
        # Minecraft uses a different coordinate system than we do. We need to flip the y and z coordinates.

        # chunk[chunk_offset_x, math.floor(y[0]), chunk_offset_z] = closest_block
        cur_z += 1



def transformChunk(data, cx, cy):
    # We will break it up into 16 1m x 1m "sticks" that span the entire chunk.
    # Whatever data is in that stick tells is what blocks to place in that stick.
    # as there's likely to be more than one block per stick, we want to place all of them.

    x, y, z, red, green, blue = data

    # get the chunk coordinates (minimum x, minimum z)
    chunk = Chunk(math.floor(cx), math.floor(cy))

    # populate the chunk with blocks by matching the data points to the blocks
    for i in range(0, 16):
        for j in range(0, 16):
            # get the data points that are in this stick
            stick_indices = np.where((x >= cx + i) & (x < cx + i + 1) & (y >= cy + j) & (y < cy + j + 1))
            stick_data = np.array([x[stick_indices], y[stick_indices], z[stick_indices], red[stick_indices], green[stick_indices], blue[stick_indices]])
            setBlocksInChunk(stick_data, chunk)


    level.put_chunk(chunk, "minecraft:overworld")
    chunk.changed = True
    level.save()


def After():
    level.close()

# now we need to iterate over the chunks. We'll do this by iterating over the x and y coordinates of the chunks.

for cx in range(min_x, max_x, 16):
    for cy in range(min_y, max_y, 16):
        # get the data points that are in this chunk
        chunk_indices = np.where((x >= cx) & (x < cx + 16) & (y >= cy) & (y < cy + 16))
        chunk_data = np.array([x[chunk_indices], y[chunk_indices], z[chunk_indices], red[chunk_indices], green[chunk_indices], blue[chunk_indices]], cx, cy)
        transformChunk(chunk_data)