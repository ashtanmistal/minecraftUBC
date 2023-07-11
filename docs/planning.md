# UBC Minecraft Project Planning Document

Written by: Ashtan Mistal

*Interested in helping out with the project? See the [Work to be done](#work-to-be-done) section for more information.*

## Table of Contents
- [UBC Minecraft Project Planning Document](#ubc-minecraft-project-planning-document)
  - [Table of Contents](#table-of-contents)
  - [Project Description](#project-description)
  - [Project Goals](#project-goals)
  - [Project Team](#project-team)
- [Work to be done](#work-to-be-done)
  - [LiDAR Data Transformation](#lidar-data-transformation)
  - [Tree Trunk Placement](#tree-trunk-placement)
  - [Ground Denoising](#ground-denoising)
  - [Manual Work](#manual-work)

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

## Project Team

The current project team consists of:
- Ashtan Mistal
- Eve Sankar
- Jon
- Hod Kimhi

# Work to be done

This section outlines the work that needs to be done to complete the project. Specific task handling is done via GitHub issues. 

## LiDAR Data Transformation

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
- Assessing the level of smoothing required for the LiDAR data based on the transformed world file. The smoothing is carried out in the [WorldEdit work](#manual-work) section.

## Tree Trunk Placement

The LiDAR data does not differentiate between tree trunks and leaves, and thus a different method must be used to place the tree trunks. We will be utilizing a stepwise tree detection approach as discussed in [this research paper](https://doi.org/10.3390/rs15051241) through mean shift clustering. The following tasks are required for this:

- 2D horizontal mean shift clustering for individual tree detection.
  - 2D was preferred in the study above due to the fact that 3D analysis focuses on the crown of the tree, which is not useful for our purposes as it ignores stem points.

## Ground Denoising

There's a lot of holes in the ground that need to be filled in. As a result, some algorithms are being researched to detect and fill in holes in the ground. This will be carried out as a plugin for the Amulet Editor, which is a tool that allows for editing of Minecraft worlds. This task is not yet started. 

## Manual Work

See [the building document](building.md) for more information.
