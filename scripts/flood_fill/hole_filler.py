import numpy as np
from amulet.api.block import Block
from tqdm import tqdm

from scripts.helpers import seed_setup, MIN_HEIGHT, GAME_VERSION


def hole_filler(points_to_fill, level, single=False):
    """
    This function is used to selectively fill in holes in a Minecraft world. It works by the user selecting a region
    to fill in (block coordinates), and performs a flood fill algorithm to detect nearby blocks. Once the void region
    is determined, the function will fill in the void with stone blocks, using a weighted average of the 3 nearest
    wall blocks to determine the height of the void.
    :param points_to_fill: Numpy coordinates (x,z) to fill in
    :param level: Amulet level object
    :param single: If True, will use tqdm to show progress. If False, will not show progress.
    :return: None
    """
    max_height = 45
    default_block = Block("minecraft", "stone")

    visited_points = []
    queue = [points_to_fill]
    wall_blocks = []
    while len(queue) > 0:
        # if we have an extremely large amount of points to fill we've likely reached a void ocean. This will run
        # forever, so we'll just stop it here.
        if len(visited_points) > 1000000:
            raise Exception("Too many points to fill. Likely reached a void ocean.")
        point = queue.pop()
        point = ([int(point[0]), int(point[1])])
        block, _ = level.get_version_block(point[0], MIN_HEIGHT, point[1], "minecraft:overworld", GAME_VERSION)
        if block.base_name == "air" and point not in visited_points:
            visited_points.append(point)
            queue.append(point + np.array([1, 0]))
            queue.append(point + np.array([-1, 0]))
            queue.append(point + np.array([0, 1]))
            queue.append(point + np.array([0, -1]))
        elif block.base_name == "stone":
            wall_blocks.append(point)
    if single:
        print("Found {} wall blocks".format(len(wall_blocks)))
    # Now that we have a set of the points to fill in, we need to figure out the height of each point. We'll base it off
    # of the weighted average of the 3 nearest wall blocks.
    wall_heights = []
    for point in wall_blocks:
        height = MIN_HEIGHT
        while height < max_height:
            block, _ = level.get_version_block(point[0], height, point[1], "minecraft:overworld", GAME_VERSION)
            if block.base_name != "stone":
                wall_heights.append(height - 1)
                break
            height += 1

    if single:
        point_iterator = tqdm(visited_points)
    else:
        point_iterator = visited_points
    for point in point_iterator:
        nearest_indices = np.argsort(np.linalg.norm(np.array(wall_blocks) - point, axis=1))[:3]
        nearest_points = np.array(wall_blocks)[nearest_indices]
        heights = np.array(wall_heights)[nearest_indices]
        weights = 1 / (np.linalg.norm(nearest_points[:, 0:2] - point, axis=1) + 1) ** 2
        height = np.sum(weights * heights) / np.sum(weights)
        for y in range(MIN_HEIGHT, int(height)):
            level.set_version_block(point[0], y, point[1], "minecraft:overworld", GAME_VERSION, default_block)
        wall_blocks.append(point)
        wall_heights.append(height)

    if single:
        print("Finished filling in void")


def main():
    """
    A simple wrapper function to call hole_filler.py
    :return: None
    """
    while True:
        level, points_to_fill = seed_setup()
        hole_filler(points_to_fill, level, single=True)
        level.save()
        level.close()


if __name__ == "__main__":
    main()
