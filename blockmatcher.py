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
from amulet_nbt import StringTag

# This is a simple Python script that transforms a chunk (16m x 16m) of data and transforms it into a Minecraft chunk.
# It processes the entire chunk but breaks it down into meter-by-meter blocks.

start_time = time.time()
# load the level
level = amulet.load_level("world/UBC")
game_version = ("java", (1, 19, 4))

# coordinates of whatever we want to set as 0,0
x_offset = 480000
y_offset = 5455000
z_offset = 55

allowed_blocks = {  # class 2. Looks like these are roads and stuff
    # "dirt": Block("minecraft", "dirt"),
    "stone": Block("minecraft", "stone"),
    # "moss block": Block("minecraft", "moss_block"),
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
    # "polished blackstone": Block("minecraft", "polished_blackstone"),
    # "white concrete": Block("minecraft", "white_concrete"),
    # "light gray concrete": Block("minecraft", "light_gray_concrete"),
    # "gray concrete": Block("minecraft", "gray_concrete"),
    # "black concrete": Block("minecraft", "black_concrete"),
    # "brown concrete": Block("minecraft", "brown_concrete"),
    # "red concrete": Block("minecraft", "red_concrete"),
    # "orange concrete": Block("minecraft", "orange_concrete"),
    # "yellow concrete": Block("minecraft", "yellow_concrete"),
    # "lime concrete": Block("minecraft", "lime_concrete"),
    # "green concrete": Block("minecraft", "green_concrete"),
    # "cyan concrete": Block("minecraft", "cyan_concrete"),
    # "light blue concrete": Block("minecraft", "light_blue_concrete"),
    # "blue concrete": Block("minecraft", "blue_concrete"),
    # "purple concrete": Block("minecraft", "purple_concrete"),
    # "magenta concrete": Block("minecraft", "magenta_concrete"),
    # "pink concrete": Block("minecraft", "pink_concrete"),
    # let's change from concrete to the blocks that are actually used in the buildings
    "bricks": Block("minecraft", "bricks"),
    "mud bricks": Block("minecraft", "mud_bricks"),
    "nether bricks": Block("minecraft", "nether_bricks"),
    # that should cover the reds
    "block of iron": Block("minecraft", "iron_block"),
    "stone bricks": Block("minecraft", "stone_bricks"),
    "deepslate tiles": Block("minecraft", "deepslate_tiles"),
    # that should cover the grays
    "oak planks": Block("minecraft", "oak_planks"),
    # that should cover the wood... this isn't really used in many places and I do want to significantly limit the
    # number of blocks that are used
}

# next we need to get the textures for each Minecraft block, and get the average rgb value for each texture
texture_location = "resources/block"

allowed_blocks_texture = {}

for block, block_object in allowed_blocks.items():
    try:
        texture = Image.open(texture_location + "/" + block_object.base_name + ".png").convert("RGB")
    except FileNotFoundError:
        texture = Image.open(texture_location + "/" + block_object.base_name + "_top.png").convert("RGB")

    # get the average rgb value for the whole texture
    allowed_blocks_texture[block] = texture.resize((1, 1), resample=Image.BILINEAR).getpixel((0, 0))

allowed_vegetation_texture = {}

for block, block_object in allowed_vegetation.items():
    try:
        texture = Image.open(texture_location + "/" + block_object.base_name + ".png").convert("RGB")
    except FileNotFoundError:
        texture = Image.open(texture_location + "/" + block_object.base_name + "_top.png").convert("RGB")

    # get the average rgb value for the whole texture
    allowed_vegetation_texture[block] = texture.resize((1, 1), resample=Image.BILINEAR).getpixel((0, 0))

allowed_trees_texture = {}

for block, block_object in allowed_trees.items():
    try:
        texture = Image.open(texture_location + "/" + block_object.base_name + ".png").convert("RGB")
    except FileNotFoundError:
        texture = Image.open(texture_location + "/" + block_object.base_name + "_top.png").convert("RGB")

    # get the average rgb value for the whole texture
    allowed_trees_texture[block] = texture.resize((1, 1), resample=Image.BILINEAR).getpixel((0, 0))

allowed_building_blocks_texture = {}

for block, block_object in allowed_building_blocks.items():
    try:
        texture = Image.open(texture_location + "/" + block_object.base_name + ".png").convert("RGB")
    except FileNotFoundError:
        texture = Image.open(texture_location + "/" + block_object.base_name + "_top.png").convert("RGB")

    # get the average rgb value for the whole texture
    allowed_building_blocks_texture[block] = texture.resize((1, 1), resample=Image.BILINEAR).getpixel((0, 0))

rotation_degrees = 32
rotation = math.radians(rotation_degrees)
inverse_rotation_matrix = np.array([[math.cos(rotation), math.sin(rotation), 0],
                                    [-math.sin(rotation), math.cos(rotation), 0],
                                    [0, 0, 1]])

print("done computing average rgb values for textures", time.time() - start_time)
# NOTE that we could do a more complex approach here to get more accurate results, but this is good enough for now

# load the data
# datasets = []
# for filename in os.listdir("LiDAR LAS Data/las/"):
#     if filename.endswith(".las"):
#         datasets.append(pylas.read("LiDAR LAS Data/las/" + filename))
# datasets.append(pylas.read("LiDAR LAS Data/las/480000_5457000.las"))

# print("done loading data", time.time() - start_time)


def transformChunk(data):
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
    # get the chunk coordinates (minimum x, minimum z)

    # now group together the data points that have the same x, y, and z coordinates
    # average the rgb values for each group
    # compare with the rgb values for each Minecraft block texture, and choose the closest one
    # place the block in the chunk

    unique_x, x_indices = np.unique(x, return_index=True)
    unique_y, y_indices = np.unique(y, return_index=True)
    unique_z, z_indices = np.unique(z, return_index=True)

    # avg_red = np.zeros((len(unique_x), len(unique_y), len(unique_z)))
    # avg_green = np.zeros((len(unique_x), len(unique_y), len(unique_z)))
    # avg_blue = np.zeros((len(unique_x), len(unique_y), len(unique_z)))
    # avg_class = np.zeros((len(unique_x), len(unique_y), len(unique_z)))

    for i, j, k in np.ndindex(len(unique_x), len(unique_y), len(unique_z)):

        # For each unique x, y, z coordinate, we want to get the average rgb value for all the data points that have
        # that coordinate. Red, green, and blue are all one-dimensional arrays.
        matching_indices = np.where((x == unique_x[i]) & (y == unique_y[j]) & (z == unique_z[k]))
        if matching_indices[0].size == 0:
            continue
        avg_red = np.average(red[matching_indices])
        avg_green = np.average(green[matching_indices])
        avg_blue = np.average(blue[matching_indices])
        avg_class = np.median(labels[matching_indices])  # the most common class in the group

        if avg_class == 2:
            mapped_texture = min(allowed_blocks_texture, key=lambda x: np.linalg.norm(
                allowed_blocks_texture[x] - np.array([avg_red, avg_green, avg_blue])))
            # now we need to get from the name to the actual Block object
            block = allowed_blocks[mapped_texture]
            level.set_version_block(unique_x[i].astype(int), unique_z[k].astype(int), unique_y[j].astype(int),
                                    "minecraft:overworld", game_version, block)
        elif avg_class == 3:
            mapped_texture = min(allowed_vegetation_texture, key=lambda x: np.linalg.norm(
                allowed_vegetation_texture[x] - np.array([avg_red, avg_green, avg_blue])))
            # now we need to get from the name to the actual Block object
            block = allowed_vegetation[mapped_texture]
            level.set_version_block(unique_x[i].astype(int), unique_z[k].astype(int), unique_y[j].astype(int),
                                    "minecraft:overworld", game_version, block)
        elif avg_class == 5:
            mapped_texture = min(allowed_trees_texture, key=lambda x: np.linalg.norm(
                allowed_trees_texture[x] - np.array([avg_red, avg_green, avg_blue])))
            # now we need to get from the name to the actual Block object
            block = allowed_trees[mapped_texture]
            level.set_version_block(unique_x[i].astype(int), unique_z[k].astype(int), unique_y[j].astype(int),
                                    "minecraft:overworld", game_version, block)
        elif avg_class == 6:
            mapped_texture = min(allowed_building_blocks_texture, key=lambda x: np.linalg.norm(
                allowed_building_blocks_texture[x] - np.array(
                    [avg_red, avg_green, avg_blue])))
            # now we need to get from the name to the actual Block object
            block = allowed_building_blocks[mapped_texture]
            level.set_version_block(unique_x[i].astype(int), unique_z[k].astype(int), unique_y[j].astype(int),
                                    "minecraft:overworld", game_version, block)
        else:
            block = Block("minecraft", "air")
            level.set_version_block(unique_x[i].astype(int), unique_z[k].astype(int), unique_y[j].astype(int),
                                    "minecraft:overworld", game_version, block)
        # print("placed block at", unique_x[i], unique_z[k], unique_y[j], "with rgb", avg_red[i, j, k], avg_green[i, j, k],
        #       avg_blue[i, j, k], "and texture", mapped_texture)
    level.save()


def deleteIndices(blue, green, labels, noise_indices, red, x, y, z):
    x = np.delete(x, noise_indices)
    y = np.delete(y, noise_indices)
    z = np.delete(z, noise_indices)
    red = np.delete(red, noise_indices)
    green = np.delete(green, noise_indices)
    blue = np.delete(blue, noise_indices)
    labels = np.delete(labels, noise_indices)
    return blue, green, labels, red, x, y, z


def performDatasetTransformation(ds):
    x = ds.x
    y = ds.y
    z = ds.z
    red = ds.red
    green = ds.green
    blue = ds.blue
    labels = ds.classification
    # denoise: remove all labels that are not 2, 3, 5, or 6
    noise_indices = np.where((labels == 1) | (labels == 9) | (labels == 7) | (labels == 4) | (labels == 8))
    blue, green, labels, red, x, y, z = deleteIndices(blue, green, labels, noise_indices, red, x, y, z)
    # apply the inverse rotation matrix to the x and y coordinates
    x = x - x_offset
    y = y - y_offset
    z = z - z_offset
    print("performing rotation matrix multiplication")
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
    x, y, z, red, green, blue, labels = x[sort_indices], y[sort_indices], z[sort_indices], red[sort_indices], green[
        sort_indices], \
        blue[sort_indices], labels[sort_indices]

    print("done sorting data", time.time() - start_time)

    # remove data points that are above 256m
    indices = np.where(z < 256)
    x, y, z, red, green, blue, labels = x[indices], y[indices], z[indices], red[indices], green[indices], blue[indices], \
        labels[
            indices]

    # Next, the script that we will be using to transform the chunk into a Minecraft chunk.
    # Data will be passed in as an array of data points to be treated as LIDAR data.

    # now we need to iterate over the chunks. We'll do this by iterating over the x and y coordinates of the chunks

    # round min and max to the lower and upper 16s and set as integers
    min_x = np.floor(min_x / 16) * 16
    min_y = np.floor(min_y / 16) * 16
    max_x = np.ceil(max_x / 16) * 16
    max_y = np.ceil(max_y / 16) * 16

    for cx in range(min_x.astype(int), max_x.astype(int), 16):
        for cy in range(min_y.astype(int), max_y.astype(int), 16):
            # get the data points that are in this chunk
            chunk_indices = np.where((x >= cx) & (x < cx + 16) & (y >= cy) & (y < cy + 16))
            chunk_data = np.array(
                [x[chunk_indices], y[chunk_indices], z[chunk_indices], red[chunk_indices], green[chunk_indices],
                 blue[chunk_indices], labels[chunk_indices]])
            transformChunk(chunk_data)
            print("done with chunk", cx, " ", cy, time.time() - start_time)
    # print("done transforming chunks", time.time() - start_time)


# datasets = []
# level = amulet.load_level("world/UBC")
# print("done loading level", time.time() - start_time)
for filename in os.listdir("LiDAR LAS Data/las/"):
    if filename.endswith(".las"):
        ds = pylas.read("LiDAR LAS Data/las/" + filename)
        performDatasetTransformation(ds)
        print("done transforming chunks for", filename, time.time() - start_time)
        # break  # for now, just do one dataset
level.close()
# for ds in datasets:
#     level = amulet.load_level("world/UBC")
#     performDatasetTransformation(ds)
#     level.close()

# level.close() # given this method removes temporary files, it may be a good idea to call this after each dataset is
# processed, and then reopen it for the next dataset.

print("done", time.time() - start_time)
