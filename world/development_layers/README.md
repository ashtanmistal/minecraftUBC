# README: Info regarding the development_layers folder

This folder contains manual backups that are created during the development process. These are different from the backups that are created by the server - Those are created in a separate branch and are pushed to the `world/UBC` folder in the `server-backups` branch approximately every 12 hours or longer as changes are made.

The purpose of these manual backups is for ease of use during development as debugging the script requires access to the most recent world state prior to script running. They also allow for visualization of the world building process as each layer is completed. If you want to see the process of the scripts more in-depth by using a Minecraft map visualization, these manual backups provide that. As such, the order in which the layers are added are as follows:

1. `UBC_default_ocean`: The default seed and terrain generation provided by Minecraft. This is the base layer that all other layers are built upon.
2. `UBC_noncolorized_dem`: The initial world created by the DEM script that transforms and interpolates ground LiDAR data. After that layer is created, that world has also been ran through the `flood_fill/fill_region.py` script that fills in and interpolates any additional holes that were left by the initial DEM creation script. These holes are inherent to the method chosen, which was to create a convex hull on a per-chunk basis. This worked great for smaller holes within chunks, but many chunks that had larger holes (and as such a significant lack of ground data), additional filling through `fill_region` was required. 
3. `UBC_colorized_dem`: The world created by the `colorize_dem` script that adds color to the DEM world. The color is determined from the geojson data that is available, and places things such as roads, ground cover, and water according to the data. A flood fill algorithm was used to fill in these regions - This worked for almost every area, however there were some areas that had a long and skinny portion where the voxelization led to the flood fill not filling in the whole area. This was fixed by running the `flood_fill/flood_block_replace.py` script for the areas. This also enabled randomization to take place, which further naturalizes the area. 
4. `UBC_buildings`: Once the area was colorized, we could add buildings. THis is using the same process as last time for the building addition, as other methods were not reliable in removing tree data or coloring the buildings. Building coloring can be done using the `flood_fill/building_recolor.py` script, which uses a modified horizontal flood fill algorithm that separates walls from roofs and allows a different block to be chosen for each. Building re-coloring can be done at any time, and as such the current focus is trees and other more important landscaping processes. 
5. `UBC_with_trails`: A simple curve voxelization, block selection, and trail placement algorithm allowed all the UEL trails to be placed into the world. 
6. `UBC_with_traffic_impactors`: Road data is available for all of BC; this data includes information to where traffic impactors such as stop signs, yield signs, roundabouts, and streetlights are. Although this data is not accurate to the specific position of these impactors, we can estimate the positions of them and place them into the world. Some more complex impactors were placed manually (e.g. streetlights) as the small number of them and their complexity made it not worth the time to create a script for them.