import json
import amulet
from amulet.api.block import Block
from amulet.api.errors import ChunkLoadError
from tqdm import tqdm
from scripts.util import bresenham_3d, convert_lat_long_to_x_z
from scripts.deprecated.geojson.sidewalk_placer import game_version
from scripts.deprecated.geojson.sidewalk_placer import get_height_of_point, translate_line_segment

ROAD_TYPE_translation = {
    "Arterial": Block("minecraft", "light_gray_concrete"),
    "Collector": Block("minecraft", "light_gray_concrete"),
    "Local": Block("minecraft", "light_gray_concrete"),
    "Service": Block("minecraft", "andesite"),
}

VEHICLE_ACCESS_width = {
    "EMERGENCY": 3,
    "PUBLIC": 6,
    "SERVICE": 5,
}


def place_road(start_x, start_y, start_z, end_x, end_y, end_z, level, road_type, vehicle_access):
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
    :param vehicle_access: whether vehicles can access the road (string)
    :return: None
    """

    if VEHICLE_ACCESS_width[vehicle_access] is None:
        return ValueError("Invalid vehicle access: " + vehicle_access)
    intersecting_blocks = bresenham_3d(start_x, start_y, start_z, end_x, end_y, end_z)
    for i in range(1, VEHICLE_ACCESS_width[vehicle_access] + 1):
        intersecting_blocks += bresenham_3d(
            *translate_line_segment(start_x, start_y, start_z, end_x, end_y, end_z, i))
        intersecting_blocks += bresenham_3d(
            *translate_line_segment(start_x, start_y, start_z, end_x, end_y, end_z, -i))

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
    road_type, vehicle_access = properties["ROAD_TYPE"], properties["VEHICLE_ACCESS"]
    # break the coordinates into line segments (each line segment is a list of two coordinates)
    line_segments = []
    for i in range(len(coordinates) - 1):
        x1, z1 = convert_lat_long_to_x_z(coordinates[i][1], coordinates[i][0])
        y1 = get_height_of_point(x1, z1, 0, level)
        x2, z2 = convert_lat_long_to_x_z(coordinates[i + 1][1], coordinates[i + 1][0])
        y2 = get_height_of_point(x2, z2, 0, level)
        line_segments.append([(x1, y1, z1), (x2, y2, z2)])

    # Place the road for each line segment
    for line_segment in line_segments:
        place_road(*line_segment[0], *line_segment[1], level, road_type, vehicle_access)


def main():
    level = amulet.load_level("/world/UBC")
    sidewalk_data_path = "/resources/ubc_roads/Data/ubcv_roads.geojson"
    with open(sidewalk_data_path) as road_data_file:
        road_data = json.load(road_data_file)

    features = road_data["features"]
    # features = features[::-1]
    for feature in tqdm(features):
        try:
            convert_feature(feature, level)
        except ChunkLoadError:
            print("Error converting feature: ", feature)
        except ValueError:
            print("Error converting feature: ", feature)
    level.save()
    level.close()


if __name__ == "__main__":
    main()
