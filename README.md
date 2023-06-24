# minecraftUBC

The UBC Minecraft Project is a project that aims to recreate the UBC Vancouver Campus inside a Minecraft world, in a 1:1 scale. The project is currently a collaboration between Ashtan Mistal and the UBC Electrical and Computer Engineering Student Society. 
The project will be hosted on a server that is accessible to all UBC students, and will be used as a platform for students to explore the campus, and a potential for event hosting once it is completed. The project will allow students new to UBC to explore the campus and get a feel for the campus before they arrive, and will allow students who are currently studying at UBC to explore the campus in a new way.
The project will be built in a 1:1 scale, meaning that 1 block in Minecraft will be equal to 1 meter in real life. This will allow students to explore the campus in a way that is as close to real life as possible.

The project works by manipulating LiDAR data (available [here](https://opendata.vancouver.ca/explore/dataset/lidar-2022/information/)) into Minecaft blocks after a series of coordinate transformations and rotations. 

Read more about the project and its current progress in the [planning documentation](https://github.com/ashtanmistal/minecraftUBC/blob/master/planning/planning.md). 

## Download

See [here](https://github.com/ashtanmistal/minecraftUBC/tree/master/world/UBC) for the current world. See an ocean and not UBC? Make sure you're spawning around `2500, 28, -1000`, and that you've copied the `region` folder as well. 

## Screenshots and Renders

The below screenshots and renders is after processing the LiDAR data into Minecraft blocks. No additional blocks have been placed. These screenshots will be updated as progress allows.

![image](https://github.com/ashtanmistal/minecraftUBC/assets/70030490/91dda6d4-b54b-4fef-9cfa-6297f8112a3c)

Render of north campus using Avoyd.

![2023-05-26_17 12 32](https://github.com/ashtanmistal/minecraftUBC/assets/70030490/98a55ca9-cf15-44cd-8613-39d2ebf50792)

Screenshot of the IKB / Koerner Library area. 


## Current Progress

Right now, I'm working on utilizing a mean shift clustering algorithm to pinpoint the centroid of trees in order to place tree trunks, using a similar method as outlined in [this research paper](https://doi.org/10.3390/rs15051241). Afterwards, I'll be re-assessing the color and texture mapping approach used for matching a given building to a block pallete. The world will then be de-hollowed and then released to the public on a server, where the interiors of buildings will be built by hand (aided by floor plans, 3d scans, and photos where available). 

## Helping Out

I'm looking for builders to help out with the project. Right now we're in the process of setting up a server, so for now take a look at the world to get a feel of what's required for an individual building and what buildings you'd like to work on.

Please visit the [Discord server](https://discord.gg/FqbDJNPgDu) to get in touch with me and other builders, and for more project updates.
