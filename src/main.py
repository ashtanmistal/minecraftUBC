import os
import shutil

from helpers import PROJECT_DIRECTORY
from rasterized_dem import BASE_DIR
from src.buildings import building_placer as building_placer
from src.geojson import traffic_impactors, uel_trail_placer
from src.trees import shrubs_placer, tree_placer
from src.flood_fill import ocean

lidar_directory = os.path.join(BASE_DIR, "resources", "las")
dem_save_path = os.path.join(BASE_DIR, "src")


def main():
    # world_directory = os.path.join(PROJECT_DIRECTORY, "world/STREETLIGHTS")
    # create_heightmap(dem_save_path, lidar_directory)
    # raster_dem_to_minecraft(dem_save_path, world_directory)
    # colorize_world()
    # sidewalk_placer.main(world_directory)
    # streetlight_handler.streetlight_handler(world_directory)
    # uel_trail_placer.place_trails(world_directory)
    # traffic_impactors.main(world_directory)
    # if os.path.exists(os.path.join(PROJECT_DIRECTORY, "world/BUILDINGS")):
    #     shutil.rmtree(os.path.join(PROJECT_DIRECTORY, "world/BUILDINGS"))
    # shutil.copytree(world_directory, os.path.join(PROJECT_DIRECTORY, "world/BUILDINGS"))
    # building_placer.main(os.path.join(PROJECT_DIRECTORY, "world/BUILDINGS"))
    # if os.path.exists(os.path.join(PROJECT_DIRECTORY, "world/SHRUBS")):
    #     shutil.rmtree(os.path.join(PROJECT_DIRECTORY, "world/SHRUBS"))
    # shutil.copytree(os.path.join(PROJECT_DIRECTORY, "world/BUILDINGS"), os.path.join(PROJECT_DIRECTORY, "world/SHRUBS"))
    # shrubs_placer.main(os.path.join(PROJECT_DIRECTORY, "world/SHRUBS"))
    # if os.path.exists(os.path.join(PROJECT_DIRECTORY, "world/TREES")):
    #     shutil.rmtree(os.path.join(PROJECT_DIRECTORY, "world/TREES"))
    # shutil.copytree(os.path.join(PROJECT_DIRECTORY, "world/SHRUBS"), os.path.join(PROJECT_DIRECTORY, "world/TREES"))
    # tree_placer.main(os.path.join(PROJECT_DIRECTORY, "world/TREES"))
    # if os.path.exists(os.path.join(PROJECT_DIRECTORY, "world/FULL")):
    #     shutil.rmtree(os.path.join(PROJECT_DIRECTORY, "world/FULL"))
    # shutil.copytree(os.path.join(PROJECT_DIRECTORY, "world/TREES"), os.path.join(PROJECT_DIRECTORY, "world/FULL"))
    ocean.main(os.path.join(PROJECT_DIRECTORY, "world/FULL"))


if __name__ == "__main__":
    main()
