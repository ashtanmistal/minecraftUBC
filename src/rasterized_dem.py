import json
import os
import sys
import numpy as np
import pylas
import rasterio
from rasterio.transform import from_origin
from scipy.spatial import cKDTree
from tqdm import tqdm
from shapely.geometry import Polygon, MultiPolygon
import amulet
from amulet.api.block import Block
from amulet.api.chunk import Chunk
from amulet.api.errors import ChunkDoesNotExist
from amulet.utils import block_coords_to_chunk_coords
from PIL import Image, ImageDraw

import src.geojson.landscaper as geojson
from src.helpers import convert_lat_long_to_x_z, preprocess_dataset, WORLD_DIRECTORY, MIN_HEIGHT

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
GEOJSON_DIR = os.path.join(BASE_DIR, "resources", "geojson_ubcv")
DEFAULT_BLOCK = Block("minecraft", "stone")

GEOJSON_FILE_LIST = [
    "landscape/geojson/ubcv_municipal_waterfeatures.geojson",
    "locations/geojson/ubcv_buildings.geojson",
    "landscape/geojson/ubcv_landscape_soft.geojson",
    "landscape/geojson/ubcv_landscape_hard.geojson",
    "context/geojson/ubcv_uel.geojson",
    "context/geojson/ubcv_beach.geojson",
    "context/geojson/ubcv_psrp.geojson"
]

CONVERSION_MAPPING = [
    geojson.WATER_CONVERSION,
    geojson.BUILDING_CONVERSION,
    geojson.LSSOFT_TYPE_CONVERSION,
    geojson.LSHARD_TYPE_CONVERSION,
    geojson.FID_LANDUS_CONVERSION,
    geojson.BEACH_CONVERSION,
    geojson.PSRP_CONVERSION
]

COLUMN_MAPPING = [
    "None",
    "None",
    "LSSOFT_TYPE",
    "LSHARD_TYPE",
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
                pylas.read(os.path.join(BASE_DIR, "resources", "las", filename)),
                2,
                remove_duplicates=False
            )
            xyz = np.vstack((x, z, y)).transpose()
            ground_points.append(xyz)

    ground_points = np.concatenate(ground_points, axis=0)

    # TODO fix the below code now that we have adjusted the coordinate system to Minecraft's
    x, y, z = ground_points[:, 0], ground_points[:, 1], ground_points[:, 2]

    print("Finished loading ground points.\n")

    # Create a grid to interpolate onto
    x_min, x_max = int(np.floor(x.min())), int(np.ceil(x.max()))
    y_min, y_max = int(np.floor(y.min())), int(np.ceil(y.max()))
    resolution = 1  # 1m resolution, height for each block in Minecraft
    grid_x, grid_y = np.mgrid[x_min:x_max:resolution, y_min:y_max:resolution]

    # create a KDTree for the ground points
    kdtree = cKDTree(ground_points[:, :2])
    # save the kdtree in case it's useful later
    np.save(os.path.join(dem_save_path, "ground_points_kdtree.npy"), kdtree)

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


def colorize_world():
    # Now it's time to colorize the DEM, using the geojson files
    # find the maximum bounds of the geojson files
    for file in GEOJSON_FILE_LIST:
        level = amulet.load_level(WORLD_DIRECTORY)
        with open(os.path.join(GEOJSON_DIR, file), "r") as f:
            geojson_data = json.load(f)
        column_name = COLUMN_MAPPING[GEOJSON_FILE_LIST.index(file)]

        default_universal_block, _, _ = level.translation_manager.get_version("java", (1, 20, 4)).block.to_universal(
            DEFAULT_BLOCK)
        default_block_id = level.block_palette.get_add_block(default_universal_block)

        for feature in tqdm(geojson_data['features']):
            # get the associated color for the feature
            properties = feature['properties']
            if column_name == "None":
                color_hex = CONVERSION_MAPPING[GEOJSON_FILE_LIST.index(file)]["color"]
            elif properties.get(column_name) == "IGNORE":
                continue
            else:
                color_hex = CONVERSION_MAPPING[GEOJSON_FILE_LIST.index(file)].get(properties[column_name], {}).get(
                    "color")
            if color_hex is None:
                continue
            depth = geojson.COLOR_TO_DEPTH[color_hex]
            # rasterize the feature
            geometry = feature['geometry']
            if geometry is None:
                continue
            # Convert the coordinates to Minecraft's coordinate system (that's what the transform requires)
            if geometry['type'] == "Polygon":
                geometry['coordinates'] = [
                    [convert_lat_long_to_x_z(coord[1], coord[0], False) for coord in geometry['coordinates'][0]]]
                bounds = Polygon(geometry['coordinates'][0]).bounds
                # subtract the minimum x and y values from the coordinates
                geometry['coordinates'] = [[(coord[0] - bounds[0], coord[1] - bounds[1]) for coord in poly] for poly in
                                           geometry['coordinates']]
            elif geometry['type'] == "MultiPolygon":
                geometry['coordinates'] = [
                    [[convert_lat_long_to_x_z(coord[1], coord[0], False) for coord in poly[0]] for poly in
                     geometry['coordinates']]]
                bounds = MultiPolygon([Polygon(poly) for poly in geometry['coordinates'][0]]).bounds
                # subtract the minimum x and y values from the coordinates
                geometry['coordinates'] = [
                    [[(coord[0] - bounds[0], coord[1] - bounds[1]) for coord in poly] for poly in poly_list] for
                    poly_list in geometry['coordinates']]
            else:
                continue
            x_min, y_min, x_max, y_max = bounds
            # as int
            x_min, y_min, x_max, y_max = int(round(x_min)), int(round(y_min)), int(round(x_max)), int(round(y_max))
            # if the polygon is too small, skip it
            if x_max - x_min < 1 or y_max - y_min < 1:
                continue

            # create a mask of the feature
            if geometry['type'] == "Polygon":
                mask = Image.new('L', (x_max - x_min, y_max - y_min), 0)
                ImageDraw.Draw(mask).polygon(geometry['coordinates'][0], outline=1, fill=1)
                mask = np.array(mask)
            elif geometry['type'] == "MultiPolygon":
                mask = Image.new('L', (x_max - x_min, y_max - y_min), 0)
                for poly in geometry['coordinates'][0]:
                    ImageDraw.Draw(mask).polygon(poly, outline=1, fill=1)
                mask = np.array(mask)
            else:
                continue

            block = geojson.COLOR_TO_BLOCK[color_hex]
            universal_block, _, _ = level.translation_manager.get_version("java", (1, 20, 4)).block.to_universal(block)
            block_id = level.block_palette.get_add_block(universal_block)
            for ix in range(x_min, x_max):
                for iz in range(y_min, y_max):
                    cx, cz = block_coords_to_chunk_coords(ix, iz)
                    try:
                        chunk = level.get_chunk(cx, cz, "minecraft:overworld")
                    except ChunkDoesNotExist:
                        continue
                    if mask[iz - y_min, ix - x_min] == 1:
                        height = MIN_HEIGHT
                        while chunk.blocks[ix % 16, height, iz % 16] == default_block_id:
                            height += 1
                        chunk.blocks[ix % 16, height - depth:height, iz % 16] = block_id
                    level.put_chunk(chunk, "minecraft:overworld")

        level.save()
        level.close()
    print("Finished colorizing the world.")


def raster_dem_to_minecraft(dem_save_path):
    """
    Rasterizes the DEM into a Minecraft world.
    This is a more robust method than lidar_surface_reconstruction.py, and removes the need for the flood fill step.
    :param dem_save_path: Path to the directory containing the DEM raster.
    :return: None
    """
    level = amulet.load_level(WORLD_DIRECTORY)
    universal_block, _, _ = level.translation_manager.get_version("java", (1, 20, 4)).block.to_universal(
        DEFAULT_BLOCK)
    block_id = level.block_palette.get_add_block(universal_block)
    # load the DEM and get the min/max x/z values
    with rasterio.open(os.path.join(dem_save_path, "dem_raster.tif")) as src:
        grid_z = src.read(1)
        transform = src.transform
    x_min, x_max = int(np.floor(transform[2] / 16) * 16), int(
        np.ceil((transform[2] + transform[0] * grid_z.shape[0]) / 16) * 16)
    z_min, z_max = int(np.floor(transform[5] / 16) * 16), int(
        np.ceil((transform[5] + transform[4] * grid_z.shape[1]) / 16) * 16)
    # reverse z_min and z_max
    z_min, z_max = z_max, z_min
    # iterate over each chunk; read the DEM and place DEFAULT_BLOCK from y=MIN_HEIGHT to y=height (the height of the DEM)
    for ix in tqdm(range(x_min, x_max, 16)):
        for iz in range(z_min, z_max, 16):
            cx, cz = block_coords_to_chunk_coords(ix, iz)
            cz = cz - 1
            # This is fixing another "off by one" chunk error earlier in the code -- don't have time to fix it
            # *properly* for now, but this works.
            try:
                chunk = level.get_chunk(cx, cz, "minecraft:overworld")
            except ChunkDoesNotExist:
                chunk = Chunk(cx, cz)
            # find the unique block_id of default_block in the chunk

            # place the blocks
            dem_in_chunk = grid_z[ix - x_min:ix - x_min + 16, iz - z_min:iz - z_min + 16].astype(int)
            if dem_in_chunk.shape != (16, 16):
                continue
            for x in range(16):
                for z in range(16):
                    chunk.blocks[x, MIN_HEIGHT:dem_in_chunk[x, z], z] = block_id
            level.put_chunk(chunk, "minecraft:overworld")
    print("Finished rasterizing DEM to Minecraft world.")
    level.save()
    level.close()
    print("Saved Minecraft world.")
