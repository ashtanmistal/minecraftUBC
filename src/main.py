import os

from src.buildings import building_placer as building_placer
from src.geojson import sidewalk_placer, streetlight_handler, traffic_impactors
from rasterized_dem import create_heightmap, raster_dem_to_minecraft, colorize_world, BASE_DIR
from helpers import PROJECT_DIRECTORY

lidar_directory = os.path.join(BASE_DIR, "resources", "las")
dem_save_path = os.path.join(BASE_DIR, "src")


def main():
    world_directory = os.path.join(PROJECT_DIRECTORY, "world/UBC")
    # create_heightmap(dem_save_path, lidar_directory)
    # raster_dem_to_minecraft(dem_save_path, world_directory)
    # colorize_world()
    sidewalk_placer.main(world_directory)
    streetlight_handler.streetlight_handler(world_directory)
    traffic_impactors.main(world_directory)
    building_placer.main(lidar_directory)


if __name__ == "__main__":
    main()