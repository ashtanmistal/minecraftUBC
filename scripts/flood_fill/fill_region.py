"""
This script takes in a starting and end coordinate, and finds void regions within the selection. It then fills in the
void regions with stone blocks using hole_filler.py. It works by breaking the selection into 16x16 chunks, and then
iterating through each chunk and checking what blocks are void. If there is a void block it will call hole_filler.py to
fill in the void.
"""

import numpy as np
from amulet.api.block import Block
from tqdm import tqdm

from hole_filler import hole_filler
from scripts.helpers import region_setup


def main():
    min_height = -64
    air_block = Block("minecraft", "air")
    cx, cx2, cz, cz2, level = region_setup()

    for chunk_x in tqdm(range(cx, cx2 + 1)):
        for chunk_z in range(cz, cz2 + 1):
            chunk = level.get_chunk(chunk_x, chunk_z, "minecraft:overworld")
            universal_block, _, _ = level.translation_manager.get_version("java", (1, 19, 4)).block.to_universal(
                air_block)
            block_id = level.block_palette.get_add_block(universal_block)
            for x in range(16):
                for z in range(16):
                    if chunk.blocks[x, min_height, z] == block_id:
                        void_coords = np.array([chunk_x * 16 + x, chunk_z * 16 + z])
                        hole_filler(void_coords, level)
    level.save()
    level.close()


if __name__ == "__main__":
    while True:
        main()
