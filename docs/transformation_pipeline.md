# Transformation of LiDAR Data and Operational Geospatial Data to a 1:1 Minecraft World

Table of Contents:
- [First Iteration](#first-iteration)
  - [LiDAR Processing](#lidar-processing)
    - [Denoising the Dataset](#denoising-the-dataset)
    - [Rotation and Translation](#rotation-and-translation)
    - [Chunk processing](#chunk-processing)
  - [Road and Sidewalk Placement](#road-and-sidewalk-placement)
- [Second Iteration](#second-iteration)
  - [Creation of a Voxelized and Colorized Digital Elevation Model](#creation-of-a-voxelized-and-colorized-digital-elevation-model)
  - [Road and Sidewalk Placement](#road-and-sidewalk-placement)
  - [Building Placement](#building-placement)
  - [Tree Handling](#tree-handling)

___

# First Iteration

The first iteration is what was [shared on social media in late June](https://www.reddit.com/r/UBC/comments/14h76gc/im_building_ubc_in_minecraft/). It was a proof of concept that showed that the idea was possible. It was built using the following pipeline:

## LiDAR Processing

### Denoising the Dataset

The first thing we need to do is ensure the quality of the data that is being placed into the world. As such, there are only a few classes of data that we care about, and so we remove noise and unneeded classes as well as removing points above the height limit of Minecraft (The only points above this limit were some noise points)

### Rotation and Translation

We do a quick coordinate space transformation by applying offsets to the data. This ensures that campus coordinates are reasonable and close to the origin. After this, we apply a rotation matrix to the data as UBC's roads are misaligned with true north, and we want the building process to be as easy as possible, so we want to properly align the roads with the x and z axes in Minecraft.

### Chunk processing

After breaking the data into chunks to process, we want to voxelize the data. This is done by truncating each value to the nearest cubic meter, and then iterate through each unique meter that contains data. We then calculate the median classification of a given meter, and select from a block palette the block that best matches the average color of the points in that meter. This is done for each meter, and then we have a voxelized chunk with the blocks placed in the world. Trees are slightly de-noised in this process, removing stray points that do not have a high enough density to be considered a tree.

## Road and Sidewalk Placement

Geodata is available for every one of UBC's roads and sidewalks, with information pertaining to type and material. This information was translated into the correct coordinate space and was placed into the already generated world, with the heights calculated from the ground terrain using a nearest-neighbour approach in an increasing radius.

___

# Second Iteration

The first iteration was a moderate success, and created a playable world for people to use and build the remaining buildings. However, it was not perfect, and there were many things that could be improved, namely the following:
- The ground was hollow in many places where there existed lots of tree or building data above, making it easy to fall out of the world
- The trees were not realistic as they had no trunks or branches
- Street data height calculation was not accurate given the lack of height data available for some trail points - this led to some sidewalks being placed far higher than they should have been
- More geojson data is available for classification purposes and block palette selection that was unused in the first iteration
- Shadows significantly affected the ground block palette selection, leading to many areas having the wrong block type where a tree shadow was over the ground

The second iteration aimed to resolve these errors through a geometric modelling based approach, and relying more heavily on the available geodata, which would select a more accurate block palette than the first iteration, which was affected by shadows and other factors.

## Creation of a Voxelized and Colorized Digital Elevation Model

In order for us to have an accurate, hole-free world, we need to write a surface reconstruction pipeline for processing the data into a voxelized DEM. A few options were considered for this, namely the creation of a triangulated irregular network (TIN) and voxelizing that. However, given the next step of voxelization right after, it was a waste of computational power to try and triangulate the mesh. As a result, a different surface reconstruction algorithm was created, which is outlined below:
- For each chunk, we can calculate the 2d convex hull of the points within. This ensures that the beach and other edges are properly defined, and also filling in some of the smaller within-chunk holes in the data.
- For points in the convex hull that *did* have associated height data, the blocks were placed accordingly. Otherwise, the height of a given point was calculated using a weighted nearest neighbours approach, where the 3 closest points in the chunk were selected. Beneath the maximum height all blocks until the minimum height were placed to fully close and fill in the mesh. 
- A few denoising steps were performed to fill in the remaining holes in the mesh:
  - First, any chunk that had less than 16/256 missing blocks was filled in completely with the same weighted nearest neighbours approach. This took care of a large amount of speckle noise in the data caused by sparse points in the dataset.
  - A flood fill algorithm was implemented to fill in the larger holes that were not caught by the previous denoising algorithms. This catches things like the missing ground data beneath buildings, where entire chunks were sparse in data. This flood fill was expanded to a "region fill", which bounded a user-selected rectangular region and filled in all holes within that region. This flood fill was performed on the bulk of the campus, on areas where the chunks did not intersect the ocean. For the flood fill, the heights were calculated using the same approach, taking into account points that were added to the mesh during flood fill to prevent the mesh from being too jagged.

The next significant step is taking the full DEM of campus and colorizing it. There are geospatial datasets outlining the land use of campus to a significant detail, which allowed for the colorization of the DEM. The following steps were taken to colorize the DEM:
- The geospatial data was converted into a voxelized polygon, and the points inside the polygon were selected via a flood fill. The seed for the flood fill was determined through a simple ray cast, until a point guaranteed to be inside the polygon was found. The flood fill selected the remaining points inside the polygon, and the block type was set accordingly, either through a set block or a random selection. 
  - The flood fill worked for almost all polygons, except for ones that were skinny, where the flood fill would be stopped early due to the voxelization of the polygon. These cases were low in number and were faster to fix manually, though it could be fixed by selecting either a finer grain of voxelization prior to flood fill (and coarser after) or by using a different algorithm. 
- Block types were selected based on various attributes of the polygon, such as land use, type, and material. See `scripts/geojson/landscaper.py` for the implementation details and the list of datasets used in the colorization process.

___

## Road and Sidewalk Detailing

The geospatial datasets that were used to colorize the DEM placed all of the roads and sidewalks, but there's a lot of additional data that we can use to further add detail to the world.
- Streetlight data is used to place every outdoor light source on campus, lighting up the walkways, streets, and other areas. While this doesn't cover any indoor lighting, it makes for a much more beautiful nighttime experience.
- Stop signs, yield signs, bollards, and crosswalks can be transformed and placed. The crosswalk data is from the same dataset as was used in the first iteration. 
- The line segments that make up the hiking trails in Pacific Spirit Park can also be transformed and placed, adding a lot of detail to the park and also adding stairs down to Wreck Beach.

## Building Placement

The next problem to tackle is placing buildings. Datapoint matching with the operational geospatial data was considered and attempted, however due to noise and trees overtop of buildings this approach was not as accurate as the approach in the first iteration. As a result, the same approach as the first iteration was taken for placing buildings. This method was to place buildings wherever there's classified LiDAR data, and matching the average point lighting information to a block type for a given meter.

The color of the buildings was semi-automatically improved using a flood fill algorithm. A user selected a wall block type, roof block type, and starting seed, and the flood fill was performed. The flood fill was done column-based given the sparsity in some walls; an [x,z] point was added if any block in its column was a building block. This worked well for buildings with monochrome walls and/or roofs. This was not performed for all buildings and was done on an as-needed basis; buildings with a significant difference in visible block type within the walls or within the roof were not flood filled as the flood fill will not have sped up the manual building coloring process.

___

## Tree Handling

Trees are the most complex part of this transformation, as simply placing a block wherever there's leaves leads to a lot of hollow trees with no trunks. 

We will follow a mean shift clustering algorithm combined with a vertical strata analysis to differentiate between actual tree clusters and crown clusters. The algorithm chosen for this project is based on [this research paper](https://doi.org/10.3390/rs15051241), where we have optimized the algorithm for speed. 

The basic outline is as follows:
- Truncate the data to the nearest square meter and only consider unique values. (Note that improvements could be made by writing a weighted mean shift algorithm, but this is not implemented in this project)
- Shift the data to ignore the height of the ground and base it on the distance away from the ground
- Perform mean shift clustering to get the candidate cluster centers
- Perform vertical strata analysis on the candidate clusters to analyze the vertical distribution of the points in the cluster. This is used to determine if the cluster is a tree cluster or a crown cluster. 
- If a given cluster is a crown cluster, the points are re-distributed to the nearest tree cluster and the cluster centers re-calculated accordingly.

Once the trunks are placed we want to place branches. We only need to branch together leaf *clusters*, and not every single leaf; as a result, a 3d DBSCAN algorithm was performed to create intra-tree clusters, with a high epsilon to take into account the truncation of the data to the nearest square meter. These clusters were then attached to the tree trunk using a constrained optimization line drawing, by minimizing the distance between the line and the points in the cluster. This line was constrained in that:
  - It must end up on the trunk, and
  - the vertical distance must be within a certain range of the cluster's height.
  - The line length must be small enough (a hard cutoff) to prevent the branches from being too long.
Trunks were placed purely vertically; branches were placed according to a 3d adaptation of Bresenham's line algorithm.


The trunks and branches worked very well on coniferous trees, but struggled with trees with large crowns due to the division of clustering to be within a given chunk. This means that trees that had crowns extending beyond a chunk boundary would be split into two trunk clusters, which meant that areas with lots of large-crowned trees (e.g. Main Mall) ended up with large numbers of trunks in the middle of the road. This was combated by removing any trunks that intersected a hard landscaping feature; such large trees would have another trunk nearby anyway due to the chunk split, so this did not lead to any loss of detail. This could be further combated by performing the mean shift clustering algorithm on a larger area, however given the sheer size of the LiDAR datasets, speed optimizations were prioritized over accuracy, allowing the algorithm to finish campus overnight instead of taking a week or more.

___

# Overall Results

The second iteration of this project has led to a much more detailed and true-to-life representation of campus, and creates a much more immersive experience. Images and videos of the second iteration are available in the project's root README.

There are further improvements that could have been made, however due to time constraints and the scope of the project, these were not implemented. These include:
- Improvement on the polygon flood fill algorithm. This algorithm performed the flood fill after voxelization, and not before, and so blocks that were touching after the voxelization was done prevented the algorithm from being able to reach all areas of the polygon. This could be fixed by performing the flood fill before voxelization, or by running the algorithm again on a different area until the flood filled area was close to the computed polygon area (the computed areas available in the dataset itself). 
- Optimizing the tree trunk placement algorithm for accuracy instead of speed. Due to computational resource constraints and the sheer size of data that was being processed, the tree trunk placement algorithm was optimized for speed. This led to some sacrifices in accuracy that would be improved by running the algorithm on a larger area, by implementing a weighted mean shift algorithm, or by considering numerous runs of the algorithm and taking the mean results as the research paper discussed. Further hyperparameter tuning would also lead to further accuracy improvements.
- Improving the building placement algorithm through a learning model for block selection. Having the block selection be based entirely on the LiDAR data was not without its flaws, and utilizing available orthographic imagery to determine what block a specific roof is made out of would lead to higher color accuracy. A learning model would be needed due to trees, shadows, and other obstructions that hinder a direct matching approach. 