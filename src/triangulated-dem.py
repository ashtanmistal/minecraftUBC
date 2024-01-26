import json
import os
import sys
import geopandas as gpd
import numpy as np
import pylas
import rasterio
from matplotlib.colors import to_rgba
from rasterio.features import rasterize
from rasterio.transform import from_origin
from scipy.spatial import cKDTree
from tqdm import tqdm

from geojson.landscaper import (LSHARD_TYPE_CONVERSION, LSSOFT_TYPE_CONVERSION, FID_LANDUS_CONVERSION,
                                BUILDING_CONVERSION, WATER_CONVERSION, BEACH_CONVERSION, PSRP_CONVERSION)
from src.helpers import convert_lat_long_to_x_z, preprocess_dataset

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
    "context/geojson/ubcv_psrp.geojson"
]

CONVERSION_MAPPING = [
    WATER_CONVERSION,
    LSHARD_TYPE_CONVERSION,
    LSSOFT_TYPE_CONVERSION,
    BUILDING_CONVERSION,
    FID_LANDUS_CONVERSION,
    BEACH_CONVERSION,
    PSRP_CONVERSION
]

COLUMN_MAPPING = [
    "None",
    "LSHARD_TYPE",
    "LSSOFT_TYPE",
    "None",
    "FID_LANDUS",
    "None",
    "None"
]


def read_las_file(file_path):
    """
    Reads a .las file and extracts the necessary point cloud data.

    :param file_path: Path to the .las file to be read.
    :return: A tuple of numpy arrays (points, colors, labels).
    """

    # Open the .las file
    las_data = pylas.read(file_path)

    # Extract xyz coordinates
    points = np.vstack((las_data.x, las_data.y, las_data.z)).transpose()

    # Extract classification labels
    labels = las_data.classification

    # Check if color information is present and extract it
    if hasattr(las_data, 'red') and hasattr(las_data, 'green') and hasattr(las_data, 'blue'):
        colors = np.vstack((las_data.red, las_data.green, las_data.blue)).transpose()
    else:
        colors = np.zeros_like(points)  # If no color info, create a dummy array with zeros

    # Normalize or preprocess the points if needed
    # This would be based on the preprocessing done in the original S3DISDataLoader

    # Return the extracted data
    return points, colors, labels


def translate_geojson():
    """
    Translates the lat/long coordinates in the geojson files to x/z coordinates.
    :return: None
    """
    print("Translating lat/long coordinates to x/z coordinates...")
    geojson_files = [json.load(open(os.path.join(GEOJSON_DIR, file), "r")) for file in GEOJSON_FILE_LIST]
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


def create_heightmap(dem_save_path, lidar_directory):
    """
    Creates a heightmap of the ground points in the dataset.
    :param dem_save_path: Path to save the heightmap to. (directory, not file)
    :param lidar_directory: Path to the directory containing the .las files.
    :return: None
    """
    ground_points = []

    for filename in tqdm(os.listdir(lidar_directory)):
        if filename.endswith(".las"):
            _, _, _, _, x, y, z = preprocess_dataset(
                read_las_file(os.path.join(BASE_DIR, "resources", "las", filename)),
                2,
                remove_duplicates=False
            )
            xyz = np.vstack((x, y, z)).transpose()
            ground_points.append(xyz)

    ground_points = np.concatenate(ground_points, axis=0)

    x, y, z = ground_points[:, 0], ground_points[:, 1], ground_points[:, 2]

    print("Finished loading ground points.\n")

    # Create a grid to interpolate onto
    x_min, x_max = int(np.floor(x.min())), int(np.ceil(x.max()))
    y_min, y_max = int(np.floor(y.min())), int(np.ceil(y.max()))
    resolution = 1  # 1m resolution, height for each block in Minecraft
    grid_x, grid_y = np.mgrid[x_min:x_max:resolution, y_min:y_max:resolution]

    # create a KDTree for the ground points
    kdtree = cKDTree(ground_points[:, :2])

    # use linear interpolation from the 3 nearest neighbors to interpolate the height values for each point in the grid
    def interpolate_heights(x, y):
        _, indices = kdtree.query(np.array([x, y]).transpose(), k=3)
        return np.mean(ground_points[indices, 2])

    grid_z = np.empty(grid_x.shape)

    # Interpolate the height values for each point in the grid
    print("Interpolating height values...")
    for i in tqdm(range(grid_x.shape[0])):
        for j in range(grid_y.shape[1]):
            grid_z[i, j] = interpolate_heights(grid_x[i, j], grid_y[i, j])

    print("Finished interpolating height values.\n")

    # Create a DEM (colorization will be in a separate step)
    transform = from_origin(x_min, y_max, resolution, resolution)
    with rasterio.open(os.path.join(dem_save_path, "dem_raster.tif"), 'w', driver='GTiff',
                       height=grid_z.shape[0], width=grid_z.shape[1],
                       count=1, dtype=str(grid_z.dtype),
                       crs='+proj=latlong', transform=transform) as dst:
        dst.write(grid_z, 1)

    print("Finished creating DEM.\n")


def create_color_raster(dem_directory):
    # Now it's time to colorize the DEM, using the geojson files and creating another raster

    # read the DEM
    with rasterio.open(os.path.join(dem_directory, "dem_raster.tif")) as src:
        grid_z = src.read(1)
        transform = src.transform

    color_raster = np.zeros((grid_z.shape[0], grid_z.shape[1], 3), dtype=np.uint8)

    # geojson files, in order of priority, is the reverse of GEOJSON_FILE_LIST

    for file in GEOJSON_FILE_LIST[::-1]:
        # read the translated geojson file
        print("Rasterizing " + file + "...")
        gdf = gpd.read_file(os.path.join(GEOJSON_DIR, file.replace(".geojson", "_translated.geojson")))
        column_name = COLUMN_MAPPING[GEOJSON_FILE_LIST.index(file)]

        for _, row in tqdm(gdf.iterrows(), total=gdf.shape[0]):
            # get the associated color for the feature
            if column_name == "None":
                color = CONVERSION_MAPPING[GEOJSON_FILE_LIST.index(file)]["color"]
            elif row[column_name] == "IGNORE":
                continue
            else:
                color = CONVERSION_MAPPING[GEOJSON_FILE_LIST.index(file)][row[
                    column_name]]["color"]
            # another mapping
            if color is None:
                color = "#000000"  # default to black if no color is found
            color = to_rgba(color)

            # rasterize the feature
            try:
                mask = rasterize([(row["geometry"], 1)], out_shape=grid_z.shape, transform=transform)
                # Update the raster - only update where mask is True
                for i in range(3):  # RGB channels
                    color_raster[:, :, i] = np.where(mask, color[i], color_raster[:, :, i])
            except ValueError:
                print("Invalid geometry in file: " + file)
                print("Skipping...")
                continue

    # Save the color raster
    with rasterio.open(
            'landuse_raster.tif', 'w', driver='GTiff',
            height=color_raster.shape[0], width=color_raster.shape[1],
            count=3, dtype=str(color_raster.dtype),
            crs='+proj=latlong',
            transform=transform
    ) as dst:
        for i in range(color_raster.shape[2]):
            dst.write(color_raster[:, :, i], i + 1)

    print("Land use raster created: landuse_raster.tif")


if __name__ == "__main__":
    translate_geojson()
    lidar_directory = os.path.join(BASE_DIR, "resources", "las")
    dem_save_path = os.path.join(BASE_DIR, "src")
    create_heightmap(dem_save_path, lidar_directory)
    create_color_raster(dem_save_path)
