# Testing the LiDAR data to have more of an idea of what we're working with
import numpy as np
import math
import pylas
import matplotlib.pyplot as plt

# load the data
data = pylas.read("LiDAR LAS Data/las/481000_5456000.las")

x, y, z = data.x, data.y, data.z
rgb = data.red, data.green, data.blue
class_data = data.classification  # classificaiton is bullshit by the looks of it... too much wrongly classified as
# noise or water
pass
pass
x = x - 481000
y = y - 5456000
rotation_degrees = 29.5
rotation = math.radians(rotation_degrees)

# rotate the data
inverse_rotation_matrix = np.array([[math.cos(rotation), math.sin(rotation), 0],
                                    [-math.sin(rotation), math.cos(rotation), 0],
                                    [0, 0, 1]])
x, y, z = np.matmul(inverse_rotation_matrix, np.array([x, y, z]))
pass

# plot the data (take every 10th point to speed up the plotting)
plt.scatter(x[::10], y[::10], s=0.1, c=z[::10], cmap='viridis')
plt.show()