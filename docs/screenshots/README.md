# Screenshot Info

## Version-1.0:
Contains screenshots from the very initial proof-of-concept with primarily naive voxelization, with some block type filtering based on classification data. The primary buildings in view were manually touched up prior to screenshots. 

This is what was shared to [social media in June of 2023](https://reddit.com/r/UBC/comments/14h76gc/im_building_ubc_in_minecraft/).

## Version-2.0:
This is the state of the world *before* any deep learning algorithm was applied. This world contained the multilayered surface reconstruction pipeline that was created to make a hole-free world, and layered in open map data to properly colorize the ground. Buildings in view are manually touched up. Contains a basic version of Forest Friends, with mean shift clustering and trunk estimation applied to voxelized data on a per-chunk basis.

This is what was shared to [social media in July of 2023](https://reddit.com/r/UBC/comments/150pupj/exciting_minecraft_ubc_project_update/). 

## Version-3.0:
Current version of the world, with deep learning pipelines applied. No buildings are manually touched up and the reconstruction pipeline is fully automated*. 

*With the exception of user-defined coordinate bounds in `ocean.py` that are easily automatable. If you want to run the script fully automated, see `main.py` and change the world directories and LiDAR directories to your local directories. 