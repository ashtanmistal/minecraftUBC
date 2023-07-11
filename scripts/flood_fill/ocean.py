"""
Places ocean at the appropriate y level and adds chunks as needed
"""

import amulet
import numpy as np
from amulet.api.block import Block
from amulet.api.chunk import Chunk
from amulet.api.errors import ChunkDoesNotExist
from tqdm import tqdm
from amulet.utils import block_coords_to_chunk_coords


def main():
    # bedrock will be placed at y = -64
    # water from y = -63 to y = -58 (inclusive)
    bedrock_block = Block("minecraft", "bedrock")
    water_block = Block("minecraft", "water")
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
            try:
                chunk = level.get_chunk(chunk_x, chunk_z, "minecraft:overworld")
            except ChunkDoesNotExist:
                chunk = Chunk(chunk_x, chunk_z)
            universal_bedrock, _, _ = level.translation_manager.get_version("java", (1, 19, 4)).block.to_universal(
                bedrock_block)
            universal_water, _, _ = level.translation_manager.get_version("java", (1, 19, 4)).block.to_universal(
                water_block)
            bedrock_id = level.block_palette.get_add_block(universal_bedrock)
            water_id = level.block_palette.get_add_block(universal_water)
            # we want to replace all zero blocks at y = -64 with bedrock
            # we want to replace all blocks from y = -63 to y = -58 with water
            for x in range(16):
                for z in range(16):
                    if chunk.blocks[x, -64, z] == 0:
                        chunk.blocks[x, -64, z] = bedrock_id
                    for y in range(-63, -57):
                        if chunk.blocks[x, y, z] == 0:
                            chunk.blocks[x, y, z] = water_id
            level.put_chunk(chunk, "minecraft:overworld")
            chunk.changed = True
    level.save()
    level.close()


if __name__ == "__main__":
    while True:
        main()
