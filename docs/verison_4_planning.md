# MinecraftUBC: Version 4.0

This document serves as a public planning document for Version 4.0 of the MinecraftUBC project.

First, a quick note regarding the sporadic project timeframe - as I work full time now (doing very similar things with computer vision and geometric modelling). There hasn't been any direct development work since the end of June, but researching, planning, and tool development has certainly been taking place. There is no rush for me to "finish" the project at this stage - after all, it's one of those projects that seemingly has infinite growth in the number of ways to improve it. Haven't even begun to consider what to do for building interiors yet - it's a massive undertaking.

## Takeaways from Version 3.0

Version 3.0 was, for the most part, a success; landscaping was far more detailed, and the process was fully automated. The buildings additionally offered some improvements compared to Version 2.0. However, there were some key takeaways from the project:

- **Building Quality**: The LiDAR-DenseSeg pipeline left room for improvement - namely in the following areas:
    - Building extent buffer was too large, leading to too many trees incorrectly classified as buildings. 
    - Accuracy of the deep learning model has room for improvement.
    - Planar segmentation was not implemented. 
- Additionally, the color data continues to be very washed out due to the fact that the LiDAR data was taken on a sunny day. Thus, every building was created using iron blocks. Where's the fun in that?
- Processing time was slower than it needed to be due to the uneven point spacing of the data. This can be significantly sped up by performing a voxel downsampling of the data early on in the pipeline.
    - Processing time can additionally benefit from a lot of parallelization :)

## Goals for Version 4.0

This version is almost entirely based on getting more accurate results in the building data. 

### Regarding Genvox

A shape-atlas based neural network for block type selection is in the research phase; the processing tasks mentioned below are highlighted _as a prerequisite_ for Genvox to begin development. A good portion of the research for Genvox is completed, but is waiting for the tasks below to be performed. 

#### Understanding Local Shape Primitives During Data Preprocessing

Before seeking to represent a large point cloud or mesh through the use of primitive shapes in a shape atlas, first gaining a high quality point cloud from raw data is necessary. 

Currently, there exists a large number of extraneous holes in every building point cloud; this makes it incredibly difficult to perform a \[Poisson] surface reconstruction algorithm without first pruning these features. The results of LiDAR-DenseSeg, while they effectively completed the building point clouds with points that were missed during the first round of semantic segmentation, created a large amount of extra noise. Further noise was present in the initial point cloud, given it was taken with a raw sensor; improving the performance of LiDAR-DenseSeg may reduce the number of extraneous points but will not mitigate the problem entirely. As a result some cleanup is necessary; ideally fully automated with minimal intervention due to the large number of buildings. 

### Data Preprocessing

- Perform necessary steps to speed up processing; e.g. voxel downsampling
- Reducing building extent polygon buffer
- Implement planar segmentation:
    - Both for bringing points closer to the plane they are on, and for identifying walls and windows. Windows will be placed where data is missing on a certain plane; this could cause problems with balconies but sufficient RANSAC parameters should mitigate this. 
- Proper color processing.
    - Colors could be fixed on a per-plane basis, and/or based on the "neighbouring wall" given normal estimation being performed on a decimated point cloud. Median filter will be performed first, alongside a min filter between a point and its nearest opposite normal. This will help reduce the problem of extreme sun on some walls, causing walls to be completely washed out. 
    - Using hue-based color matching for Minecraft blocks instead of RGB like was done before. 
    - More complex methods could of course be implemented given additional color data but it will be worthwhile to see how this turns out with existing data. 
- Re-train LiDAR-DenseSeg given the reduced polygon extent, estimated normals, and downsampled pointcloud. 


### Some further improvements and details:

#### Normal estimation:

-  For buildings that primarily consist of a single box, estimating normals and orienting the normals to face away from the mesh center will be sufficient. 
- For buildings that contain multiple "sub-components" (e.g. those that are not effectively defined by a single box), we will need to break the mesh into its components. 
 - Then, for each component, we can estimate normals and orient them away from the component center. 

 #### Feature Removal

Smaller features that are not a part of the larger point cloud should be removed; first based on vertex count (<5 as a start), to assist with removing points that require many denoising steps down the line. The updated building mask should reduce the number of features that this step removes but there are bound to be some points that need further touchups. 

#### Quantization of Holes and Edges

_This assumes an exact triangulation of the point cloud on a per-building basis has been performed._

Because of the eventual conversion to Minecraft blocks, edges (as in mesh edges) that are not purely vertical or horizontal cause problems. **If an edge is on a boundary**, the dot product of the edge vector with the X, Y, and Z axes should be calculated; if it is less than a given threshold the vertices should be "snapped" to the corresponding axes. This will reduce truncation error in places like windows that often are misshaped. Spike removal shouldn't be necessary if the angles are kept less than 22.5$^{\circ}$, but some testing in this step would be good. 

An additional step could be good of making the hole size, if it is within a certain threshold to 1, to be exactly 1 (moving or removing vertices accordingly, be careful here to avoid overlapping faces). Same reasons as above but this could help ensure consistency across buildings. Note that Manhattan distance metric should be used; radial doesn't make sense here. 
