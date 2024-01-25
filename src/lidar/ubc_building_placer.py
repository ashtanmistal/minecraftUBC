import amulet
import numpy as np
from amulet.api.block import Block
from amulet.utils.world_utils import block_coords_to_chunk_coords
from tqdm import tqdm

import src.helpers

BUILDING_BLOCKS = {
    "bricks": Block("minecraft", "bricks"),
    "stone bricks": Block("minecraft", "stone_bricks"),
    "iron block": Block("minecraft", "iron_block"),
    "deepslate tiles": Block("minecraft", "deepslate_tiles"),
}

BUILDING_BLOCKS_TEXTURES = {
    block: src.helpers.get_average_rgb(block_object) for block, block_object in BUILDING_BLOCKS.items()
}
BUILDING_LABEL = 6


def transform_chunk(data, level):
    """
    This transforms a slice of LiDAR data that is particular to a given chunk, estimates the best block to place for a
    given square meter, and places it.
    :param data: The LiDAR data to transform
    :param level: Amulet level object
    :return: None
    """
    chunk_data_x, chunk_data_y, chunk_data_z, chunk_data_red, chunk_data_green, chunk_data_blue = data
    if len(chunk_data_x) == 0 or len(chunk_data_y) == 0 or len(chunk_data_z) == 0:
        return

    # now we need to group the data into meter sized cubes
    unique_x, x_indices = np.unique(chunk_data_x, return_index=True)
    unique_y, y_indices = np.unique(chunk_data_y, return_index=True)
    unique_z, z_indices = np.unique(chunk_data_z, return_index=True)
    chunk_x, chunk_z = block_coords_to_chunk_coords(unique_x[0], unique_z[0])
    chunk = level.get_chunk(chunk_x, chunk_z, "minecraft:overworld")

    for i, j, k in np.ndindex(len(unique_x), len(unique_y), len(unique_z)):
        matching_indices = np.where(
            (chunk_data_x == unique_x[i]) & (chunk_data_y == unique_y[j]) & (chunk_data_z == unique_z[k]))
        offset_x, offset_z = unique_x[i] - chunk_x * 16, unique_z[k] - chunk_z * 16
        if matching_indices[0].size == 0 or chunk.blocks[int(offset_x), int(unique_y[j]), int(offset_z)] != 0:
            continue
        # now we have all the points that are in the same meter cube
        # we need to find the average color, but this time we'll normalize the color to get rid of shadows
        # this average color will be matched to a block from the selection above
        average_color = np.mean(np.array(
            [chunk_data_red[matching_indices], chunk_data_green[matching_indices], chunk_data_blue[matching_indices]]),
                                axis=1)
        mapped_color = min(BUILDING_BLOCKS_TEXTURES, key=lambda b: np.linalg.norm(BUILDING_BLOCKS_TEXTURES[b] -
                                                                                  average_color))
        mapped_block = BUILDING_BLOCKS[mapped_color]

        universal_block, universal_block_entity, universal_extra = level.translation_manager.get_version("java", (
            1, 19, 4)).block.to_universal(mapped_block)
        block_id = level.block_palette.get_add_block(universal_block)
        chunk.blocks[int(offset_x), int(unique_y[j]), int(offset_z)] = block_id
    chunk.changed = True


def transform_dataset(dataset, _):
    level = amulet.load_level(src.helpers.WORLD_DIRECTORY)
    red, green, blue = (dataset.red / 256).astype(int), (dataset.green / 256).astype(int), (
            dataset.blue / 256).astype(int)
    indices = np.where(dataset.classification == 6)
    if len(indices[0]) == 0:
        return
    filtered_red, filtered_green, filtered_blue = red[indices], green[indices], blue[indices]
    max_x, max_z, min_x, min_z, rounded_x, rounded_y, rounded_z = src.helpers.preprocess_dataset(dataset,
                                                                                                 BUILDING_LABEL)

    for chunk_x in tqdm(range(min_x.astype(int), max_x.astype(int), 16)):
        for chunk_z in range(min_z.astype(int), max_z.astype(int), 16):
            chunk_indices = np.where((rounded_x >= chunk_x) & (rounded_x < chunk_x + 16) & (rounded_z >= chunk_z) & (
                    rounded_z < chunk_z + 16))
            chunk_data = np.array(
                [rounded_x[chunk_indices], rounded_y[chunk_indices], rounded_z[chunk_indices],
                 filtered_red[chunk_indices],
                 filtered_green[chunk_indices],
                 filtered_blue[chunk_indices]])
            transform_chunk(chunk_data, level)
    level.save()
    level.close()


if __name__ == "__main__":
    src.helpers.dataset_iterator(transform_dataset)
