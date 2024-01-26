import math
import os
import time

import amulet
import numpy as np
import pylas
import pyproj
from PIL import Image
from amulet.utils import block_coords_to_chunk_coords
import sys
import os

MIN_HEIGHT = -64
MAX_HEIGHT = 100
ROTATION_DEGREES = 28.000  # This is the rotation of UBC's roads relative to true north.
ROTATION_RADIANS = math.radians(ROTATION_DEGREES)
INVERSE_ROTATION_MATRIX = np.array([[math.cos(ROTATION_RADIANS), math.sin(ROTATION_RADIANS), 0],
                                    [-math.sin(ROTATION_RADIANS), math.cos(ROTATION_RADIANS), 0],
                                    [0, 0, 1]])
BLOCK_OFFSET_X = 480000
BLOCK_OFFSET_Z = 5455000
HEIGHT_OFFSET = 59
GAME_VERSION = ("java", (1, 19, 4))
# PROJECT_DIRECTORY = r"C:\Users\Ashtan\OneDrive - UBC\School\2023S\minecraftUBC"
PROJECT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORLD_DIRECTORY = os.path.join(PROJECT_DIRECTORY, "world/UBC")
LIDAR_DIRECTORY = os.path.join(PROJECT_DIRECTORY, "resources/LiDAR LAS Data/las")
TEXTURE_DIRECTORY = os.path.join(PROJECT_DIRECTORY, "resources/block")


def convert_lat_long_to_x_z(lat, long, return_int=True):
    """
    Converts the given latitude and longitude coordinates to Minecraft x and z coordinates. Uses a pipeline to convert
    from EPSG:4326 (lat/lon) to EPSG:26910 (UTM zone 10N).
    :param lat: the latitude coordinate
    :param long: the longitude coordinate
    :param return_int: whether to return the coordinates as integers or not
    :return: the Minecraft x and z coordinates of the given latitude and longitude
    """
    pipeline = "+proj=pipeline +step +proj=axisswap +order=2,1 +step +proj=unitconvert +xy_in=deg +xy_out=rad +step " \
               "+proj=utm +zone=10 +ellps=GRS80"
    transformer = pyproj.Transformer.from_pipeline(pipeline)
    transformed_x, transformed_z = transformer.transform(lat, long)
    x, z, _ = np.matmul(INVERSE_ROTATION_MATRIX, np.array([transformed_x - BLOCK_OFFSET_X,
                                                           transformed_z - BLOCK_OFFSET_Z,
                                                           1]))
    z = -z  # flip z axis to match Minecraft

    if return_int:
        return int(x), int(z)
    else:
        return x, z


def bresenham_3d(x1, y1, z1, x2, y2, z2):
    """
    Implementation for Bresenham's algorithm in 3d. Adapted from the following source:
    https://www.geeksforgeeks.org/bresenhams-algorithm-for-3-d-line-drawing/
    :param x1: Starting x coordinate
    :param y1: Starting y coordinate
    :param z1: Starting z coordinate
    :param x2: Ending x coordinate
    :param y2: Ending y coordinate
    :param z2: Ending z coordinate
    :return: List of points in the line
    """
    x1, y1, z1 = int(x1), int(y1), int(z1)
    x2, y2, z2 = int(x2), int(y2), int(z2)
    list_of_points = [(x1, y1, z1)]
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    dz = abs(z2 - z1)
    if x2 > x1:
        xs = 1
    else:
        xs = -1
    if y2 > y1:
        ys = 1
    else:
        ys = -1
    if z2 > z1:
        zs = 1
    else:
        zs = -1

    # Driving axis is X-axis
    if dx >= dy and dx >= dz:
        p1 = 2 * dy - dx
        p2 = 2 * dz - dx
        while x1 != x2:
            x1 += xs
            if p1 >= 0:
                y1 += ys
                p1 -= 2 * dx
            if p2 >= 0:
                z1 += zs
                p2 -= 2 * dx
            p1 += 2 * dy
            p2 += 2 * dz
            list_of_points.append((x1, y1, z1))

    # Driving axis is Y-axis
    elif dy >= dx and dy >= dz:
        p1 = 2 * dx - dy
        p2 = 2 * dz - dy
        while y1 != y2:
            y1 += ys
            if p1 >= 0:
                x1 += xs
                p1 -= 2 * dy
            if p2 >= 0:
                z1 += zs
                p2 -= 2 * dy
            p1 += 2 * dx
            p2 += 2 * dz
            list_of_points.append((x1, y1, z1))

    # Driving axis is Z-axis
    else:
        p1 = 2 * dy - dz
        p2 = 2 * dx - dz
        while z1 != z2:
            z1 += zs
            if p1 >= 0:
                y1 += ys
                p1 -= 2 * dz
            if p2 >= 0:
                x1 += xs
                p2 -= 2 * dz
            p1 += 2 * dy
            p2 += 2 * dx
            list_of_points.append((x1, y1, z1))

    return list_of_points


def bresenham_2d(x1, y1, x2, y2):
    """
    Implementation for Bresenham's algorithm in 2d. Adapted from the 3d version above.
    :param x1: Starting x coordinate
    :param y1: Starting y coordinate
    :param x2: Ending x coordinate
    :param y2: Ending y coordinate
    :return: List of points in the line
    """

    # convert all coordinates to integers
    x1, y1 = int(x1), int(y1)
    x2, y2 = int(x2), int(y2)
    list_of_points = [(x1, y1)]
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    if x2 > x1:
        xs = 1
    else:
        xs = -1
    if y2 > y1:
        ys = 1
    else:
        ys = -1

    # Driving axis is X-axis
    if dx >= dy:
        p1 = 2 * dy - dx
        while x1 != x2:
            x1 += xs
            if p1 >= 0:
                y1 += ys
                p1 -= 2 * dx
            p1 += 2 * dy
            list_of_points.append((x1, y1))

    # Driving axis is Y-axis
    else:
        p1 = 2 * dx - dy
        while y1 != y2:
            y1 += ys
            if p1 >= 0:
                x1 += xs
                p1 -= 2 * dy
            p1 += 2 * dx
            list_of_points.append((x1, y1))

    return list_of_points


def region_setup():
    """
    Prompts the user for coordinates of the region to be analyzed. Loads the level and returns the level object and
    corresponding chunk coordinates.
    :return: chunk coordinates of the region to be analyzed, level object
    """
    level = amulet.load_level(WORLD_DIRECTORY)
    start_coords = get_coords_from_prompt("starting coordinate: ")
    end_coords = get_coords_from_prompt("ending coordinate: ")
    chunk_start_x, chunk_start_z = block_coords_to_chunk_coords(start_coords[0], start_coords[1])
    chunk_end_x, chunk_end_z = block_coords_to_chunk_coords(end_coords[0], end_coords[1])
    if chunk_start_x > chunk_end_x:
        chunk_start_x, chunk_end_x = chunk_end_x, chunk_start_x  # Swap to ensure chunk_start_x < chunk_end_x
    if chunk_start_z > chunk_end_z:
        chunk_start_z, chunk_end_z = chunk_end_z, chunk_start_z  # Swap to ensure chunk_start_z < chunk_end_z

    return chunk_start_x, chunk_end_x, chunk_start_z, chunk_end_z, level


def get_coords_from_prompt(prompt_string):
    """
    Parses the given prompt string and returns the coordinates as a numpy array.
    :param prompt_string: string to prompt the user with
    :return: numpy array of coordinates, with the y coordinate removed
    """
    user_prompt = input(prompt_string)
    inputted_text_array = user_prompt.split(" ")
    if inputted_text_array[0] == "/tp":
        inputted_text_array = inputted_text_array[1:]
    coordinate_array_full = [float(coord) for coord in inputted_text_array]
    coordinate_array = np.array(coordinate_array_full[::2])

    return coordinate_array


def seed_setup():
    """
    Prompts the user for the coordinates of where they want the seed to be set for a flood fill operation. Initializes
    the flood fill array and the level object.
    :return: level object and an initialized flood fill array
    """
    level = amulet.load_level(WORLD_DIRECTORY)
    print("Enter the coordinates of the region to fill in  (i.e. '/tp 1738.5 200 -466.5')")
    points_to_fill = get_coords_from_prompt("Coordinates: ")

    return level, points_to_fill


def dataset_iterator(dataset_operation, finished_datasets=None):
    """
    Iterates through all the .las files in the given directory and applies the given decorator to each dataset.
    :param dataset_operation: function to apply to each dataset
    :param finished_datasets: list of datasets that have already been processed
    :return: None
    """
    if finished_datasets is None:
        finished_datasets = []
    start_time = time.time()
    for filename in os.listdir(LIDAR_DIRECTORY):
        if filename.endswith(".las") and filename not in finished_datasets:
            dataset = pylas.read(os.path.join(LIDAR_DIRECTORY, filename))
            print("transforming chunks for", filename, time.time() - start_time)
            dataset_operation(dataset, start_time)
            print("done transforming chunks for", filename, time.time() - start_time)


def get_height(block_x, block_z, level, blocks_to_ignore=None):
    """
    Gets the height of the highest block at the given x and z coordinates.
    :param block_x: x coordinate of the block
    :param block_z: z coordinate of the block
    :param level: Amulet level object
    :param blocks_to_ignore: list of blocks to ignore when calculating the height
    :return: height of the highest non-ignored block at the given x and z coordinates
    """
    if blocks_to_ignore is None:
        blocks_to_ignore = []
    chunk_x, chunk_z = block_coords_to_chunk_coords(block_x, block_z)
    chunk = level.get_chunk(chunk_x, chunk_z, "minecraft:overworld")
    block_ids_to_ignore = [level.block_palette.get_add_block(block) for block in blocks_to_ignore]
    offset_x, offset_z = block_x % 16, block_z % 16
    # so overall we want to ignore blocks that are != 0 and are not in the blocks_to_ignore list
    for y in range(MAX_HEIGHT, MIN_HEIGHT, -1):
        block = chunk.blocks[offset_x, y, offset_z]
        if block not in block_ids_to_ignore and block != 0:
            return y

    return None


def preprocess_dataset(lidar_ds, label_to_keep, remove_duplicates=True):
    """
    Preprocesses the given dataset by removing all points that are not of the given label, and then rotating the
    dataset to match Minecraft's orientation.
    :param remove_duplicates: whether to remove duplicate points or not
    :param lidar_ds: the dataset to preprocess
    :param label_to_keep: the label (e.g. 2 for ground terrain) to keep
    :return: the maximum and minimum x and z coordinates of the dataset, and the x, y, and z coordinates of the dataset
    """
    initial_x, initial_z, initial_y, labels = lidar_ds.x, lidar_ds.y, lidar_ds.z, lidar_ds.classification
    indices_to_delete = np.where(labels != label_to_keep)
    filtered_x, filtered_y, filtered_z = np.delete(initial_x, indices_to_delete), \
        np.delete(initial_y, indices_to_delete), np.delete(initial_z, indices_to_delete)
    dataset = np.matmul(INVERSE_ROTATION_MATRIX, np.array([filtered_x - BLOCK_OFFSET_X,
                                                           filtered_z - BLOCK_OFFSET_Z,
                                                           filtered_y - HEIGHT_OFFSET]))
    rotated_x, rotated_z, rotated_y = np.floor(dataset[0]), -np.floor(dataset[1]), np.floor(dataset[2])
    # remove duplicate points (considering x, y, z pairs)
    if remove_duplicates:
        unique_indices = np.unique(np.array([rotated_x, rotated_y, rotated_z]), axis=1, return_index=True)[1]
        unique_x, unique_y, unique_z = rotated_x[unique_indices], rotated_y[unique_indices], rotated_z[unique_indices]
        min_x, min_z, max_x, max_z = np.floor(np.min(unique_x) / 16) * 16, np.floor(np.min(unique_z) / 16) * 16, np.ceil(
            np.max(unique_x) / 16) * 16, np.ceil(np.max(unique_z) / 16) * 16

        return max_x, max_z, min_x, min_z, unique_x, unique_y, unique_z
    else:
        min_x, min_z, max_x, max_z = np.floor(np.min(rotated_x) / 16) * 16, np.floor(np.min(rotated_z) / 16) * 16, np.ceil(
            np.max(rotated_x) / 16) * 16, np.ceil(np.max(rotated_z) / 16) * 16

        return max_x, max_z, min_x, min_z, rotated_x, rotated_y, rotated_z


def get_average_rgb(block_object):
    """
    Gets the average RGB value of the given block object's texture.
    :param block_object: the block object to get the texture of
    :return: the average RGB value of the given block object's texture
    """
    texture = Image.open(TEXTURE_DIRECTORY + "/" + block_object.base_name + ".png").convert("RGB")

    return texture.resize((1, 1), resample=Image.BILINEAR).getpixel((0, 0))
