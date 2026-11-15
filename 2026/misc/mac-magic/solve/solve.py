import matplotlib.pyplot as plt

with open("./DS_Store", "rb") as f:
    data = f.read()

data = data.split(b"tIlocblob")
x = []
y = []
for txt_file in data:
    # Get coordinate value from hex at each filename offset
    x.append(int.from_bytes(txt_file[4:8], byteorder='big'))
    y.append(int.from_bytes(txt_file[8:12], byteorder='big'))

# Remove first point (outlier/not proper coordinate)
x.pop(0)
y.pop(0)

'''
Flip y around (as y represents value from the top, 
not bottom, so it will be flipped otherwise)
'''
max_y = max(y)
y = [max_y - i for i in y] 

fig, ax = plt.subplots()
ax.scatter(x, y, s=100)
plt.show()