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
