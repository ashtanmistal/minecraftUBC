import amulet
import numpy as np
from amulet.api.block import Block
from amulet.utils import block_coords_to_chunk_coords
from amulet_nbt import StringTag
from tqdm import tqdm

from scripts.helpers import convert_lat_long_to_x_z, WORLD_DIRECTORY

"""
This is a CLI for recoloring buildings. It works very similarly to the flood_block_replace.py script, except that
we don't want to just replace the block below the first air block -- we need to get all blocks that fit the criteria
that the user specifies. This is done by a modified flood fill. For a given x,z, we get all the blocks in the column
that fit the criteria. The block that's at the top of the column and fits the criteria is also added to the list of
roof blocks, and the others are added to the wall blocks. The [x,z] tuple is added to the visited list. 

Once we have the list of wall blocks and roof blocks, we can recolor them. The user specifies a separate replacement
block for the wall and roof blocks. 
"""

DEFAULT_FIND_BLOCKS = [
    Block("universal_minecraft", "bricks"),
    Block("universal_minecraft", "stone_bricks"),
    Block("universal_minecraft", "stone_bricks", {
        "variant": StringTag("normal")
    }),
    Block("universal_minecraft", "iron_block"),
    Block("universal_minecraft", "deepslate_tiles")]

MIN_HEIGHT = -34
MAX_HEIGHT = 95


def flood_replace(seed, level, find_blocks, replace_block, replace_roof_block):
    """
    This function works similarly to the flood void filler, except that the user can select what block they'd
    like to replace, and what block they'd like to replace it with. This is useful for replacing blocks that
    all have the incorrect block type within a certain region; the user can just block off the region manually
    and run this function. It will not replace void blocks, only blocks that are the same as the block_to_replace
    parameter.
    :param seed: Numpy coordinates (x,z) to fill in
    :param level: Amulet level object
    :param find_blocks: List of Block objects to replace
    :param replace_block: Block object to replace with
    :param replace_roof_block: Block object to replace roof blocks with
    :return: None
    """

    visited_points = []
    wall_blocks = []
    roof_blocks = []
    queue = [seed]
    # get the block ids for all the find and replace blocks
    find_block_ids = [level.block_palette.get_add_block(block) for block in find_blocks]
    wall_block, _, _ = level.translation_manager.get_version("java",
                                                             (1, 19, 4)).block.to_universal(
        replace_block)
    roof_block, _, _ = level.translation_manager.get_version("java",
                                                             (1, 19, 4)).block.to_universal(
        replace_roof_block)
    wall_block_id = level.block_palette.get_add_block(wall_block)
    roof_block_id = level.block_palette.get_add_block(roof_block)
    while len(queue) > 0:
        if len(visited_points) > 1000000:
            raise ValueError("Too many points to fill. Did you close off the region?")
        point = queue.pop()
        point = ([int(point[0]), int(point[1])])
        if point in visited_points:
            continue
        cx, cz = block_coords_to_chunk_coords(point[0], point[1])
        chunk = level.get_chunk(cx, cz, "minecraft:overworld")
        column = chunk.blocks[point[0] % 16, MIN_HEIGHT:MAX_HEIGHT, point[1] % 16]
        # get the indices of the blocks that match the find block ids
        # right now column is still a 3d array of shape=(1, max_height - min_height, 1), so we need to flatten it
        column = np.array(column).flatten()
        indices = np.where(np.isin(column, find_block_ids))
        # add all the blocks in the indices to the wall blocks, except for the top one
        if len(indices[0]) > 0:
            wall_blocks.extend([((point[0]), (MIN_HEIGHT + index), (point[1])) for index in indices[0][:-1]])
            # add the top block to the roof blocks

            roof_blocks.append(((point[0]), (MIN_HEIGHT + indices[0][-1]), (point[1])))
        else:
            continue  # if there are no blocks in the column that match the find block ids, we don't need to add
            # points to the queue
        # add the point to the visited points
        visited_points.append(point)
        # add the adjacent points to the queue
        x, z = point
        queue.extend([[x + 1, z], [x - 1, z], [x, z + 1], [x, z - 1]])
    print(f"Found {len(wall_blocks)} wall blocks and {len(roof_blocks)} roof blocks")
    # replace the wall blocks
    for wall_block in tqdm(wall_blocks):
        cx, cz = block_coords_to_chunk_coords(wall_block[0], wall_block[2])
        chunk = level.get_chunk(cx, cz, "minecraft:overworld")
        chunk.blocks[wall_block[0] % 16, wall_block[1], wall_block[2] % 16] = wall_block_id
        chunk.changed = True
    # replace the roof blocks
    for roof_block in tqdm(roof_blocks):
        cx, cz = block_coords_to_chunk_coords(roof_block[0], roof_block[2])
        chunk = level.get_chunk(cx, cz, "minecraft:overworld")
        chunk.blocks[roof_block[0] % 16, roof_block[1], roof_block[2] % 16] = roof_block_id
        chunk.changed = True


def main():
    """
    A very basic CLI for the flood fill function. This will be improved later.
    :return: None
    """
    replace_roof_block = Block("minecraft", "andesite")
    wall_block = Block("minecraft", "light_gray_concrete")
    while True:
        print("Please enter the coordinates of the starting seed for the flood fill")
        coords = input("Coordinates: ")
        # if the coordinates are lat/lon, convert them to x/z
        if "," in coords:
            coords = coords.split(",")
            coords = [float(coord) for coord in coords]
            coords = convert_lat_long_to_x_z(*coords)
            coords = list(coords)
        else:
            coords = coords.split(" ")
            if coords[0] == "/tp":
                coords = coords[1:]
            coords = [float(coord) for coord in coords]
            coords = coords[::2]
        level = amulet.load_level(WORLD_DIRECTORY)
        # wall_block = Block.from_string_blockstate(wall_block)
        # replace_roof_block = Block.from_string_blockstate(replace_roof_block)
        flood_replace(coords, level, DEFAULT_FIND_BLOCKS, wall_block, replace_roof_block)
        level.save()
        level.close()


if __name__ == "__main__":
    main()
