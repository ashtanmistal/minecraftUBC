"""
This script transforms the traffic impactors data inside a geojson file into the Minecraft world.
It finds the side of the road and places relevant things such as stop signs, yield signs, and traffic lights.
"""

import json
import os

import amulet
import numpy as np
from amulet import Block
from amulet.api.errors import ChunkDoesNotExist
from tqdm import tqdm

import src.helpers

ROAD_DATA_JSON_PATH = os.path.join(src.helpers.PROJECT_DIRECTORY, "resources", "BC_Road_Data_Selected.geojson")

MAX_PERPENDICULAR_SEARCH_DISTANCE = 20
IMPACTOR_DISTANCE = 10

YIELD_SIGN_CONFIGURATION = [
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "target"),
]

DEAD_END_SIGN_CONFIGURATION = [
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "yellow_concrete"),
]

STOP_SIGN_CONFIGURATION = [
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "red_concrete"),
]

# TRAFFIC_LIGHT_CONFIGURATION = [
#     Block("minecraft", "pink_wool")  # TODO we'll just do the traffic lights manually as it'll take less time
# ]

BOLLARDS_CONFIGURATION = [
    Block("minecraft", "polished_blackstone_wall"),
]

BLOCKS_TO_IGNORE = [  # blocks to ignore when calculating the height of a block
    Block("minecraft", "red_concrete"),
    Block("minecraft", "yellow_concrete"),
    Block("minecraft", "green_concrete"),
    Block("minecraft", "polished_blackstone"),
    Block("minecraft", "polished_blackstone_wall"),
    Block("minecraft", "target"),
]

ROAD_MATERIALS = [
    "gray_concrete",
    "gray_concrete_powder",
    "white_concrete",
]

TRAFFIC_IMPACTOR_TRANSLATION = {
    "C": None,  # cul-de-sac
    # "L": TRAFFIC_LIGHT_CONFIGURATION,  # TODO removed for CVPR presentation for fully automated pipeline
    # This is a traffic light and needs to be handled differently; this will get caught in the main function here
    "O": None,  # overpass
    "R": YIELD_SIGN_CONFIGURATION,  # vehicles must yield to traffic in the roundabout
    "S": STOP_SIGN_CONFIGURATION,
    "U": None,  # underpass
    "Y": YIELD_SIGN_CONFIGURATION,
    "G": None,  # community gate - this is horizontal and will also need to be handled differently
    "B": BOLLARDS_CONFIGURATION,
    "M": BOLLARDS_CONFIGURATION,  # represents a gate or bollards that restrict access to a pedestrian mall
    "T": None,  # there are no toll booths in the area
    "D": DEAD_END_SIGN_CONFIGURATION,
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
    blocks = TRAFFIC_IMPACTOR_TRANSLATION[sign_type]
    for i, block in enumerate(blocks):
        level.set_version_block(int(x), int(y) + i + 1, int(z), "minecraft:overworld", src.helpers.GAME_VERSION,
                                block)

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
        return from_x, src.helpers.get_height(from_x, from_z, level), from_z
    # find the direction of the line from (from_x, from_z) to (to_x, to_z)
    direction_vector = np.array([to_x - from_x, to_z - from_z])
    normalized_direction_vector = direction_vector / np.linalg.norm(direction_vector)
    # find the perpendicular vector
    if direction == "right":
        perpendicular_vector = np.array([-normalized_direction_vector[1], normalized_direction_vector[0]])
    elif direction == "left":
        perpendicular_vector = np.array([normalized_direction_vector[1], -normalized_direction_vector[0]])
    else:
        raise ValueError("Direction must be either 'right' or 'left'")
    # the magnitude of this line is MAX_PERPENDICULAR_SEARCH_DISTANCE
    end_search_x = to_x + perpendicular_vector[0] * MAX_PERPENDICULAR_SEARCH_DISTANCE
    end_search_z = to_z + perpendicular_vector[1] * MAX_PERPENDICULAR_SEARCH_DISTANCE
    search_blocks = src.helpers.bresenham_2d(to_x, to_z, end_search_x, end_search_z)
    for (x, z) in search_blocks:
        height = src.helpers.get_height(x, z, level)
        if height is None:
            continue
        block, _ = level.get_version_block(x, height, z, "minecraft:overworld", src.helpers.GAME_VERSION)
        if block.base_name in ROAD_MATERIALS:
            continue
        else:
            return x, height, z

    return search_blocks[-1][0], src.helpers.get_height(search_blocks[-1][0], search_blocks[-1][1], level), \
        search_blocks[-1][1]


def traffic_sign_handler(from_x, from_z, to_x, to_z, level, sign_type):
    """
    This function places traffic signs in the world by finding the edge of the road and placing the sign there.
    :param from_x: the x coordinate of the start of the line
    :param from_z: the z coordinate of the start of the line
    :param to_x: the x coordinate of the end of the line
    :param to_z: the z coordinate of the end of the line
    :param level: the Amulet level object
    :param sign_type: the type of traffic sign to place (string, 1 character)
    :return: None
    """
    right_edge_x, right_edge_y, right_edge_z = find_road_edge(from_x, from_z, to_x, to_z, "right", level)
    vertical_traffic_impactor_placer(level, right_edge_x, right_edge_y, right_edge_z, sign_type)


def convert_feature(feature, level):
    """
    Converts a feature from the geojson file into the Minecraft world. This function is called for each feature.
    :param feature: json object representing a feature
    :param level: the Amulet level object
    :return: None
    """
    coordinates, properties = feature["geometry"]["coordinates"][0], feature["properties"]
    from_traffic_impactor = properties["FROM_TRAFFIC_IMPACTOR_CODE"]
    to_traffic_impactor = properties["TO_TRAFFIC_IMPACTOR_CODE"]
    from_x, from_z = src.helpers.convert_lat_long_to_x_z(coordinates[0][1], coordinates[0][0])
    to_x, to_z = src.helpers.convert_lat_long_to_x_z(coordinates[-1][1], coordinates[-1][0])
    try:
        if to_traffic_impactor is not None and TRAFFIC_IMPACTOR_TRANSLATION[to_traffic_impactor] is not None:
            # We don't want to place the feature *right* at the end of the segment, as that's almost always in the
            # middle of an intersection. Instead, we want to place it close to the end of the segment. As a result
            # we'll use Bresenham's line algorithm to draw a line from the second last coordinate to the last
            # coordinate, backtrack 15 blocks (or the second last coordinate if the line is shorter than 15 blocks),
            # and place the feature there.
            second_last_x, second_last_z = src.helpers.convert_lat_long_to_x_z(coordinates[-2][1],
                                                                               coordinates[-2][0])
            line = src.helpers.bresenham_2d(second_last_x, second_last_z, to_x, to_z)
            if len(line) > IMPACTOR_DISTANCE:
                to_x, to_z = line[-IMPACTOR_DISTANCE]
            else:
                to_x, to_z = line[0]
            traffic_sign_handler(from_x, from_z, to_x, to_z, level,
                                 to_traffic_impactor)
        if from_traffic_impactor is not None and TRAFFIC_IMPACTOR_TRANSLATION[from_traffic_impactor] is not None:
            second_first_x, second_first_z = src.helpers.convert_lat_long_to_x_z(coordinates[1][1],
                                                                                 coordinates[1][0])
            line = src.helpers.bresenham_2d(from_x, from_z, second_first_x, second_first_z)
            if len(line) > IMPACTOR_DISTANCE:
                from_x, from_z = line[-IMPACTOR_DISTANCE]
            else:
                from_x, from_z = line[0]
            traffic_sign_handler(to_x, to_z, from_x, from_z, level,
                                 from_traffic_impactor)
    except ChunkDoesNotExist:
        pass


def main(world_directory):
    """
    Main function that loads the Minecraft world and the geojson file, and calls the convert_feature function for each
    feature in the geojson file.
    :return: None
    """
    level = amulet.load_level(world_directory)
    with open(ROAD_DATA_JSON_PATH) as f:
        data = json.load(f)

    features = data["features"]
    for feature in tqdm(features):
        convert_feature(feature, level)

    level.save()
    level.close()


# if __name__ == "__main__":
#     main(src.helpers.WORLD_DIRECTORY)
