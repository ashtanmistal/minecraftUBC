import math

import numpy as np

rotation_degrees = 28.000  # This is the rotation of UBC's roads relative to true north.
rotation = math.radians(rotation_degrees)
inverse_rotation_matrix = np.array([[math.cos(rotation), math.sin(rotation), 0],
                                    [-math.sin(rotation), math.cos(rotation), 0],
                                    [0, 0, 1]])
x_offset = 480000
z_offset = 5455000
game_version = ("java", (1, 19, 4))
