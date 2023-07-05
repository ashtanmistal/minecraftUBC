"""
This script takes in a starting and end coordinate, and finds void regions within the selection. It then fills in the
void regions with stone blocks using hole_filler.py. It works by breaking the selection into 16x16 chunks, and then
iterating through each chunk and checking what blocks are void. If there is a void block it will call hole_filler.py to
fill in the void.
"""

from hole_filler import hole_filler

import amulet
import numpy as np
from amulet.api.block import Block
from tqdm import tqdm
from amulet.utils import block_coords_to_chunk_coords


def main():
    min_height = -64
    air_block = Block("minecraft", "air")
    level = amulet.load_level("world/UBC")
    prompt = input("starting coordinate: ")
    start = prompt.split(" ")
    if start[0] == "/tp":
        start = start[1:]
    start = [float(coord) for coord in start]
    # we only need x and z; ignore y
    start = start[::2]
    start = np.array(start)
    prompt = input("ending coordinate: ")
    end = prompt.split(" ")
    if end[0] == "/tp":
        end = end[1:]
    end = [float(coord) for coord in end]
    end = end[::2]
    end = np.array(end)
    # get the chunk coordinates of the start and end points
    cx, cz = block_coords_to_chunk_coords(start[0], start[1])
    cx2, cz2 = block_coords_to_chunk_coords(end[0], end[1])
    if cx > cx2:
        cx, cx2 = cx2, cx
    if cz > cz2:
        cz, cz2 = cz2, cz

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
