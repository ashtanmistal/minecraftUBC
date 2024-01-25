"""
Places ocean at the appropriate y level and adds chunks as needed
"""

from amulet.api.block import Block
from amulet.api.chunk import Chunk
from amulet.api.errors import ChunkDoesNotExist
from tqdm import tqdm

from src.helpers import region_setup


def main():
    """
    Places ocean at the appropriate y level and adds chunks as needed.
    :return: None
    """
    # bedrock will be placed at y = -64
    # water from y = -63 to y = -58 (inclusive)
    bedrock_block = Block("minecraft", "bedrock")
    water_block = Block("minecraft", "water")
    cx, cx2, cz, cz2, level = region_setup()

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
