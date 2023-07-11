import amulet
import numpy as np
import pyproj
from amulet.utils import block_coords_to_chunk_coords

from scripts.utils import inverse_rotation_matrix, x_offset, z_offset


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
        bresenham_driver(dx, dy, dz, list_of_points, x1, x2, xs, y1, ys, z1, zs)

    # Driving axis is Y-axis
    elif dy >= dx and dy >= dz:
        bresenham_driver(dy, dx, dz, list_of_points, x1, y2, ys, y1, xs, z1, zs)

    # Driving axis is Z-axis
    else:
        bresenham_driver(dz, dy, dx, list_of_points, x1, z2, zs, y1, ys, z1, xs)
    return list_of_points


def bresenham_driver(dx, dy, dz, list_of_points, x1, x2, xs, y1, ys, z1, zs):
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
