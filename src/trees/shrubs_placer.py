import os
from collections import defaultdict

import amulet
import numpy as np
import pylas
from amulet.api.block import Block
from amulet.api.errors import ChunkDoesNotExist
from amulet.utils import block_coords_to_chunk_coords
from tqdm import tqdm
from src.helpers import INVERSE_ROTATION_MATRIX, BLOCK_OFFSET_X, BLOCK_OFFSET_Z, HEIGHT_OFFSET
from amulet_nbt import StringTag

DENSITY_THRESHOLD_LOW = 3
DENSITY_THRESHOLD_HIGH = 20
LAS_DIRECTORY = r"C:\Users\Ashtan Mistal\OneDrive - UBC\School\2023S\minecraftUBC\resources\las"

def process_las(las_file, level):
    """
    Reads an LAS file and places the low shrubs in the world as per process_points.
    :param las_file: basename of the LAS file to process
    :param level: Amulet level object
    :return: None
    """
    dataset = pylas.read(las_file)
    labels = dataset.classification
    labels_to_delete = np.where(labels != 3)
    x = dataset.x
    y = dataset.y
    z = dataset.z
    x = np.delete(x, labels_to_delete)
    y = np.delete(y, labels_to_delete)
    z = np.delete(z, labels_to_delete)
    if len(x) == 0:
        return
    xyz = np.matmul(INVERSE_ROTATION_MATRIX, np.array([x - BLOCK_OFFSET_X,
                                                       y - BLOCK_OFFSET_Z,
                                                       z]))
    xyz[1] = -xyz[1]  # match the Minecraft coordinate system
    process_points(xyz, level, os.path.basename(las_file))

def process_points(points, level, basename):
    azalea_leaves = Block("minecraft", "flowering_azalea_leaves", {"persistent": StringTag("true")})
    grass = Block("minecraft", "short_grass")
    moss_block = Block("minecraft", "moss_block")
    grass_block = Block("minecraft", "grass_block")

    universal_azalea, _, _ = level.translation_manager.get_version("java", (1, 20, 4)).block.to_universal(azalea_leaves)
    id_azalea = level.block_palette.get_add_block(universal_azalea)
    universal_grass, _, _ = level.translation_manager.get_version("java", (1, 20, 4)).block.to_universal(grass)
    id_grass = level.block_palette.get_add_block(universal_grass)
    universal_moss_block, _, _ = level.translation_manager.get_version("java", (1, 20, 4)).block.to_universal(moss_block)
    id_moss_block = level.block_palette.get_add_block(universal_moss_block)
    universal_grass_block, _, _ = level.translation_manager.get_version("java", (1, 20, 4)).block.to_universal(grass_block)
    id_grass_block = level.block_palette.get_add_block(universal_grass_block)

    points_x = np.round(points[0, :]).astype(int)
    points_y = np.round(points[2, :]).astype(int) - HEIGHT_OFFSET
    points_z = np.round(points[1, :]).astype(int)

    min_x, max_x = np.floor(np.min(points_x) / 16) * 16, np.ceil(np.max(points_x) / 16) * 16
    min_z, max_z = np.floor(np.min(points_z) / 16) * 16, np.ceil(np.max(points_z) / 16) * 16

    chunk_bins = defaultdict(list)

    for i in range(len(points_x)):
        cx, cz = block_coords_to_chunk_coords(points_x[i], points_z[i])
        chunk_bins[(cx, cz)].append((points_x[i] - 16 * cx, points_y[i], points_z[i] - 16 * cz))

    total_rejected = 0

    for (cx, cz), chunk_data in tqdm(chunk_bins.items()):
        chunk_data = np.array(chunk_data).T
        try:
            chunk = level.get_chunk(cx, cz, "minecraft:overworld")
        except ChunkDoesNotExist:
            continue

        min_y, max_y = np.min(chunk_data[1]), np.max(chunk_data[1])
        y_range = max_y - min_y + 1

        occupied = np.zeros((16, y_range, 16), dtype=int)
        chunk_data[1] -= min_y

        np.add.at(occupied, (chunk_data[0], chunk_data[1], chunk_data[2]), 1)

        height_offset = min_y

        for x in range(16):
            for z in range(16):
                for y in range(y_range):
                    count = occupied[x, y, z]
                    if count == 0 or chunk.blocks[x, y + height_offset, z] != 0:  # skip if no points or already occupied
                        continue
                    if count < DENSITY_THRESHOLD_LOW:
                        total_rejected += 1
                    elif count < DENSITY_THRESHOLD_HIGH:
                        below_block = chunk.blocks[x, y + height_offset - 1, z]
                        if below_block == id_moss_block or below_block == id_grass_block:
                            chunk.blocks[x, y + height_offset, z] = id_grass
                    else:
                        # place until no longer air, max of 4m depth
                        cond = True
                        i = 0
                        while chunk.blocks[x, y + height_offset - i, z] == 0 and cond:
                            chunk.blocks[x, y + height_offset - i, z] = id_azalea
                            i += 1
                            if i == 4:
                                cond = False


        chunk.changed = True
    print(f"Rejected {total_rejected} points in {basename} out of {len(points_x)}")


def main(world_directory):
    # start_from_scratch = True  # variable to assist with debugging. Set to True by default
    # if start_from_scratch:
    #     if os.path.exists("../world/SHRUBS"):
    #         shutil.rmtree("../world/SHRUBS")
    #     shutil.copytree("../world/TRAILS", "../world/SHRUBS")

    for filename in os.listdir(LAS_DIRECTORY):
        if not filename.endswith(".las"):
            continue
        print(f"Processing {filename}")
        level = amulet.load_level(world_directory)
        process_las(os.path.join(LAS_DIRECTORY, filename), level)
        level.save()
        level.close()


if __name__ == "__main__":
    world_dir = r"C:\Users\Ashtan Mistal\OneDrive - UBC\School\2023S\minecraftUBC\world\SHRUBS"
    main(world_dir)
