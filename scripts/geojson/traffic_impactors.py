"""
This script transforms the traffic impactors data inside a geojson file into the Minecraft world.
It finds the side of the road and places relevant things such as stop signs, yield signs, and traffic lights.
"""

import json

import amulet
import numpy as np
from amulet import Block
from amulet.api.errors import ChunkDoesNotExist
from amulet.utils import block_coords_to_chunk_coords
from tqdm import tqdm

from scripts.util import bresenham_2d, convert_lat_long_to_x_z

game_version = ("java", (1, 19, 4))

json_path = "/resources/BC_Road_Data_Selected.geojson"

MAX_PERPENDICULAR_SEARCH_DISTANCE = 20
IMPACTOR_DISTANCE = 10
min_height = -40
max_height = 50

yield_sign = [
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "target"),
]

dead_end_sign = [
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "yellow_concrete"),
]

stop_sign = [
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "red_concrete"),
]

traffic_light_vertical = [  # just the stick part of the traffic light
    Block("minecraft", "pink_wool")  # we'll just do the traffic lights manually as it'll take less time than debugging
]

height_blocks_ignore = [
    Block("minecraft", "red_concrete"),
    Block("minecraft", "yellow_concrete"),
    Block("minecraft", "green_concrete"),
    Block("minecraft", "polished_blackstone"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "target"),
]

road_materials = [
    "gray_concrete",
    "gray_concrete_powder",
    "white_concrete",
]

bollards = [
    Block("minecraft", "polished_blackstone_wall"),
]  # we don't need to place a lantern here as all lit bollards are placed in the streetlight handler

traffic_impactor_translation = {
    "C": None,  # cul-de-sac
    "L": traffic_light_vertical,
    # This is a traffic light and needs to be handled differently; this will get caught in the main function here
    "O": None,  # overpass
    "R": yield_sign,  # vehicles must yield to traffic in the roundabout
    "S": stop_sign,
    "U": None,  # underpass
    "Y": yield_sign,
    "G": None,  # community gate - this is horizontal and will also need to be handled differently
    "B": bollards,
    "M": bollards,  # represents a gate or bollards that restrict access to a pedestrian mall
    "T": None,  # there are no toll booths in the area
    "D": dead_end_sign,
}


def vertical_traffic_impactor_placer(level, x, y, z, sign_type):
    """
    This function places regular (i.e. purely vertical) traffic impactors in the world.
    More complex traffic impactors, such as streetlights, need to be handled separately.
    :param level: the Amulet level object
    :param x: x coordinate of the traffic impactor
    :param y: y coordinate of the traffic impactor
    :param z: z coordinate of the traffic impactor
    :param sign_type: the type of traffic impactor to place (string, 1 character)
    :return: None
    """
    if y is None:
        return None
    blocks = traffic_impactor_translation[sign_type]
    for i, block in enumerate(blocks):
        level.set_version_block(int(x), int(y) + i + 1, int(z), "minecraft:overworld", game_version, block)

    return None


def find_road_edge(from_x, from_z, to_x, to_z, direction, level):
    """
    Draws a line perpendicular to the vector from (from_x, from_z) to (to_x, to_z), and finds the furthest block
    that is of a road type. This is used to find the edge of the road at the "to" point. Only searches to the extent
    of MAX_PERPENDICULAR_SEARCH_DISTANCE to avoid taking into account another road.
    :param from_x: x coordinate of the beginning of the line
    :param from_z: z coordinate of the beginning of the line
    :param to_x: x coordinate of the end of the line; this is where we will search for the road edge
    :param to_z: z coordinate of the end of the line; this is where we will search for the road edge
    :param direction: Whether to search in the right or left direction
    :param level: the Amulet level object
    :return: (x,y,z) of the furthest road material block in the direction specified
    """
    if from_x == to_x and from_z == to_z:
        return from_x, get_height(from_x, from_z, level), from_z
    # find the direction of the line from (from_x, from_z) to (to_x, to_z)
    direction_vector = np.array([to_x - from_x, to_z - from_z])
    direction_vector = direction_vector / np.linalg.norm(direction_vector)
    # find the perpendicular vector
    if direction == "right":
        perpendicular_vector = np.array([-direction_vector[1], direction_vector[0]])
    elif direction == "left":
        perpendicular_vector = np.array([direction_vector[1], -direction_vector[0]])
    else:
        raise ValueError("Direction must be either 'right' or 'left'")
    # the magnitude of this line is MAX_PERPENDICULAR_SEARCH_DISTANCE
    end_search_x = to_x + perpendicular_vector[0] * MAX_PERPENDICULAR_SEARCH_DISTANCE
    end_search_z = to_z + perpendicular_vector[1] * MAX_PERPENDICULAR_SEARCH_DISTANCE
    search_blocks = bresenham_2d(to_x, to_z, end_search_x, end_search_z)
    for (x, z) in search_blocks:
        height = get_height(x, z, level)
        if height is None:
            continue
        block, _ = level.get_version_block(x, height, z, "minecraft:overworld", game_version)
        if block.base_name in road_materials:
            continue
        else:
            return x, height, z
    return search_blocks[-1][0], get_height(search_blocks[-1][0], search_blocks[-1][1], level), search_blocks[-1][1]


def traffic_light_handler(from_x, from_z, to_x, to_z, level):
    # First we need to find the road edge to the right
    right_edge_x, right_edge_y, right_edge_z = find_road_edge(from_x, from_z, to_x, to_z, "right", level)
    # we'll also need the left edge to know where the streetlights end
    left_edge_x, left_edge_y, left_edge_z = find_road_edge(from_x, from_z, to_x, to_z, "left", level)
    if right_edge_y is None or left_edge_y is None:
        return None
    height = right_edge_y + len(traffic_light_vertical)
    streetlight_blocks = bresenham_2d(right_edge_x, right_edge_z, left_edge_x, left_edge_z)
    vertical_traffic_impactor_placer(level, right_edge_x, right_edge_y, right_edge_z, "L")
    if len(streetlight_blocks) >= 6:
        # We want to divide the streetlights into quarters. The block at the first and third quarter will be a
        # yellow light. The red and green lights will be placed on either side of the yellow light.
        # the rest is polished blackstone
        first_quartile_index = int(len(streetlight_blocks) / 4)
        third_quartile_index = int(3 * len(streetlight_blocks) / 4)
        for i, (x, z) in enumerate(streetlight_blocks):
            # if a block already exists there we don't want to overwrite it
            cur_block, _ = level.get_version_block(
                int(x), int(height), int(z), "minecraft:overworld", game_version
            )
            if cur_block.base_name != "minecraft:air":
                continue
            if i == first_quartile_index or i == third_quartile_index:
                level.set_version_block(
                    int(x),
                    int(height + 1),
                    int(z),
                    "minecraft:overworld",
                    game_version,
                    Block("minecraft", "yellow_concrete"),
                )
            elif i == first_quartile_index - 1 or i == third_quartile_index - 1:
                level.set_version_block(
                    int(x),
                    int(height + 1),
                    int(z),
                    "minecraft:overworld",
                    game_version,
                    Block("minecraft", "red_concrete"),
                )
            elif i == first_quartile_index + 1 or i == third_quartile_index + 1:
                level.set_version_block(
                    int(x),
                    int(height + 1),
                    int(z),
                    "minecraft:overworld",
                    game_version,
                    Block("minecraft", "green_concrete"),
                )
            else:
                level.set_version_block(
                    int(x),
                    int(height),
                    int(z),
                    "minecraft:overworld",
                    game_version,
                    Block("minecraft", "polished_blackstone"),
                )

    else:
        # not enough space for a horizontal traffic light, so we'll place the lights vertically instead
        to_place = [
            Block("minecraft", "lime_concrete"),
            Block("minecraft", "yellow_concrete"),
            Block("minecraft", "red_concrete"),
        ]
        # we want to place two blackstone blocks before placing the vertical traffic light, so we'll append two
        # blackstone blocks to the beginning of the list
        to_place = [Block("minecraft", "polished_blackstone")] * 4 + to_place
        for i, block in enumerate(to_place):
            level.set_version_block(
                int(right_edge_x),
                int(height + i),
                int(right_edge_z),
                "minecraft:overworld",
                game_version,
                block,
            )


def traffic_sign_handler(from_x, from_z, to_x, to_z, level, sign_type):
    right_edge_x, right_edge_y, right_edge_z = find_road_edge(from_x, from_z, to_x, to_z, "right", level)
    vertical_traffic_impactor_placer(level, right_edge_x, right_edge_y, right_edge_z, sign_type)


def convert_feature(feature, level):
    coordinates, properties = feature["geometry"]["coordinates"][0], feature["properties"]
    from_traffic_impactor = properties["FROM_TRAFFIC_IMPACTOR_CODE"]
    to_traffic_impactor = properties["TO_TRAFFIC_IMPACTOR_CODE"]
    from_x, from_z = convert_lat_long_to_x_z(coordinates[0][1], coordinates[0][0])
    to_x, to_z = convert_lat_long_to_x_z(coordinates[-1][1], coordinates[-1][0])
    try:
        if to_traffic_impactor is not None and traffic_impactor_translation[to_traffic_impactor] is not None:
            # We don't want to place the feature *right* at the end of the segment, as that's almost always in the
            # middle of an intersection. Instead, we want to place it close to the end of the segment. As a result
            # we'll use Bresenham's line algorithm to draw a line from the second last coordinate to the last
            # coordinate, backtrack 15 blocks (or the second last coordinate if the line is shorter than 15 blocks),
            # and place the feature there.
            # if to_traffic_impactor == "L":
            #     traffic_light_handler(from_x, from_z, to_x, to_z, level)
            # else:
            second_last_x, second_last_z = convert_lat_long_to_x_z(coordinates[-2][1], coordinates[-2][0])
            line = bresenham_2d(second_last_x, second_last_z, to_x, to_z)
            if len(line) > IMPACTOR_DISTANCE:
                to_x, to_z = line[-IMPACTOR_DISTANCE]
            else:
                to_x, to_z = line[0]
            traffic_sign_handler(from_x, from_z, to_x, to_z, level,
                                 to_traffic_impactor)
        if from_traffic_impactor is not None and traffic_impactor_translation[from_traffic_impactor] is not None:
            # if from_traffic_impactor == "L":
            #     traffic_light_handler(to_x, to_z, from_x, from_z, level)  # switching "from" and "to" as the traffic
            #     # impactor is at the start of the segment
            # else:
            second_first_x, second_first_z = convert_lat_long_to_x_z(coordinates[1][1], coordinates[1][0])
            line = bresenham_2d(from_x, from_z, second_first_x, second_first_z)
            if len(line) > IMPACTOR_DISTANCE:
                from_x, from_z = line[-IMPACTOR_DISTANCE]
            else:
                from_x, from_z = line[0]
            traffic_sign_handler(to_x, to_z, from_x, from_z, level,
                                 from_traffic_impactor)
    except ChunkDoesNotExist:
        pass
    # other errors we still want to raise


def get_height(x, z, level, blocks_to_ignore=None):
    if blocks_to_ignore is None:
        blocks_to_ignore = []
    cx, cz = block_coords_to_chunk_coords(x, z)
    chunk = level.get_chunk(cx, cz, "minecraft:overworld")
    block_ids_to_ignore = [level.block_palette.get_add_block(block) for block in blocks_to_ignore]
    offset_x, offset_z = x % 16, z % 16
    # so overall we want to ignore blocks that are != 0 and are not in the blocks_to_ignore list
    for y in range(max_height, min_height, -1):
        block = chunk.blocks[offset_x, y, offset_z]
        if block not in block_ids_to_ignore and block != 0:
            return y
    return None


def main():
    level = amulet.load_level("/world/UBC")
    with open(json_path) as f:
        data = json.load(f)

    features = data["features"]
    for feature in tqdm(features):
        convert_feature(feature, level)

    level.save()
    level.close()


if __name__ == "__main__":
    main()
