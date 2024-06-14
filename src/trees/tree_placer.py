import os
import amulet
import numpy as np
from amulet.api.block import Block
from amulet.api.errors import ChunkDoesNotExist
from amulet.utils import block_coords_to_chunk_coords
from tqdm import tqdm
import pandas as pd
from scipy.spatial import cKDTree
import pickle
from amulet_nbt import StringTag

"""
This script is very rough as it was done in a rush. There are thus improvements that can be made.
"""

csv_dir = r"C:\Users\Ashtan Mistal\OneDrive - UBC\School\2023S\minecraftUBC\resources\ubcv_campus_trees_processed.csv"
labels_dir = r"C:\Users\Ashtan Mistal\OneDrive - UBC\School\2023S\minecraftUBC\resources\clustered_points\predicted_labels.npy"
data_path = r"C:\Users\Ashtan Mistal\OneDrive - UBC\School\2023S\minecraftUBC\resources\clustered_points\processed_data_all.pkl"


game_version = ("java", (1, 20, 4))


def main(world_dir):
    """
    Places trees in the world. If there is a trunk in the CSV that is within 3m of a predicted tree,
    check if the tree is a Cherry tree. Else, check the label of the tree (0 is deciduous, 1 is coniferous).
    The points directory contains various datapoints of that tree; place the leaves and trunk (mean of the points, excluding y) in the world.
    :return: None
    """

    level = amulet.load_level(world_dir)

    deciduous_block = Block("minecraft", "oak_leaves", {"persistent": StringTag("true")})
    coniferous_block = Block("minecraft", "spruce_leaves", {"persistent": StringTag("true")})
    cherry_block = Block("minecraft", "cherry_leaves", {"persistent": StringTag("true")})

    air_block = Block("minecraft", "air")
    moss_block = Block("minecraft", "moss_block")
    iron_block = Block("minecraft", "iron_block")
    stone_bricks = Block("minecraft", "stone_bricks")

    # universal_deciduous_block, _, _ = level.translation_manager.get_version("java", (1, 20, 4)).block.to_universal(deciduous_block)
    # id_deciduous = level.block_palette.get_add_block(universal_deciduous_block)
    # universal_coniferous_block, _, _ = level.translation_manager.get_version("java", (1, 20, 4)).block.to_universal(coniferous_block)
    # id_coniferous = level.block_palette.get_add_block(universal_coniferous_block)
    # universal_cherry_block, _, _ = level.translation_manager.get_version("java", (1, 20, 4)).block.to_universal(cherry_block)
    # id_cherry = level.block_palette.get_add_block(universal_cherry_block)

    deciduous_trunk = Block("minecraft", "oak_log")
    coniferous_trunk = Block("minecraft", "spruce_log")
    cherry_trunk = Block("minecraft", "cherry_log")

    # universal_deciduous_trunk, _, _ = level.translation_manager.get_version("java", (1, 20, 4)).block.to_universal(deciduous_trunk)
    # id_deciduous_trunk = level.block_palette.get_add_block(universal_deciduous_trunk)
    # universal_coniferous_trunk, _, _ = level.translation_manager.get_version("java", (1, 20, 4)).block.to_universal(coniferous_trunk)
    # id_coniferous_trunk = level.block_palette.get_add_block(universal_coniferous_trunk)
    # universal_cherry_trunk, _, _ = level.translation_manager.get_version("java", (1, 20, 4)).block.to_universal(cherry_trunk)
    # id_cherry_trunk = level.block_palette.get_add_block(universal_cherry_trunk)



    csv_data = pd.read_csv(csv_dir, header=0)
    csv_tree_points = []
    is_cherry = []
    for row in csv_data.iterrows():
        xz = np.array([row[1]['X'], row[1]['Z']])
        # if row[1]['TAXA'].__contains__('Prunus'):
        if 'prunus' in row[1]['TAXA'].lower() or 'cherry' in str(row[1]['COMMON_NAME']).lower():
            is_cherry.append(True)
        else:
            is_cherry.append(False)
        csv_tree_points.append(xz)

    # make a kdtree of the tree points
    csv_tree_points = np.array(csv_tree_points)
    tree_kdtree = cKDTree(csv_tree_points)
    predicted_labels = np.load(labels_dir)
    predicted_labels = predicted_labels.flatten()  # flatten the labels

    points = pickle.load(open(data_path, "rb"))[0]

    for i in tqdm(range(len(points))):
        tree_points = points[i]
        pred_label = predicted_labels[i]

        # height = np.max(tree_points[:, 1]) - np.min(tree_points[:, 1])
        trunk_xz = np.mean(tree_points[:, [0, 2]], axis=0).astype(int)
        # the height is the max at the mean xz point
        points_at_mean_xz = tree_points[tree_points[:, 0].astype(int) == trunk_xz[0]]
        height = np.max(points_at_mean_xz[:, 1]) - np.min(points_at_mean_xz[:, 1])

        if pred_label == 0:
            block = deciduous_block
            trunk = deciduous_trunk
        else:
            block = coniferous_block
            trunk = coniferous_trunk

        # get the closest tree point in the CSV file
        _, idx = tree_kdtree.query(trunk_xz, distance_upper_bound=5, k=1)
        if idx < len(csv_tree_points) and is_cherry[idx]:
            block = cherry_block
            trunk = cherry_trunk

        # place the leaves

        starting_height = height.astype(int) + np.min(tree_points[:, 1]).astype(int)
        try:
            while level.get_version_block(trunk_xz[0], starting_height, trunk_xz[1], "minecraft:overworld",
                                          game_version)[0] in [air_block, iron_block, stone_bricks]:  # all the blocks that are ok to replace
                level.set_version_block(trunk_xz[0], starting_height, trunk_xz[1], "minecraft:overworld", game_version,
                                        trunk)
                starting_height -= 1
        except ChunkDoesNotExist:
            continue

        for point in tree_points:
            x, y, z = point[0].astype(int), point[1].astype(int), point[2].astype(int)
            # don't replace the trunk
            try:
                if level.get_version_block(x, y, z, "minecraft:overworld", game_version) == trunk:
                    continue
                level.set_version_block(x, y, z, "minecraft:overworld", game_version, block)
            except ChunkDoesNotExist:
                continue

    level.save()
    level.close()


if __name__ == "__main__":
    WORLD_DIR = r"C:\Users\Ashtan Mistal\OneDrive - UBC\School\2023S\minecraftUBC\world\TREES"
    main(WORLD_DIR)
