# minecraftUBC

The UBC Minecraft Project is a project that aims to recreate the UBC Vancouver Campus inside a Minecraft world, in a 1:1 scale. The project is currently a collaboration between Ashtan Mistal and the UBC Electrical and Computer Engineering Student Society, with a team of builders assembled from various social media platforms.

It's built by manipulating LiDAR data (available [here](https://opendata.vancouver.ca/explore/dataset/lidar-2022/information/)) into Minecraft blocks. The exact pipeline is described in the [transformation pipeline document](https://github.com/ashtanmistal/minecraftUBC/blob/master/transformation_pipeline.md). Then, details such as accurate coloring, windows, and other details are manually added. It's therefore a full 1:1 scale recreation, to the extent that Minecraft allows. 

Right now, the project is available as a world download (see below), and is also hosted on a public server (see the [Discord server](https://discord.gg/FqbDJNPgDu) for the link). 

It is intended to be used as a platform for students to explore the campus, and has a potential for event hosting once it is completed. It'll allow students new to UBC to explore the campus and get a feel for the campus before they arrive, and students who are currently studying at UBC to explore in a new way.


Read a bit more about the project and its current progress in the [planning documentation](https://github.com/ashtanmistal/minecraftUBC/blob/master/planning/planning.md). **Interested in helping? Read through the planning document, and then join the [Discord server](https://discord.gg/FqbDJNPgDu) to get in touch with me and other builders, and for more project updates.**

## Download

**Looking to check out the world? See the [Discord server](https://discord.gg/FqbDJNPgDu) for the link to the server. That's where current world progress is now being developed, with backups to GitHub.**

See [here](https://github.com/ashtanmistal/minecraftUBC/tree/master/world/UBC) for the current world. See an ocean and not UBC? Make sure you're spawning around `2500, 28, -1000`, and that you've copied the `region` folder as well. Having other issues? Please ping me on Discord in the server. 

## Screenshots and Renders

The below screenshots and renders is after processing the LiDAR data into Minecraft blocks, with some touch-ups in various buildings. These screenshots will be updated as progress allows.

![2023-06-23_11 36 12](screenshots/2023-06-23_11.36.12.png)

Screenshot of some Ponderosa progress.

![2023-06-23_11 40 20](screenshots/2023-06-23_11.40.20.png)

IKB, Ladner clock tower, and Buchanan tower.

![2023-06-23_12 17 01](screenshots/2023-06-23_12.17.01.png)

Wreck Beach south of the stairs, with some residence buildings in the background.


![image](https://github.com/ashtanmistal/minecraftUBC/assets/70030490/91dda6d4-b54b-4fef-9cfa-6297f8112a3c)

Render of north campus using Avoyd.

## Helping Out

I'm looking for builders to help out with the project! Please visit the [Discord server](https://discord.gg/FqbDJNPgDu) to get in touch with me and other builders, and for more project updates.

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

Many of the FAQ questions will be resolved in the second iteration of the terrain transformation pipeline, which you can read about [here](https://github.com/ashtanmistal/minecraftUBC/blob/master/transformation_pipeline.md). 
