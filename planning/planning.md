# UBC Minecraft Project Planning Document

Written by: Ashtan Mistal

*Interested in helping out with the project? See the [Work to be done](#work-to-be-done) section for more information.*

## Table of Contents
- [UBC Minecraft Project Planning Document](#ubc-minecraft-project-planning-document)
  - [Table of Contents](#table-of-contents)
  - [Project Description](#project-description)
  - [Project Goals](#project-goals)
  - [Project Timeline](#project-timeline)
  - [Project Team](#project-team)
  - [Project Deliverables](#project-deliverables)
  - [Project Budget](#project-budget)
  - [Project Communication](#project-communication)
- [Work to be done](#work-to-be-done)
  - [LiDAR Data Transformation](#lidar-data-transformation)
  - [Orthographic Imagery Transformation](#orthographic-imagery-transformation)
  - [Floor Plan Transformation](#floor-plan-transformation)
  - [Manual Work](#manual-work)
  - [Server Hosting](#server-hosting)

## Project Description

The UBC Minecraft Project is a project that aims to recreate the UBC Vancouver Campus inside a Minecraft world, in a 1:1 scale. The project is currently a collaboration between Ashtan Mistal and the UBC Electrical and Computer Engineering Student Society.

The project will be hosted on a server that is accessible to all UBC students, and will be used as a platform for students to explore the campus, and a potential for event hosting once it is completed. The project will allow students new to UBC to explore the campus and get a feel for the campus before they arrive, and will allow students who are currently studying at UBC to explore the campus in a new way. 

The project will be built in a 1:1 scale, meaning that 1 block in Minecraft will be equal to 1 meter in real life. This will allow students to explore the campus in a way that is as close to real life as possible.

## Project Goals

- Exterior of all buildings on campus will be built in a 1:1 scale, using transformed LiDAR data from the UBC Campus.
- Foliage and roads will also be generated using this LiDAR data.
- Orthographic imagery will be used to select the color palette for the buildings.
- Building interiors will be created by gathering floor plans from various UBC websites, and compiled into an organized document. See [the spreadsheet](https://docs.google.com/spreadsheets/d/16vR1eYbdkNVdfTgkR4nw5c2QBYRDDq_WJ4L-AfOAfrM/edit?usp=sharing) for more information.
- Once the automated work is done, the project will be opened up to the public for manual work. This will include lots of WorldEdit work to fill in holes in the world in areas that the LiDAR data did not capture (i.e. under trees, inside buildings, etc.), as well as adding water features, and other aesthetic features. See the [Work to be done](#work-to-be-done) section for more information.
- The project will be hosted on a server that is accessible to all UBC students during building. A world download will be provided once the project is completed, and the server will be publicly accessible as long as funding permits.

## Project Timeline
- LiDAR data transformation will be completed by the end of May 2023, and the orthographic imagery shortly after.
- Manual transformation of exteriors will be in-progress in early June 2023, and will be completed by the end of August 2023. This encompasses all manual work except for building interiors.
- Server hosting will need to be sorted in mid June. This is dependent on the number of volunteers that are available to help with this task.
- Building interiors will be completed by the end of August 2023. This is dependent on the number of volunteers that are available to help with this task and the speed at which the project progresses.
- A website will need to be created by the end of August 2023. This is dependent on the progress of the project.


## Project Team

The current project team consists of:
- Ashtan Mistal
- Eve Sankar
- Jon
- Hod

## Project Deliverables

- A Minecraft world file that contains the UBC Vancouver Campus, in a 1:1 scale.
- A Python-based tool that can be used to transform LiDAR data into Minecraft blocks. (done)
- A Python-based tool that can be used to transform orthographic imagery into a dictionary of Minecraft blocks by object recognition and color matching.
- A Python-based tool that can be used to transform floor plans into a WorldEdit schematic file.

## Project Budget

TODO: Add budget once determined. Budget is needed for:
- Server hosting
- Project website domain (potentially)
- TODO: Add more once determined

## Project Communication

Current project communication is on Discord with the project leads and will be transformed into a Discord server once public communication and advertisement is required for the project. 


# Work to be done

This section outlines the work that needs to be done to complete the project. the specific assignments for tasks requiring multiple people will be done on a spreadsheet, and will be linked under each subsection once it is created.

## LiDAR Data Transformation (done)

Assigned to: Ashtan Mistal

This work primarily involves the following tasks:
- Calculating the rotation of UBC's roads from true north to be used as a rotation matrix for the LiDAR data. _(Current status: done)_
- Calculating the height offset of the LiDAR data such that the sea level corresponds to the current world generation height in the superflat world. _(Current status: done)_
- Writing a script to transform the LiDAR data into a Minecraft world file. _(Current status: Done)
  - This tool first de-noises the LiDAR data by removing all points that are unclassified, classified as noise, or are otherwise uninteresting for the transformation requirements. 
  - It then transforms the LiDAR data using the rotation matrix. 
  - It then separates the LiDAR data into chunks based on the chunk size of the Minecraft world.
  - For each chunk, the data is quantized to be assigned to a given block, where the classification and average color are then used to match the LiDAR data to a Minecraft block.
  - The block is then placed into the Minecraft world file based on the offsets assigned, and this process is repeated for every block with LiDAR data in the chunk.
  - The process is then repeated for every chunk in the LiDAR data.
- Assessing the level of de-noising required for the LiDAR data based on the transformed world file. The de-noising is carried out in the [WorldEdit work](#manual-work) section. _(Current status: Not started)_
- Assessing the level of smoothing required for the LiDAR data based on the transformed world file. The smoothing is carried out in the [WorldEdit work](#manual-work) section.

## Tree Trunk Placement

Assigned to: Ashtan Mistal

The LiDAR data does not differentiate between tree trunks and leaves, and thus a different method must be used to place the tree trunks. We will be utilizing a stepwise tree detection approach as discussed in [this research paper](https://doi.org/10.3390/rs15051241) through mean shift clustering. The following tasks are required for this:

- 2D horizontal mean shift clustering for individual tree detection.
  - 2D was preferred in the study above due to the fact that 3D analysis focuses on the crown of the tree, which is not useful for our purposes as it ignores stem points.

Current progress: Analyzing optimal choice for search kernel.

## Orthographic Imagery Transformation

Assigned to: Ashtan Mistal (Help appreciated)

_(Current status: Not started)_

The LiDAR data is excellent for determining the overall shape of the buildings and trees but does not accurately capture data regarding the color of the buildings; the colors that were captured were strongly grayscale and based on the amount of light hitting a given building at the time the LiDAR data was captured. This means that the LiDAR data is not suitable for determining the color of the buildings, and thus a different method must be used.
A manual method is applicable for this, but may be more slow given the amount of buildings on campus. Thus, an automated method is preferred. The following tasks are required for this:
- Writing a script to match a pixel location in the orthographic imagery to a block in the Minecraft world.
  - This tool must calculate a bounding polygon for each building in the imagery, and ignore shadows and other features that are not important to color matching.
  - The tool must then determine the specific Minecraft block to match to the roof of the building. This can either be done using texture analysis or a simple average of the color of the roof, and then determine the minimum difference match to the texture or average color match in the Minecraft block palette selected in the script. 
  - This match will be assigned to the building in Minecraft, either by using a Python script to replace all blocks in the bounding polygon with the matched block, or by placing a block at the location of the roof (requiring manual replacement of the blocks, but may be more accurate than an automated method). Regardless of the method chosen this will speed up the process of coloring the buildings in the Minecraft world.
  - The process is then repeated for every building in the orthographic imagery.

## Floor Plan Transformation

Assigned to: Eve Sankar, Jon, Ashtan Mistal

Current status: In progress

There is a lot of work to be done in this section. Not all the floor plans of UBC are accessible to the public nor are they all in one place. 

The primary work that has to be done is assembling and organizing the floor plans into a single document.

If time permits, a script will be written to transform the floor plans into a WorldEdit schematic file. 
This will allow the floor plans to be easily placed into the Minecraft world file. Else, these floor plans will be provided to volunteers working on the interior of the buildings. If floor plans are not available, the interior will be left empty apart from floor division and windows.

Floor plans are also available in-person via fire exit plans. This is a backup option, however, and will be incredibly time-consuming and likely not worth the effort.

## Manual Work

Assigned to: Everyone interested in helping

There is lots of manual work to be done in this project. This includes:
- **Transforming interiors**. This is a big task and is separated into a separate document. This document will be linked here once it is created. (TODO)
- Making the world not hollow, and replacing any holes in the ground left by the LiDAR data. Most of this is WorldEdit work to significantly speed up the process. 
- Placing shrubs and smaller touches to the world. Right now it looks really good from above, but it would be great to have signs, benches, and other small details to make the world feel more alive.
- Trimming trees. As Minecraft's trees make a whole square meter of leaves (!) if leaves are detected by the LiDAR sensor, this makes the trees look very busy and make it more difficult to a player not in spectator mode to traverse the ground. Especially trees around walkways, making the campus walkable is a priority. Trees in tree-dominated areas do not need to be trimmed, however.

## Server Hosting

Assigned to: Hod

_(Current status: In progress, waiting for world file to be completed)_

We need a server to host the Minecraft world, but this will be determined later once we know more about budget and the size of the world file. This will need to be done prior to getting volunteers to work on the manual work, however, as the world file will need to be hosted somewhere for people to be able to work on the project. 

Reaching out to the UBC Minecraft Club may be a good idea for this, as they may have a server that can be used for this project.

## Other Work

- **Website**. A website is required to provide information about the project. This is not a priority, however, and will be done once the project is complete. Currently assigned to Ashtan Mistal.
- **Project advertisement**. This is a priority to get volunteers for the manual work. Currently assigned to everyone interested.
