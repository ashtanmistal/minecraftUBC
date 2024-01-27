# minecraftUBC

### Table of Contents:
- [Introduction](#introduction)
- [Server and World Download](#server-and-world-download)
- [Helping Out + Project Contributors](#helping-out)
- [Screenshots and Renders](#screenshots-and-renders)

## Introduction

The UBC Minecraft Project is a project that aims to recreate the UBC Vancouver Campus inside a Minecraft world, in a 1:1 scale. It's built by transforming LiDAR data, operational geospatial data, and various reference imagery through surface reconstruction, data processing, and machine learning algorithms. **Read more about the development and world-building pipeline in the [transformation pipeline document](docs/transformation_pipeline.md)**. This sculpted world is then manually touched up by a team of builders to add details such as accurate wall coloring, windows, and other details. It's therefore a full 1:1 scale recreation of campus to the extent that Minecraft allows.

**Note: This project uses submodules. Please clone with `git clone --recurse-submodules https://github.com/ashtanmistal/minecraftUBC.git` if you want to clone the deep learning submodules as well.** If you just want to download the world, there's no need to clone the submodules.

## Server and World Download

If you're looking to check out the world on the server, please see the [Discord server](https://discord.gg/FqbDJNPgDu) for the IP address. That's where current world progress is now being developed, with backups to GitHub.

Those regular backups to GitHub are available in this repository in the [server auto backups branch](https://github.com/ashtanmistal/minecraftUBC/tree/server-auto-backups), under the `world/UBC` directory. The master branch holds the latest "stable" version in case of corruption or other issues with the server. The world is backed up approximately every 12 hours. 

If you're looking for what the world looks like after various processing steps you can check out the `world/development_layers` directory.


## Helping Out

We're currently looking for more builders to help out with the manual side of the project! If you're interested in helping out, please join the [Discord server](https://discord.gg/FqbDJNPgDu) and check out the #building-resources channel for more information.

### Project Contributors

An exhaustive list of builders is available in the spreadsheet listed in the [building document](docs/building.md).

The following people have contributed to the project outside the manual building process:
- Ashtan Mistal
- Hod Kimhi
- Eve Sankar
- Bryce Wilson


## Screenshots and Renders

The full album of screenshots is available in the [docs/screenshots](docs/screenshots) directory.

![2023-07-15_12.58.24.png](docs/screenshots/2023-07-15_12.58.24.png)

![2023-07-15_13.17.35.png](docs/screenshots/2023-07-15_13.17.35.png)

![2023-07-15_14.06.13.png](docs/screenshots/2023-07-15_14.06.13.png)

![2023-07-15_14.32.38.png](docs/screenshots/2023-07-15_14.32.38.png)
