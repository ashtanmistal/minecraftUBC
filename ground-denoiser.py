#  Ground denoising algorithm for pre-existing Minecraft world
#  written by: Ashtan Mistal

from amulet.api.block import Block
import amulet
import os
import time
from amulet.api.chunk import Chunk
from amulet.api.errors import ChunkDoesNotExist, ChunkLoadError
from amulet.utils.world_utils import block_coords_to_chunk_coords
from amulet.api.selection import SelectionBox
import tqdm

# This algorithm is designed to take a pre-existing Minecraft world (here, a world that was built by transforming
# LiDAR data). We have specific block types that were recognised as ground material during the transformation of the
# LiDAR data, but due to inherent noise in the data, some de-noising (removing void) is required. This algorithm is
# designed to remove the void from ground blocks that are surrounded or nearly surrounded by other ground blocks.


# This is done by checking the 8 neighboring blocks in a given height layer, and if `x` or more of them are ground
# blocks, the center block is also considered a ground block. As a result we want to ignore any other block
# within this 8 block radius that is not a ground block (should not count towards the `x` or more ground
# blocks). This algorithm is designed to be run on a single height layer at a time, and will work on a given chunk by
# filtering out all non-ground blocks, and then running the algorithm on the remaining ground blocks. This algorithm
# is designed to be run on a single chunk at a time, and will be run on all chunks in a given world. The blocks on
# the edges of the chunk will be ignored for now. If needed for additional de-noising, we can consider the
# neighboring chunks as well such that these edge cases can be effectively de-noised.

# We will also de-noise the stone inside moss, moss inside stone, etc. Basically if enough blocks around a given
# block are of a different type, we will change the block to be of that type. This will be done after the initial
# de-noising of the ground blocks.


ground_blocks = {
    "dirt": Block("minecraft", "dirt"),
    "stone": Block("minecraft", "stone"),
    "moss block": Block("minecraft", "moss_block"),
}

level = amulet.load_level("world/UBC")

min_ground_blocks = 6  # 6 out of 8 blocks must be ground blocks for a block to be considered a ground block


# TODO ignore all blocks below y = -55 (y = -56 and below are all superflat generated terrain)


def ground_denoiser_neighbour(box):
    """
    This function takes a selection box and runs the ground denoiser algorithm on the blocks within the box.
    :param box: SelectionBox object
    :return: None
    """

    # get the block data from the world that belongs in the box
    blocks = level.get_coord_box("minecraft:overworld", box, False)

    # iterate through all the chunks in the box





selection = SelectionBox((0, 0, 0), (16, 256, 16))
ground_denoiser_neighbour(selection)
level.save()
level.close()