"""
This is a helper script for various geojson operations. It takes in a set of connected vertices representing a polygon,
and voxelizes the space through a flood fill algorithm. This voxel set is then divided into chunks for further block
operations.
"""

import numpy as np

import src.helpers

CUTOFF_MAX_X = 5200
CUTOFF_MAX_Z = 2800


def point_inside_polygon(x_value: int, z_value: int, matrix) -> bool:
    """
    This function takes in a point and a matrix and returns True if the point is inside the polygon and
    False otherwise, via ray casting within the matrix.
    :param x_value: point x to test
    :param z_value: point z to test
    :param matrix: Matrix of boolean values where true represents a polygon edge
    :return: boolean value representing whether the point is inside the polygon
    """
    # find a point outside the polygon by checking the edges if the true values
    min_x, min_y = np.min(np.argwhere(matrix), axis=0)
    max_x, _ = np.max(np.argwhere(matrix), axis=0)
    # traverse x from min to max until we find a false value
    outside_point = None
    for x in range(min_x, max_x + 1):
        if not matrix[x, min_y]:
            outside_point = (x, min_y)
            break
    if outside_point is None:
        raise ValueError("No outside point found for polygon.")

    intersections = 0
    for x1, z1 in src.helpers.bresenham_2d(x_value, z_value, outside_point[0], outside_point[1]):
        if matrix[x1, z1]:
            intersections += 1

    return intersections % 2 == 1


def find_starting_point(matrix):
    """
    This function takes in a matrix and returns a starting point for the flood fill algorithm. It does this by
    scanning the matrix for a column or row with exactly two true values that are not adjacent. It then returns
    the x and z value between those two true values.
    :param matrix: Matrix of boolean values where true represents a polygon edge
    :return: tuple of x and z values representing the starting point for the flood fill algorithm
    """
    for x in range(matrix.shape[0]):
        z_values = np.argwhere(matrix[x, :])
        if len(z_values) == 2:
            z1, z2 = z_values.flatten()  # Flatten the array to get individual values
            if abs(z1 - z2) > 1:
                return x, (z1 + z2) // 2

    for z in range(matrix.shape[1]):
        x_values = np.argwhere(matrix[:, z])
        if len(x_values) == 2:
            x1, x2 = x_values.flatten()  # Flatten the array to get individual values
            if abs(x1 - x2) > 1:
                return (x1 + x2) // 2, z

    return None  # If no starting point is found, return None


def primary_vertices_divider(vertices: list):
    """
    This function takes in a list of vertices that define a polygon and returns a large matrix that is filled with
    True values where the polygon is. This large matrix can then be used to voxelize the polygon.
    :param vertices: The counterclockwise-oriented list of vertices representing the polygon
    :return: large matrix that is filled with True values where the polygon is, and the min x and z values
    """
    # First we need to convert the vertices into minecraft coordinates.
    translated_vertices = np.array(
        [src.helpers.convert_lat_long_to_x_z(vertex[1], vertex[0]) for vertex in vertices]).T
    min_x, min_z = np.min(translated_vertices, axis=1)
    translated_vertices -= np.array([min_x, min_z]).reshape(2, 1)
    max_x, max_z = np.max(translated_vertices, axis=1)

    large_matrix = np.zeros((max_x + 1, max_z + 1), dtype=bool)
    for i in range(len(translated_vertices[0]) - 1):
        x0, z0 = translated_vertices[:, i]
        x1, z1 = translated_vertices[:, i + 1]
        for x, z in src.helpers.bresenham_2d(x0, z0, x1, z1):
            large_matrix[x, z] = True
    # we should also connect the end to the beginning
    x0, z0 = translated_vertices[:, -1]
    x1, z1 = translated_vertices[:, 0]
    for x, z in src.helpers.bresenham_2d(x0, z0, x1, z1):
        large_matrix[x, z] = True
    # Now we need to find a starting point for the flood fill algorithm.
    # if there's not enough points to start the flood fill, or if it's all true, then we can just return the matrix
    if np.sum(large_matrix) < 8 or np.all(large_matrix):
        return large_matrix, min_x, min_z
    starting_point = find_starting_point(large_matrix)
    if starting_point is None:
        return large_matrix, min_x, min_z
    x, z = starting_point
    large_matrix = boolean_flood_fill(large_matrix, max_x, max_z, x, z)
    # Now we have a large matrix that is filled with True values where the polygon is.

    return large_matrix, min_x, min_z


def boolean_flood_fill(large_matrix, max_x, max_z, seed_x, seed_z):
    """
    Flood fill algorithm that sets all values in the matrix to True that are connected to the starting point
    :param large_matrix: Matrix to be filled
    :param max_x: max x value
    :param max_z: max z value
    :param seed_x: Seed x value
    :param seed_z: Seed z value
    :return: Flood filled matrix
    """
    queue = [(seed_x, seed_z)]
    while len(queue) > 0:
        x, z = queue.pop(0)
        if large_matrix[x, z]:
            continue
        large_matrix[x, z] = True
        if x > 0:
            queue.append((x - 1, z))
        if x < max_x:
            queue.append((x + 1, z))
        if z > 0:
            queue.append((x, z - 1))
        if z < max_z:
            queue.append((x, z + 1))
    return large_matrix


def secondary_vertices_divider(vertices: list, large_matrix, min_x, min_z):
    """
    transforms secondary vertices into minecraft coordinates, creates a large matrix, and performs a flood fill
    on the matrix. The secondary vertices are points that are within the primary polygon and represent holes in the
    polygon.
    :param vertices: List of secondary vertices
    :param large_matrix: The large matrix that represents the primary polygon
    :param min_x: min x value of the primary polygon
    :param min_z: min z value of the primary polygon
    :return: secondary large matrix
    """
    translated_vertices = np.array(
        [src.helpers.convert_lat_long_to_x_z(vertex[1], vertex[0]) for vertex in vertices]).T
    translated_vertices -= np.array([min_x, min_z]).reshape(2, 1)

    # we need to create another large_matrix object with which to flood fill these vertices. That new object we will
    # use to invert the values of the large_matrix object.
    secondary_large_matrix = np.zeros_like(large_matrix, dtype=bool)
    max_x, max_z = np.max(translated_vertices, axis=1)
    for i in range(len(translated_vertices[0]) - 1):
        x0, z0 = translated_vertices[:, i]
        x1, z1 = translated_vertices[:, i + 1]
        for x, z in src.helpers.bresenham_2d(x0, z0, x1, z1):
            secondary_large_matrix[x, z] = True
    # we should also connect the end to the beginning
    x0, z0 = translated_vertices[:, -1]
    x1, z1 = translated_vertices[:, 0]
    for x, z in src.helpers.bresenham_2d(x0, z0, x1, z1):
        secondary_large_matrix[x, z] = True
    # Now we need to find a starting point for the flood fill algorithm. We will use the find_starting_point function
    # for this.
    # we should only flood fill if the number of True points is greater than 8
    if np.sum(secondary_large_matrix) < 8 or np.all(secondary_large_matrix):
        return secondary_large_matrix
    starting_point = find_starting_point(secondary_large_matrix)
    if starting_point is None:
        # raise ValueError("No starting point found for flood fill algorithm.")
        return secondary_large_matrix
    x, z = starting_point
    secondary_large_matrix = boolean_flood_fill(secondary_large_matrix, max_x, max_z, x, z)
    return secondary_large_matrix  # We will have multiple secondary matrices that we will need to use to invert the
    # values of the large matrix. But this will need to be done in another function.


def polygon_divider(coordinates):
    """
    This function takes in a list of coordinates that define a polygon and returns a large matrix that is filled with
    True values where the polygon is. This large matrix can then be used to voxelize the polygon.
    :param coordinates: a list of coordinates that define a polygon
    :return: a large matrix that is filled with True values where the polygon is
    """
    # if it contains just one array, then it is a polygon. If it contains multiple arrays, then it is a multipolygon.
    # we need to voxelize this polygon
    large_matrix, min_x, min_z = primary_vertices_divider(coordinates[0])
    # we need to get the secondary vertices and invert the values of the large matrix. There may be some overlap between
    # some secondary vertices, so we'll want to take a union of all of them.

    if len(coordinates) > 1:
        secondary_matrices = []
        for secondary_vertices in coordinates[1:]:
            secondary_large_matrix = secondary_vertices_divider(secondary_vertices, large_matrix, min_x, min_z)
            secondary_matrices.append(secondary_large_matrix)
        # or them all together
        secondary_large_matrix = secondary_matrices[0]
        for matrix in secondary_matrices[1:]:
            secondary_large_matrix |= matrix
        # now if a value is true in the secondary matrix, we want to invert the value in the large matrix
        large_matrix[secondary_large_matrix] = False
    if min_z < 0:
        offset_min = min_x % 16, (min_z % 16)
    else:
        offset_min = min_x % 16, min_z % 16
    large_matrix = np.pad(large_matrix, ((offset_min[0], 0), (offset_min[1], 0)), mode="constant",
                          constant_values=False)
    # min_x was the offset to the actual world data from 0,0 of the matrix. Now that we've changed 0,0 we need to update
    # min_x and min_z
    min_x -= offset_min[0]
    min_z -= offset_min[1]

    # we need to cut off the bounds of some of the data as it goes outside the map
    if large_matrix.shape[0] + min_x > CUTOFF_MAX_X:
        large_matrix = large_matrix[:CUTOFF_MAX_X - min_x, :]
    if large_matrix.shape[1] + min_z > CUTOFF_MAX_Z:
        large_matrix = large_matrix[:, :CUTOFF_MAX_Z - min_z]
    return large_matrix, min_x, min_z
