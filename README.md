# minecraftUBC

The UBC Minecraft Project is a project that aims to recreate the UBC Vancouver Campus inside a Minecraft world, in a 1:1 scale. The project is currently a collaboration between Ashtan Mistal and the UBC Electrical and Computer Engineering Student Society. 

It's built by by manipulating LiDAR data (available [here](https://opendata.vancouver.ca/explore/dataset/lidar-2022/information/)) into Minecaft blocks after a series of coordinate transformations and rotations.Then, details such as accurate coloring, windows, and other details are manually added (in-progress). It's therefore a full 1:1 scale recreation, to the extent that Minecraft allows. 

Right now, the project is available as a world download (see below), but will be hosted on a server soon. 

It is intended to be used as a platform for students to explore the campus, and has a potential for event hosting once it is completed. It'll allow students new to UBC to explore the campus and get a feel for the campus before they arrive, and students who are currently studying at UBC to explore in a new way.


Read more about the project and its current progress in the [planning documentation](https://github.com/ashtanmistal/minecraftUBC/blob/master/planning/planning.md). **Interested in helping? Read through the planning document, and then join the [Discord server](https://discord.gg/FqbDJNPgDu) to get in touch with me and other builders, and for more project updates.**

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

___

# FAQ

- I want to build some buildings! How do I get started?
  - Join the [Discord server](https://discord.gg/FqbDJNPgDu) and we'll get you set up.
- I want to help out, but I don't want to build buildings. What else can I do?
  - There's lots of other things to do! See the [planning document](https://github.com/ashtanmistal/minecraftUBC/blob/master/planning/planning.md) for a list of things to do. Mainly it's finding some floor plans and putting them in the spreadsheet, or finding some photos of areas Google Maps doesn't capture. 
- Why are there lots of holes in the ground?
  - The LiDAR data is not perfect, and there are lots of holes in the data. I'm working on a way to fill in these holes automatically, but it's a slow process. Right now I'm just filling in the holes by hand as I go along but not worrying about it too much.
- Why are there lots of floating trees?
  - Tree trunks usually aren't visible from the sky - it's just the leaves that are - so tree trunks are a work in progress. See mean shift clustering above.
- Some of the buildings only have partial walls. Why?
  - See "holes in the ground" above. This doesn't matter too much as the LiDAR data just provides a useful skeleton for the buildings, and the rest is built by hand (using WorldEdit).
