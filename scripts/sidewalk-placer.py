import json
import math

import amulet
import numpy as np
from amulet.api.block import Block
from amulet.api.errors import ChunkDoesNotExist, ChunkLoadError
from amulet.utils.world_utils import block_coords_to_chunk_coords
from tqdm import tqdm
import pyproj
from bresenham import get_intersecting_block_coords

"""This script transforms a geojson file of sidewalks, trails, and similar walkways, and places them in the UBC 
Vancouver Minecraft world. To do this, we will calculate the height of the start and end points of the sidewalk, 
and then place a line of blocks between them. This line will depend on the road type, in which we will change the 
width, pattern, and/or block type dependent on this information. We will additionally use the surface type if 
available to determine the block type of the sidewalk."""

game_version = ("java", (1, 19, 4))

min_y = -58
max_y = 45

x_offset = 480000
z_offset = 5455000

MAX_SEARCH_RADIUS = 6  # the maximum search radius for the height of the start and end points

terrain_blocks = {
    "moss_block": Block("minecraft", "moss_block"),
    "stone": Block("minecraft", "stone"),
    "white concrete": Block("minecraft", "white_concrete"),
    "light gray concrete": Block("minecraft", "light_gray_concrete"),
    "grass block": Block("minecraft", "grass_block"),
    "dirt": Block("minecraft", "dirt")
}

rotation_degrees = 28.000  # This is the rotation of UBC's roads relative to true north.
# After converting lat/lon to metres and subtracting the offset, the roads are rotated 28 degrees clockwise.
rotation = math.radians(rotation_degrees)
inverse_rotation_matrix = np.array([[math.cos(rotation), math.sin(rotation), 0],
                                    [-math.sin(rotation), math.cos(rotation), 0],
                                    [0, 0, 1]])

ROAD_TYPE_translation = {
    '': None,
    "Crosswalk": Block("minecraft", "white_concrete"),  # will leave original block underneath
    "Local Access Pathway": Block("minecraft", "andesite"),
    "Primary Pathway": Block("minecraft", "andesite"),
    "Sidewalk": Block("minecraft", "smooth_stone"),
    "Street_Crossing": Block("minecraft", "white_concrete"),  # TODO does this mean that there is no crosswalk? if so,
    # leave original block underneath?
    "Trail": Block("minecraft", "dirt_path"),
}

SURFACE_TYPE_translation = {
    '': None,
    "Unpaved???": Block("minecraft", "cobblestone"),  # not sure why this label was in the dataset lol
    "Unpaved": Block("minecraft", "cobblestone"),
    "Paved/large gravel": Block("minecraft", "cobblestone"),
    "Dirt": Block("minecraft", "dirt"),
    "Paved": None,
    "asphalt": None,
    "Dirt/small gravel": Block("minecraft", "coarse_dirt"),
    "Dirt///": Block("minecraft", "coarse_dirt"),
    "Grass": Block("minecraft", "grass_block")
}  # Others will be left as the original block type as specified by road_type_regular_translation

VEHICLE_ACCESS_width = {  # whether vehicles are able to access the road determines how wide the path should be
    "": 1,
    "EMERGENCY": 3,
    "NONE": 1,
    "SERVICE": 3
}
crosswalk_width = 2

ROAD_TYPE_search_radius = {  # the search radius for the height of the start and end points depends on the road type
    '': None,
    "Crosswalk": 1,
    "Local Access Pathway": 3,
    "Primary Pathway": 1,
    "Sidewalk": 1,
    "Street_Crossing": 1,
    "Trail": 3
}


# functions we need to write:
# 1. get the height of a point [done for now]
# 2. convert lat/long to x/z
# 3. rotation matrix (align with UBC's world instead of nesw) [done for now]
# 4. get the block type of a line segment
# 5. functions to place a crosswalk, sidewalk, and trail
#    - trail will likely be within trees so we'll need a larger search radius for the elevation calculation
#    - crosswalk will need to place a pattern of alternating blocks (white concrete and original block type)


# main loop:
# for each segment in the geojson file:
#  - get the height of the start and end points
#  - convert lat/long to x/z (incl. rotation matrix)
#  - get the block type of the line segment (switch on road type)
#  - call appropriate placement function

def get_height_of_point(x, z, search_radius, level):
    """
    Returns the height of the highest block at the given x,z coordinates. Only considers blocks within the search
    radius, between min_y and max_y, and ignores non-terrain blocks.
    :param x: the Minecraft x coordinate of the point
    :param z: the Minecraft z coordinate of the point
    :param search_radius: the radius around the point to search for blocks
    :param level: the Minecraft level object
    :return: the height of the highest terrain block at the given x,z coordinates (throw an error if none found)
    """
    # TODO this function is not working properly; always setting minimum height and never anything else
    # get the chunk coordinates of the point
    chunk_x, chunk_z = block_coords_to_chunk_coords(x, z)
    # load the chunk
    try:
        chunk = level.get_chunk(chunk_x, chunk_z, "minecraft:overworld")
    except ChunkDoesNotExist:
        raise ChunkLoadError(f"Chunk ({chunk_x}, {chunk_z}) does not exist - check coordinates")
    # get the height of the highest block within the search radius
    height = max_y
    # only search the blocks in the outer layer of the search radius - we've checked the inner layers already on
    # previous iterations
    for i in range(search_radius):
        # search the blocks on the top of the square
        for j in range(-search_radius + i, search_radius - i + 1):
            # search the blocks on the left side of the square
            block, _ = level.get_version_block(x - search_radius + i, height, z + j, "minecraft:overworld", game_version)
            if block in terrain_blocks.values():
                return height
            # search the blocks on the right side of the square
            block, _ = level.get_version_block(x + search_radius - i, height, z + j, "minecraft:overworld", game_version)
            if block in terrain_blocks.values():
                return height
        # search the blocks on the bottom of the square
        for j in range(-search_radius + i + 1, search_radius - i):
            # search the blocks on the left side of the square
            block, _ = level.get_version_block(x - search_radius + i, height, z + j, "minecraft:overworld", game_version)
            if block in terrain_blocks.values():
                return height
            # search the blocks on the right side of the square
            block, _ = level.get_version_block(x + search_radius - i, height, z + j, "minecraft:overworld", game_version)
            if block in terrain_blocks.values():
                return height
        height -= 1
    if height == min_y:
        # raise ValueError(f"No terrain blocks found within {search_radius} blocks of ({x}, {z})")
        if search_radius < MAX_SEARCH_RADIUS:
            return get_height_of_point(x, z, search_radius + 1, level)
        else:
            pass
            raise ValueError(f"No terrain blocks found within {MAX_SEARCH_RADIUS} blocks of ({x}, {z})")
    # TODO should we try calling the function again with a larger search radius?
    return height


def convert_lat_long_to_x_z(lat, long):
    """
    Converts the given latitude and longitude coordinates to Minecraft x and z coordinates. Uses a pipeline to convert
    from EPSG:4326 (lat/lon) to EPSG:26910 (UTM zone 10N).
    :param lat: the latitude coordinate
    :param long: the longitude coordinate
    :return: the Minecraft x and z coordinates of the given latitude and longitude
    """
    pipeline = "+proj=pipeline +step +proj=axisswap +order=2,1 +step +proj=unitconvert +xy_in=deg +xy_out=rad +step " \
               "+proj=utm +zone=10 +ellps=GRS80"
    transformer = pyproj.Transformer.from_pipeline(pipeline)
    x, z = transformer.transform(lat, long)
    x, z = x - x_offset, z - z_offset
    # x, z = z, x
    x, z, _ = np.matmul(inverse_rotation_matrix, np.array([x, z, 1]))
    z = -z  # flip z axis to match Minecraft
    return int(x), int(z)  # TODO is this the right order?


def get_block_type_of_line_segment(road_type, surface_type):
    """
    Returns the block type of the line segment based on the road type and surface type.
    :param road_type: the type of road (e.g. "Sidewalk")
    :param surface_type: the type of surface (e.g. "Paved/large gravel")
    :return: the block type of the line segment
    """
    if road_type in ROAD_TYPE_translation:
        block = ROAD_TYPE_translation[road_type]
    else:
        return ValueError(f"Road type {road_type} not recognized")  # this should never happen
    if surface_type in SURFACE_TYPE_translation:
        block = SURFACE_TYPE_translation[surface_type]
    return block


def place_crosswalk(start_x, start_y, start_z, end_x, end_y, end_z, level):
    """
    Places a crosswalk between the given start and end coordinates.
    :param start_x: the Minecraft x coordinate of the start of the crosswalk
    :param start_y: the Minecraft y coordinate of the start of the crosswalk
    :param start_z: the Minecraft z coordinate of the start of the crosswalk
    :param end_x: the Minecraft x coordinate of the end of the crosswalk
    :param end_y: the Minecraft y coordinate of the end of the crosswalk
    :param end_z: the Minecraft z coordinate of the end of the crosswalk
    :param level: the Minecraft level object
    :return: None
    """
    intersecting_blocks = get_intersecting_block_coords(start_x, start_y, start_z, end_x, end_y, end_z)
    # Because the crosswalk is crosswalk_width blocks wide, we need to place blocks on either side of the line segment.
    # This requires translating the line segment one meter on either side of the original line segment (perpendicular
    # to the line segment) and then placing blocks along the new line segments.
    for i in range(1, crosswalk_width + 1):
        intersecting_blocks_right = get_intersecting_block_coords(
            *translate_line_segment(start_x, start_y, start_z, end_x, end_y, end_z, i))
        intersecting_blocks_left = get_intersecting_block_coords(
            *translate_line_segment(start_x, start_y, start_z, end_x, end_y, end_z, -i))
        # Place the blocks intersected by the translated line segments
        i = 0
        for block in intersecting_blocks_right:
            if i % 2 == 0:
                level.set_version_block(int(block[0]), int(block[1]), int(block[2]), "minecraft:overworld",
                                        game_version, ROAD_TYPE_translation["Crosswalk"])
            i += 1
        i = 0
        for block in intersecting_blocks_left:
            if i % 2 == 0:
                level.set_version_block(int(block[0]), int(block[1]), int(block[2]), "minecraft:overworld",
                                        game_version, ROAD_TYPE_translation["Crosswalk"])
            i += 1

    # Place the blocks intersected by the original line segment
    i = 0
    for block in intersecting_blocks:
        if i % 2 == 0:
            level.set_version_block(int(block[0]), int(block[1]), int(block[2]), "minecraft:overworld",
                                    game_version, ROAD_TYPE_translation["Crosswalk"])
        i += 1


def translate_line_segment(start_x, start_y, start_z, end_x, end_y, end_z, distance):
    """
    Translates the given line segment by the given distance. Always calculates the line along the x,z plane.
    :param start_x: the Minecraft x coordinate of the start of the line segment
    :param start_y: the Minecraft y coordinate of the start of the line segment
    :param start_z: the Minecraft z coordinate of the start of the line segment
    :param end_x: the Minecraft x coordinate of the end of the line segment
    :param end_y: the Minecraft y coordinate of the end of the line segment
    :param end_z: the Minecraft z coordinate of the end of the line segment
    :param distance: the distance to translate the line segment along the perpendicular
    :return: the translated line segment
    """
    # Calculate the angle of the line segment
    angle = math.atan2(end_z - start_z, end_x - start_x)
    # Calculate the new points
    start_x_new = start_x + distance * math.sin(angle)
    start_z_new = start_z + distance * math.cos(angle)
    end_x_new = end_x + distance * math.sin(angle)
    end_z_new = end_z + distance * math.cos(angle)
    return start_x_new, start_y, start_z_new, end_x_new, end_y, end_z_new


def place_road(start_x, start_y, start_z, end_x, end_y, end_z, level, road_type, surface_type, vehicle_access):
    """
    Places a road between the given start and end coordinates.
    :param start_x: the Minecraft x coordinate of the start of the road
    :param start_y: the Minecraft y coordinate of the start of the road
    :param start_z: the Minecraft z coordinate of the start of the road
    :param end_x: the Minecraft x coordinate of the end of the road
    :param end_y: the Minecraft y coordinate of the end of the road
    :param end_z: the Minecraft z coordinate of the end of the road
    :param level: the Minecraft level object
    :param road_type: the type of road to place (string)
    :param surface_type: the surface type of the road (string)
    :param vehicle_access: whether vehicles can access the road (string)
    :return: None
    """
    if ROAD_TYPE_search_radius[road_type] is None:
        return ValueError("Invalid road type: " + road_type)
    if VEHICLE_ACCESS_width[vehicle_access] is None:
        return ValueError("Invalid vehicle access: " + vehicle_access)
    intersecting_blocks = get_intersecting_block_coords(start_x, start_y, start_z, end_x, end_y, end_z)
    for i in range(1, VEHICLE_ACCESS_width[vehicle_access] + 1):
        intersecting_blocks += get_intersecting_block_coords(
            *translate_line_segment(start_x, start_y, start_z, end_x, end_y, end_z, i))
        intersecting_blocks += get_intersecting_block_coords(
            *translate_line_segment(start_x, start_y, start_z, end_x, end_y, end_z, -i))

    if SURFACE_TYPE_translation[surface_type] is not None:
        block_type = SURFACE_TYPE_translation[surface_type]
    else:
        block_type = ROAD_TYPE_translation[road_type]
    for block in intersecting_blocks:
        level.set_version_block(int(block[0]), int(block[1]), int(block[2]), "minecraft:overworld",
                                game_version, block_type)


def convert_feature(feature, level):
    """
    Converts the given feature into a road in the given level.
    :param feature: A road feature from the GeoJSON file
    :param level: The Minecraft level object
    :return: None
    """
    coordinates, properties = feature["geometry"]["coordinates"], feature["properties"]
    road_type, surface_type, vehicle_access = properties["ROAD_TYPE"], properties["SURFACE_TYPE"], \
        properties["VEHICLE_ACCESS"]
    # break the coordinates into line segments (each line segment is a list of two coordinates)
    line_segments = []
    for i in range(len(coordinates) - 1):
        x1, z1 = convert_lat_long_to_x_z(coordinates[i][1], coordinates[i][0])
        y1 = get_height_of_point(x1, z1, ROAD_TYPE_search_radius[road_type], level)
        x2, z2 = convert_lat_long_to_x_z(coordinates[i + 1][1], coordinates[i + 1][0])
        y2 = get_height_of_point(x2, z2, ROAD_TYPE_search_radius[road_type], level)
        line_segments.append([(x1, y1, z1), (x2, y2, z2)])

    # Place the road for each line segment
    for line_segment in line_segments:
        if road_type == "Crosswalk":
            place_crosswalk(*line_segment[0], *line_segment[1], level)
        else:
            place_road(*line_segment[0], *line_segment[1], level, road_type, surface_type, vehicle_access)


def main():
    level = amulet.load_level("../world/UBC")
    sidewalk_data_path = "../resources/ubc_roads/Data/ubcv_paths_sidewalks.geojson"
    with open(sidewalk_data_path) as sidewalk_data_file:
        sidewalk_data = json.load(sidewalk_data_file)

    for feature in tqdm(sidewalk_data["features"]):
        try:
            convert_feature(feature, level)
        except ChunkLoadError:
            print("Error converting feature: ", feature)
        # convert_feature(feature, level)

    level.save()
    level.close()


if __name__ == "__main__":
    main()
