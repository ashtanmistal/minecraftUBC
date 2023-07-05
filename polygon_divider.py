"""
This is a helper script for various geojson operations. It takes in a set of connected vertices representing a polygon,
and voxelizes the space through a flood fill algorithm. This voxel set is then divided into chunks for further block
operations.
"""

from scripts.deprecated.geojson.bresenham import bresenham_2d
from amulet.utils import block_coords_to_chunk_coords


# We will fake a chunk object here. What we want to keep track of is the coordinates of the chunk. The blocks in the
# chunk are kept as a boolean in a 16x16 fixed array (basically "is it in the polygon or not?").
class Chunk:
    """
    Pseudo-chunk object: a chunk object that only keeps track of the coordinates of the chunk and a boolean array of
    blocks.
    """
    def __init__(self, cx: int, cz: int):
        """
        Initialize a pseudo-chunk object with the given chunk coordinates.
        :param cx: the chunk x coordinate
        :param cz: the chunk z coordinate
        """
        self.cx = cx
        self.cz = cz
        self.blocks = [[False for _ in range(16)] for _ in range(16)]

    def __getitem__(self, item):
        """
        Get the block at the given coordinates.
        :param item: the coordinates of the block (x, z)
        :return: the block at the given coordinates
        """
        return self.blocks[item]


# We want to iterate through the vertices and use Bresenham's algorithm to get the blocks representing the edges of
