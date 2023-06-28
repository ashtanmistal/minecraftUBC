# script to remove the void at the bottom of the world
# and replace it with a layer of bedrock at y=-64, and dirt from y=-63 to y=-61
import time

import amulet
from amulet.api.block import Block
from amulet.api.errors import ChunkDoesNotExist, ChunkLoadError
from amulet.utils.world_utils import block_coords_to_chunk_coords
from tqdm import tqdm

start_time = time.time()
game_version = ("java", (1, 19, 4))

bedrock = Block("minecraft", "bedrock")
dirt = Block("minecraft", "dirt")

x_min = 0
x_max = 5248
z_min = -2304
z_max = 2816

for x in tqdm(range(x_min, x_max, 16)):
    level = amulet.load_level("../world/UBC")
    for z in range(z_min, z_max, 16):
        cx, cz = block_coords_to_chunk_coords(x, z)
        try:
            chunk = level.get_chunk(cx, cz, "minecraft:overworld")
        except ChunkDoesNotExist:
            continue
        except ChunkLoadError:
            continue
        universal_bedrock, universal_bedrock_entity, universal_bedrock_extra = level.translation_manager.get_version("java", (
            1, 19, 4)).block.to_universal(bedrock)
        bedrock_block_id = level.block_palette.get_add_block(universal_bedrock)
        if chunk.blocks[0, -64, 0] == bedrock_block_id:
            continue
        chunk.blocks[:, -64, :] = bedrock_block_id
        universal_dirt, universal_dirt_entity, universal_dirt_extra = level.translation_manager.get_version("java", (
            1, 19, 4)).block.to_universal(dirt)
        dirt_block_id = level.block_palette.get_add_block(universal_dirt)
        chunk.blocks[:, -63:-61, :] = dirt_block_id
        level.put_chunk(chunk, "minecraft:overworld")
    level.save()
    level.close()
