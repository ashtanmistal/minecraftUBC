# Buildings

This directory contains the deep learning that was performed on the point clouds of buildings.
The main project, LiDAR-DenseSeg, is included as a submodule.

`building-placer.py` performs the remaining post-processing steps not directly related to deep learning; such as:
- Transforming the output .obj files into the Minecraft world
  - Creating a KDTree for the point cloud
  - Performing a radius-based neighbour search to reject outlier points in the point cloud
  - Performs a plane fitting algorithm on the nearest neighbours in the point cloud to reduce quantization error in voxelization (part of the LiDAR-DenseSeg project, but this is a step best performed when the point cloud is being processed for Minecraft)
  - Picking the optimal Minecraft block for each voxel in the voxelized point cloud

This step is performed after streetlights are placed into the world (as a result it creates a new world folder with the buildings placed in it).