"""
We need a more efficient method of creating the DEM from the ground data that does not require semi-manual hole filling.
Thus, this approach is a new approach that addresses these issues through the following method:

1. Create a KDtree of the ground points, considering only the x and y coordinates (height is not used for this)
2. For each GeoJSON polygon, get a set of 1x1m points that are within the polygon (this can just be done in QGIS)
3. For each point, get the 3 nearest neighbours from the KDtree
4. Calculate the height of the point using a weighted average of the heights of the 3 nearest neighbours
5. If the nearest neighbour is > 1m away, then add the weighted average to the KDtree to fill in the gaps
6. If the nearest neighbour is <= 1m away, don't add the weighted average to the KDtree as sufficient points in the
    area already exist to create a smooth surface
7. Use the height and related geojson polygon data to create a colorized DEM (3d array). Save the file.
8. Place the DEM in the Minecraft world
"""

import json
import math
import os
import numpy as np
import pylas
import pyproj
from shapely.geometry import shape, Point
from scipy.spatial import KDTree
from tqdm import tqdm
import sys
from src.helpers import convert_lat_long_to_x_z

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
GEOJSON_DIR = os.path.join(BASE_DIR, "resources", "geojson_ubcv")

GEOJSON_FILE_LIST = [
    "landscape/geojson/ubcv_municipal_waterfeatures.geojson",
    "landscape/geojson/ubcv_landscape_hard.geojson",
    "landscape/geojson/ubcv_landscape_soft.geojson",
    "locations/geojson/ubcv_buildings.geojson",
    "context/geojson/ubcv_uel.geojson",
    "context/geojson/ubcv_beach.geojson",
    "context/geojson/ubcv_psrp.geojson",
]


# These are in priority order: the first one will be used if there is a conflict (i.e. one point belongs to two
# polygons)

geojson_files = [json.load(open(os.path.join(GEOJSON_DIR, file), "r")) for file in GEOJSON_FILE_LIST]


print("Translating lat/long coordinates to x/z coordinates...")

for filename, file in tqdm(zip(GEOJSON_FILE_LIST, geojson_files)):
    # call convert_lat_long_to_x_z on each vertex in each polygon in the geojson file
    # this will translate the lat/long coordinates to x/z coordinates
    features = file["features"]
    for i in range(0, len(features)):
        feature = features[i]
        try:
            if feature["geometry"]["type"] == "Polygon":
                coordinates, properties = feature["geometry"]["coordinates"], feature["properties"]
                coordinates_translated = []
                for polygon in coordinates:
                    for vertex in polygon:
                        coordinates_translated.append(convert_lat_long_to_x_z(vertex[1], vertex[0], False))
                feature["geometry"]["coordinates"] = coordinates_translated
            elif feature["geometry"]["type"] == "MultiPolygon":
                coordinates, properties = feature["geometry"]["coordinates"], feature["properties"]
                for j in range(0, len(coordinates)):
                    polygon = coordinates[j][0]
                    coordinates_translated = []
                    for vertex in polygon:
                        coordinates_translated.append(convert_lat_long_to_x_z(vertex[1], vertex[0], False))
                    coordinates[j] = coordinates_translated
                feature["geometry"]["coordinates"] = coordinates
            else:
                raise TypeError("Invalid geometry type")
        except TypeError:
            print("Invalid geometry type in file: " + filename)
            print("Skipping...")
            continue

        # save the file, with "translated" appended to the end filename
        file["features"][i] = feature
    with open(os.path.join(GEOJSON_DIR, filename.replace(".geojson", "_translated.geojson")), "w") as f:
        json.dump(file, f)

print("Finished translating coordinate space.\n")

# find the bounds of the area

print("Finding bounds of the area...")


# we will use the Shapely library to find the bounds of the area

uel_feature = geojson_files[4]["features"][0]  # UEL has the largest bounds via visual inspection
# Of course change for other datasets, this is just for speed
uel_shape = shape(uel_feature["geometry"])
min_x, min_y, max_x, max_y = uel_shape.bounds
print("Bounds of the area: ")
print("Min x: " + str(min_x))
print("Min y: " + str(min_y))
print("Max x: " + str(max_x))
print("Max y: " + str(max_y))
print("")

print("Building KDTree of ground points...")

ground_points = []

for filename in tqdm(os.listdir(os.path.join(BASE_DIR, "resources", "las"))):
    if filename.endswith(".las"):
        las_file = pylas.read(os.path.join(BASE_DIR, "resources", "las", filename))
        # remove all points that are not ground points
        points = las_file.points[las_file.points["classification"] == 2]
        ground_points.extend(points)

ground_points = np.array(ground_points)

# create a KDTree of the ground points
ground_points_kdtree = KDTree(ground_points[:, 0:2])

