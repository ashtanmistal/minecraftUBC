# Transformation of LiDAR Data, Orthographic Imagery, and Operational Geospatial Data to a 1:1 Minecraft World

___

## Creation of a TIN and a voxelized DEM

First, we take the LiDAR data, extract only the ground information, and transform it into a triangulated irregular network (TIN). Though this loses the color data, it efficiently stores vertices needed for voxelization. This network we then treat as an open manifold mesh, where the goal is then to close the mesh: To do this, we also know that there exists a plane beneath the current mesh (The bedrock layer, as well as a couple layers above). We then want to take the boundary edges add vertices and edges vertically until this plane is reached; after which, we connect the points that are touching the plane to create a closed manifold mesh. This closed mesh is easy to voxelize; numerous algorithms exist for such a task already.

Once that's done, we need to take the orthophotos and perform a Gaussian blur such that we have a reduced number of points per square meter.

We also have the polygons that are defined in the geodata: We want to voxelize this polygon in a smart manner, and get a set of all voxels that are inside this polygon. Based on various polygon attributes (i.e. landscape information), we can match the orthographic image data within that voxel (now only a few pixels to compare after blurring) to determine the block type, if not already set by the polygon attributes. That defines the block type for every ground block. 

This provides a voxelized, colorized digital elevation model (DEM) of the surface. 

___

## Placing buildings

The next problem to tackle is placing buildings. Walls and roofs can just be placed wherever there's LiDAR data for a given area - there's not much information as to the walls for some areas given they're not all visible from the sky when the scan was taken, so we want to use what we have.

We can use a similar color matching approach for the roofs, but we will want to try to ignore shadows and replace all "shadow" block colors with their non-shadow counterpart. We want to do this in a way that doesn't remove any additional coloring on the roof. I'm not quite sure as to the best approach for this; we may just color match. 

The matched color is the effective block color for all building blocks of a given x,z. This means walls will inherit the roof color that is directly above. 

___

## Tree handling

Trees are the most complex part of this transformation, as simply placing a block wherever there's leaves leads to a lot of hollow trees with no trunks. 

First, we want to round the leaves and cluster them closer to other points within a square meter. This ensures that the trees aren't overly lush, and that we don't have an overly complex NP-hard branch creation problem. 

Let's place tree trunks. In order to learn where tree trunks should be, we need to cluster each tree and determine where exaclty the trunk should be placed. This will be done through a combination of horizontal mean shift clustering and vertical strata analysis to get the centers of only the tree crowns. This is outlined further elsewhere. We can perform a much faster mean shift clustering algorithm knowing that we are using voxelized data; this is outlined in https://doi.org/10.48550/arXiv.2104.00303. The tree trunks are placed from the height of the tree down to the elevation set by the TIN. 

Once the trunks are placed we want to place branches. We only need to branch together leaf *clusters*, and not every single leaf; as a result, we can do the following:

- Every leaf block is its own cluster
- If it is adjacent with other leaf blocks, assign it to the same cluster. Keep track of the cluster centers. Once we have the cluster centers, we want to parameterize a line from the cluster center to the tree trunk; a line that is optimized by maximizing the number of leaf blocks it is touching (We have only one independent variable to optimize here, which is the height along the trunk). We can do this just by minimizing distance; no need to voxelize and calculate exact touching voxels. 
- We don't need all cluster centers to be connected directly to the center of the tree. Some clusters may be sub-clusters of another. As a result, we want to calculate the closest branch that comes *from a larger cluster* (within a certain range), and parameterize a line from the smaller cluster center to the larger branch using the same approach as above. If this new parameterized line is shorter than the original parameterized line to the tree trunk, the smaller cluster is now a sub-branch of the larger cluster. 
- Voxelize branches. We can determine the block types to use for the tree based on some geojson data for the UBC campus; trees outside of this coverage are set based on the average color of the leaves for the given cluster, determined via orthographic imagery.

___

## Street data and other touches

There's a lot of data that isn't covered in the LiDAR Data or orthographic imagery. This section outlines some smaller details that help create an immersive and true-to-life world. 

### Road markings

We use operational geospatial data containing roads as vectors along with information about the given road, i.e. number of lanes in each direction, road type, etc. We can lay this data overtop of the voxelized DEM prior to building and tree placement to get yellow and white line markings. The block types of the road were still determined in the colorization of the DEM, so there is no need to re-color at this stage for areas within UBC. We could, however, re-color the UEL roads as those do not have as in-depth data regarding hard surface type. 

Sidewalk data additionally keeps track of crosswalks; as such, we can place markings for those as well. 


### Road Signs

This operational geospatial data also contains information about traffic impactors. This information can be used to place road signs (using a pre-determined structure) after a quick coordinate transformation.

### Hiking Trails

Most hiking trails will have been missed in the DEM. Every sidewalk marked as a trail will be laid overtop of the DEM (replacing the top blocks with a trail type matched to block type), with signs placed at trailheads and the trail name as the sign data. 