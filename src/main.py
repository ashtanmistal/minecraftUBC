import os

from src.buildings import building_placer as building_placer
from src.geojson import sidewalk_placer, streetlight_handler, traffic_impactors
from rasterized_dem import create_heightmap, raster_dem_to_minecraft, colorize_world, BASE_DIR

lidar_directory = os.path.join(BASE_DIR, "resources", "las")
dem_save_path = os.path.join(BASE_DIR, "src")


def main():
    create_heightmap(dem_save_path, lidar_directory)
    raster_dem_to_minecraft(dem_save_path)
    colorize_world()
    sidewalk_placer.main()
    streetlight_handler.streetlight_handler()
    traffic_impactors.main()
    building_placer.main(lidar_directory)
