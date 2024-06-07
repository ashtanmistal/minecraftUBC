import os
import shutil

import amulet
import numpy as np
import pylas
from amulet.api.block import Block
from amulet.utils import block_coords_to_chunk_coords
from scipy.spatial import cKDTree
from tqdm import tqdm

import src.helpers
from src.helpers import INVERSE_ROTATION_MATRIX, BLOCK_OFFSET_X, BLOCK_OFFSET_Z, HEIGHT_OFFSET

BUILDING_BLOCKS = {
    "stone bricks": Block("minecraft", "stone_bricks"),
    "iron block": Block("minecraft", "iron_block"),
}
BUILDING_BLOCKS_TEXTURES = {
    block: src.helpers.get_average_rgb(block_object) for block, block_object in BUILDING_BLOCKS.items()
}

OBJ_DIRECTORY = (r"C:\Users\Ashtan Mistal\OneDrive - "
                 r"UBC\School\2023W1\CPSC533Y\Project\LiDAR-DenseSeg\src\classification\pointnet2-ubc-semseg\log"
                 r"\sem_seg\merged\visual\data\buildings_split")  # damn that's a long path
LAS_DIRECTORY = r"C:\Users\Ashtan Mistal\OneDrive - UBC\School\2023S\minecraftUBC\resources\las"  # TODO make relative

OUTLIER_THRESHOLD = 100
OUTLIER_RADIUS = 1.4
TRUNCATION_RADIUS = 0.2
TRUNCATION_THRESHOLD = 0.6


def process_obj(obj_file, level):
    """
    This function processes the .obj files outputted by the deep learning model into a voxelized point cloud.
    :param obj_file: The .obj file to process
    :param level: The Amulet level object to place the buildings in
    :return: None
    """
    # read the .obj file
    # each line is "v 2954.938307 95.129650 97.216000 255 255 255"
    # where the first three numbers are the x, y, z coordinates, and the last three numbers are the RGB values

    with open(obj_file, 'r') as file:
        lines = file.readlines()

    size = len(lines)
    # create a size x 6 array to store the points
    points = np.empty((size, 6), dtype=float)
    for i, line in enumerate(lines):
        if line.startswith('v '):
            parts = line.split()
            x, y, z = map(float, parts[1:4])
            y = -y
            r, g, b = map(int, parts[4:7])
            points[i] = [x, y, z, r, g, b]
    process_points(points, level, os.path.basename(obj_file))


def process_las(las_file, level):
    """
    Reads an LAS file and performs the same processing as process_obj
    :param las_file: basename of the LAS file to process
    :param level: Amulet level object
    :return: None
    """
    dataset = pylas.read(las_file)
    xyz = np.matmul(INVERSE_ROTATION_MATRIX, np.array([dataset.x - BLOCK_OFFSET_X,
                                                       dataset.z - BLOCK_OFFSET_Z,
                                                       dataset.y - HEIGHT_OFFSET]))
    points = np.vstack([xyz, dataset.red, dataset.green, dataset.blue]).T
    process_points(points, level, os.path.basename(las_file))


def process_points(points, level, basename):
    """
    This function processes the points in the point cloud to place the buildings in the level.
    :param points: Nx6 array of points
    :param level: Amulet level object
    :param basename: The name of the file being processed (for logging purposes)
    :return: None
    """
    size = len(points)
    tree = cKDTree(points[:, :2])

    # rejecting outlier points: for each point, find the nearest neighbours within a radius of 1.5 meters
    # if the number of neighbours is less than OUTLIER_THRESHOLD, reject the point

    rejects = np.zeros(size, dtype=bool)
    for i in range(size):
        point = points[i]
        neighbours = tree.query_ball_point(point[:2], OUTLIER_RADIUS, workers=-1, p=2)
        if len(neighbours) < OUTLIER_THRESHOLD:
            rejects[i] = True

    # print(f"Rejecting {np.sum(rejects)} points as outliers out of {size} points")
    if np.sum(rejects) == size:
        print(f"Warning: All points in {basename} were rejected during outlier detection")
        return

    points = points[~rejects]
    size = len(points)

    tree = cKDTree(points[:, :3])

    # let's try to reject points that cause truncation errors.
    # Check the neighbours within a 0.2m radius. If the majority get rounded to a different voxel, reject the point
    rejects = np.zeros(size, dtype=bool)
    for i in range(size):
        point = points[i]
        neighbours = tree.query_ball_point(point[:3], TRUNCATION_RADIUS, workers=-1, p=2)
        neighbour_points = points[neighbours]
        neighbour_points_rounded = np.round(neighbour_points[:, :3], 0)
        rounded_point = np.round(point[:3], 0)
        if np.sum(np.all(neighbour_points_rounded == rounded_point, axis=1)) < len(neighbours) * TRUNCATION_THRESHOLD:
            rejects[i] = True

    print(f"Rejecting {np.sum(rejects)} points due to truncation errors out of {size} points")
    points = points[~rejects]
    size = len(points)

    if size == 0:
        print(f"Warning: All points in {basename} were rejected during truncation error check")
        return

    # placing the buildings in the level
    # switch the Y and Z coordinates to match the Minecraft coordinate system
    points_x, points_y, points_z = np.round(points[:, 0]).astype(int), np.round(points[:, 2]).astype(int), np.round(
        points[:, 1]).astype(int)
    points_y -= HEIGHT_OFFSET
    points_red, points_green, points_blue = np.round(points[:, 3]).astype(int), np.round(points[:, 4]).astype(
        int), np.round(points[:, 5]).astype(int)
    min_x, max_x = np.floor(np.min(points_x) / 16) * 16, np.ceil(np.max(points_x) / 16) * 16
    min_z, max_z = np.floor(np.min(points_z) / 16) * 16, np.ceil(np.max(points_z) / 16) * 16

    rejected = 0

    for chunk_block_x in range(min_x.astype(int), max_x.astype(int), 16):
        for chunk_block_z in range(min_z.astype(int), max_z.astype(int), 16):
            points_in_chunk = np.where(
                (points_x >= chunk_block_x) & (points_x < chunk_block_x + 16) & (points_z >= chunk_block_z) & (
                        points_z < chunk_block_z + 16))
            if len(points_in_chunk[0]) == 0:
                continue
            chunk_data = np.array([points_x[points_in_chunk], points_y[points_in_chunk], points_z[points_in_chunk],
                                   points_red[points_in_chunk], points_green[points_in_chunk],
                                   points_blue[points_in_chunk]])
            chunk = level.get_chunk(*block_coords_to_chunk_coords(chunk_block_x, chunk_block_z), "minecraft:overworld")
            min_y, max_y = np.min(chunk_data[1]), np.max(chunk_data[1])
            chunk_data[1] -= min_y
            height_offset = min_y
            chunk_color_matrix = np.zeros((16, max_y - min_y + 1, 16, 3), dtype=float)
            chunk_color_count = np.zeros((16, max_y - min_y + 1, 16), dtype=int)

            # convert x,y,z to int
            for i in range(len(chunk_data[0])):
                x, y, z, r, g, b = chunk_data[:, i]
                chunk_color_matrix[x - chunk_block_x, y, z - chunk_block_z] += [r, g, b]
                chunk_color_count[x - chunk_block_x, y, z - chunk_block_z] += 1

            for x, y, z in np.ndindex(16, max_y - min_y + 1, 16):
                if chunk_color_count[x, y, z] == 0:
                    continue
                # check neighbouring blocks in the xz plane for stray blocks
                if x > 0:  # no need to check y bounds; all points are above ground + height offset is not yet applied
                    if z > 0:
                        if np.sum(chunk_color_count[x - 1:x + 2, y - 1:y + 2, z - 1:z + 2] > 0) < 4:
                            rejected += 1
                            continue
                    else:

                        if np.sum(chunk_color_count[x - 1:x + 2, y - 1:y + 2, z:z + 2] > 0) < 2:
                            rejected += 1
                            continue
                else:
                    if z > 0:
                        if np.sum(chunk_color_count[x:x + 2, y - 1:y + 2, z - 1:z + 2] > 0) < 2:
                            rejected += 1
                            continue
                    else:
                        # along chunk boundary. can't reject
                        pass
                average_color = chunk_color_matrix[x, y, z] / chunk_color_count[x, y, z]
                mapped_color = min(BUILDING_BLOCKS,
                                   key=lambda b: np.linalg.norm(BUILDING_BLOCKS_TEXTURES[b] - average_color))
                mapped_block = BUILDING_BLOCKS[mapped_color]
                universal_block, universal_block_entity, universal_extra = level.translation_manager.get_version("java",
                                                                                                                 (1, 20,
                                                                                                                  4)).block.to_universal(
                    mapped_block)
                block_id = level.block_palette.get_add_block(universal_block)
                chunk.blocks[x, y + height_offset, z] = block_id
            chunk.changed = True

    print(f"Rejected {rejected} blocks due to insufficient neighbours out of {size} blocks")
    if rejected / size > 0.01:
        print(f"Warning: Neighbour algorithm rejected more than 1% of the blocks in {basename}")


def main():
    start_from_scratch = True  # variable to assist with debugging. Set to True by default
    if start_from_scratch:
        if os.path.exists("../world/BUILDINGS"):
            shutil.rmtree("../world/BUILDINGS")
        shutil.copytree("../world/STREETLIGHTS", "../world/BUILDINGS")

    files_to_process = []

    for filename in os.listdir(OBJ_DIRECTORY):
        if filename.endswith("_pred.obj"):
            obj_file = os.path.join(OBJ_DIRECTORY, filename)
            files_to_process.append(obj_file)

    for filename in tqdm(files_to_process):
        level = amulet.load_level("../world/BUILDINGS")
        process_obj(filename, level)
        # import pdb; pdb.set_trace()
        level.save()
        level.close()

    print("Buffer Buildings placed in world/BUILDINGS. Processing remaining buildings...")

    las_files = ["merged_pip.las", "merged_raw.las"]
    for filename in tqdm(las_files):
        level = amulet.load_level("../world/BUILDINGS")
        process_las(os.path.join(LAS_DIRECTORY, filename), level)
        level.save()
        level.close()


if __name__ == "__main__":
    main()
