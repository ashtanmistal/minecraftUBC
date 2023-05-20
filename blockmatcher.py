# blockmatcher.py
# author: Ashtan Mistal
import math
import os

# This is a simple Python script that transforms a chunk (16m x 16m) of data and transforms it into a Minecraft chunk.
# It processes the entire chunk but breaks it down into meter-by-meter blocks.

import amulet
from PIL import Image
from PIL.Image import Resampling
from amulet.api.block import Block
from amulet.utils.world_utils import block_coords_to_chunk_coords
from amulet_nbt import StringTag, IntTag
from amulet.api.chunk import Chunk
from amulet.api.errors import ChunkLoadError, ChunkDoesNotExist
import matplotlib.pyplot as plt
import numpy as np

import pylas

# load the level
# level = amulet.load_level("UBC")  # TODO replace with path to the Minecraft world folder
# game_version = ("java", (1, 19, 4))

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

# Next, the script that we will be using to transform the chunk into a Minecraft chunk.
# Data will be passed in as an array of data points to be treated as LIDAR data.

# def transformChunk(data):
#     # We will break it up into 16 1m x 1m "sticks" that span the entire chunk.
#     # Whatever data is in that stick tells is what blocks to place in that stick.
#     # as there's likely to be more than one block per stick, we want to place all of them.
#
#     x = data.x
#     height = data.z
#     y = data.y
#
#     # TODO find out if the color values are stored individually or as a single value
#     rgb = data.rgb
#
#     # get the chunk coordinates (minimum x, minimum z)
#     chunk = Chunk(math.floor(cx), math.floor(cy))
#
#     # TODO populate the chunk with blocks
#
#     level.put_chunk(chunk, "minecraft:overworld")
#     chunk.changed = True
#     level.save()
#
#
# def After():
#     level.close()
