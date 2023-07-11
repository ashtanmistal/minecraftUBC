import numpy as np
from amulet.api.block import Block
from tqdm import tqdm

from scripts.util import seed_setup


def flood_replace(seed, level, find_block, replace_block, min_height, max_height, game_version=("java", (1, 19, 4))):
    """
    This function works similarly to the flood void filler, except that the user can select what block they'd
    like to replace, and what block they'd like to replace it with. This is useful for replacing blocks that
    all have the incorrect block type within a certain region; the user can just block off the region manually
    and run this function. It will not replace void blocks, only blocks that are the same as the block_to_replace
    parameter.
    :param seed: Numpy coordinates (x,z) to fill in
    :param level: Amulet level object
    :param find_block: Block object to replace
    :param replace_block: Block object to replace with
    :param min_height: Minimum height to replace blocks at
    :param max_height: Maximum height to replace blocks at
    :param game_version: Game version tuple
    :return: None
    """

    find_block_base_name = find_block.base_name

    visited_points = []
    heights = []
    queue = [seed]
    while len(queue) > 0:
        if len(visited_points) > 1000000:
            raise Exception("Too many points to fill. Did you close off the region?")
        point = queue.pop()
        point = ([int(point[0]), int(point[1])])
        # find the height of the top block just before we reach air
        height = min_height
        block_at_height, _ = level.get_version_block(point[0], height, point[1], "minecraft:overworld", game_version)
        for y in range(min_height, max_height):
            block, _ = level.get_version_block(point[0], y, point[1], "minecraft:overworld", game_version)
            if block.base_name == "air":
                break
            height = y
            block_at_height = block
        if block_at_height.base_name == find_block_base_name and point not in visited_points:
            visited_points.append(point)
            heights.append(height)
            queue.append(point + np.array([1, 0]))
            queue.append(point + np.array([-1, 0]))
            queue.append(point + np.array([0, 1]))
            queue.append(point + np.array([0, -1]))
    print("Found {} blocks to replace".format(len(visited_points)))

    for point, height in tqdm(zip(visited_points, heights)):
        # replace_block = random.choices(
        #     [Block("minecraft", "moss_block"), Block("minecraft", "dirt"), Block("minecraft", "grass_block")],
        #     weights=[0.6, 0.1, 0.3],
        #     k=1
        # )[0]
        level.set_version_block(point[0], height, point[1], "minecraft:overworld", game_version, replace_block)
    print("Finished replacing blocks")


def main():
    while True:
        level, points_to_fill = seed_setup()
        input_block = Block("minecraft", "smooth_red_sandstone")
        output_block = Block("minecraft", "dirt")
        min_height = input("Enter the minimum height to replace blocks at: ")
        max_height = input("Enter the maximum height to replace blocks at: ")
        flood_replace(points_to_fill, level, input_block, output_block, int(min_height), int(max_height))
        level.save()
        level.close()


if __name__ == "__main__":
    main()
