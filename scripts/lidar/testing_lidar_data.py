# Testing the LiDAR data to have more of an idea of what we're working with
import numpy as np
import math
import pylas
import matplotlib.pyplot as plt

# load the data
data = pylas.read("LiDAR LAS Data/las/481000_5458000.las")

x, y, z = data.x, data.y, data.z
rgb = data.red, data.green, data.blue
class_data = data.classification
# Labels:
# 1. Unclassified;
# 2. Bare - earth and low grass;
# 3. Low vegetation(height < 2m);
# 4. High vegetation(height > 2m);
# 5. Water;
# 6. Buildings;
# 7. Other;
# 8. Noise(noise points, blunders, outliners, etc)

# hist of class data
# plt.hist(class_data, bins=8)
# plt.show()

# pass
# pass
# x = x - 481000
# y = y - 5456000
# rotation_degrees = 29.5
# rotation = math.radians(rotation_degrees)
#
# # rotate the data
# inverse_rotation_matrix = np.array([[math.cos(rotation), math.sin(rotation), 0],
#                                     [-math.sin(rotation), math.cos(rotation), 0],
#                                     [0, 0, 1]])
# x, y, z = np.matmul(inverse_rotation_matrix, np.array([x, y, z]))
# pass
#
# # plot the data (take every 10th point to speed up the plotting)
# plt.scatter(x[::10], y[::10], s=0.1, c=z[::10], cmap='viridis')
# plt.show()

# let's plot the data, using the class data to color the points
# unclassified should be red
# bare earth and low grass should be green
# low vegetation should be blue
# high vegetation should be yellow
# water should be cyan
# buildings should be magenta
# other should be white
# noise should be black
# colors = ['red', 'green', 'blue', 'yellow', 'cyan', 'magenta', 'white', 'black']
# for i in range(8):
#     indices = np.where(class_data == i)
#     plt.scatter(x[indices], y[indices], s=0.1, c=colors[i])
# plt.show()

# let's zoom into 481800 < x < 482000 and 5456000 < y < 5456200
# indices = np.where((x > 481000) & (x < 481600) & (y > 5456000) & (y < 5456400))
# x = x[indices]
# y = y[indices]
# z = z[indices]
# class_data = class_data[indices]
#
colors = ['red', 'green', 'blue', 'yellow', 'cyan', 'magenta', 'white', 'black', 'orange']
# for i in range(8):
#     indices = np.where(class_data == i)
#     plt.scatter(x[indices], y[indices], s=0.1, c=colors[i])
# plt.show()


fig, ax = plt.subplots(3, 3, figsize=(50, 50))
fig.suptitle('LiDAR Data')
for i in range(9):
    indices = np.where(class_data == i+1)
    ax[i // 3, i % 3].scatter(x[indices], y[indices], s=0.1, c=colors[i])
    ax[i // 3, i % 3].set_title(f'Class {i+1}')
plt.show()
