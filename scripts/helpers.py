import math
import os
import time

import amulet
import numpy as np
import pylas
import pyproj
from amulet.utils import block_coords_to_chunk_coords


min_height = -64
max_height = 100
rotation_degrees = 28.000  # This is the rotation of UBC's roads relative to true north.
rotation = math.radians(rotation_degrees)
inverse_rotation_matrix = np.array([[math.cos(rotation), math.sin(rotation), 0],
                                    [-math.sin(rotation), math.cos(rotation), 0],
                                    [0, 0, 1]])
x_offset = 480000
z_offset = 5455000
game_version = ("java", (1, 19, 4))


def convert_lat_long_to_x_z(lat, long):
    """
    Converts the given latitude and longitude coordinates to Minecraft x and z coordinates. Uses a pipeline to convert
    from EPSG:4326 (lat/lon) to EPSG:26910 (UTM zone 10N).
    :param lat: the latitude coordinate
    :param long: the longitude coordinate
    :return: the Minecraft x and z coordinates of the given latitude and longitude
    """
    pipeline = "+proj=pipeline +step +proj=axisswap +order=2,1 +step +proj=unitconvert +xy_in=deg +xy_out=rad +step " \
               "+proj=utm +zone=10 +ellps=GRS80"
    transformer = pyproj.Transformer.from_pipeline(pipeline)
    x, z = transformer.transform(lat, long)
    x, z = x - x_offset, z - z_offset
    x, z, _ = np.matmul(inverse_rotation_matrix, np.array([x, z, 1]))
    z = -z  # flip z axis to match Minecraft
    return int(x), int(z)


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
    level = amulet.load_level("world/UBC")
    prompt = input("starting coordinate: ")
    start = prompt.split(" ")
    if start[0] == "/tp":
        start = start[1:]
    start = [float(coord) for coord in start]
    # we only need x and z; ignore y
    start = start[::2]
    start = np.array(start)
    prompt = input("ending coordinate: ")
    end = prompt.split(" ")
    if end[0] == "/tp":
        end = end[1:]
    end = [float(coord) for coord in end]
    end = end[::2]
    end = np.array(end)
    # get the chunk coordinates of the start and end points
    cx, cz = block_coords_to_chunk_coords(start[0], start[1])
    cx2, cz2 = block_coords_to_chunk_coords(end[0], end[1])
    if cx > cx2:
        cx, cx2 = cx2, cx
    if cz > cz2:
        cz, cz2 = cz2, cz
    return cx, cx2, cz, cz2, level


def seed_setup():
    """
    Prompts the user for the coordinates of where they want the seed to be set for a flood fill operation. Initializes
    the flood fill array and the level object.
    :return: level object and an initialized flood fill array
    """
    level = amulet.load_level("world/UBC")
    # Select a region to fill in
    prompt = "Enter the coordinates of the region to fill in  (i.e. '/tp 1738.5 200 -466.5')"
    print(prompt)
    coords = input("Coordinates: ").split(" ")
    # get rid of the /tp part if it exists
    if coords[0] == "/tp":
        coords = coords[1:]
    coords = [float(coord) for coord in coords]
    # we only need x and z; ignore y
    coords = coords[::2]
    points_to_fill = np.array(coords)
    return level, points_to_fill


def dataset_iterator(lidar_path, dataset_operation, finished_datasets=None):
    """
    Iterates through all the .las files in the given directory and applies the given decorator to each dataset.
    :param lidar_path: string path to the directory containing the .las files
    :param dataset_operation: function to apply to each dataset
    :param finished_datasets: list of datasets that have already been processed
    :return: None
    """
    if finished_datasets is None:
        finished_datasets = []
    start_time = time.time()
    for filename in os.listdir(lidar_path):
        if filename.endswith(".las") and filename not in finished_datasets:
            dataset = pylas.read(os.path.join(lidar_path, filename))
            print("transforming chunks for", filename, time.time() - start_time)
            dataset_operation(dataset, start_time)
            print("done transforming chunks for", filename, time.time() - start_time)


def get_height(x, z, level, blocks_to_ignore=None):
    if blocks_to_ignore is None:
        blocks_to_ignore = []
    cx, cz = block_coords_to_chunk_coords(x, z)
    chunk = level.get_chunk(cx, cz, "minecraft:overworld")
    block_ids_to_ignore = [level.block_palette.get_add_block(block) for block in blocks_to_ignore]
    offset_x, offset_z = x % 16, z % 16
    # so overall we want to ignore blocks that are != 0 and are not in the blocks_to_ignore list
    for y in range(max_height, min_height, -1):
        block = chunk.blocks[offset_x, y, offset_z]
        if block not in block_ids_to_ignore and block != 0:
            return y
    return None
