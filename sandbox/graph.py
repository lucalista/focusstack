import matplotlib.pyplot as plt
import networkx as nx

import networkx as nx
import matplotlib.pyplot as plt

G = nx.Graph()
G.add_edge(1, 2)
G.add_edge(1, 3)
G.add_edge(1, 5)
G.add_edge(2, 3)
G.add_edge(3, 4)
G.add_edge(4, 5)

#pos = {1: (0, 0), 2: (-1, 0.3), 3: (2, 0.17), 4: (4, 0.255), 5: (5, 0.03)}

options = {
    "font_size": 36,
    "node_size": 3000,
    "node_color": "white",
    "edgecolors": "#f0f0f0",
    "linewidths": 5,
    "edge_color": "#a0a0a0",
    "width": 5,
    "labels": {1: "AAA", 2: "BBB", 3: "CCC", 4: "DDD", 5: "EEE"},
    "bbox": {"ec": "k", "fc": "white", "alpha": 0.7}
}
nx.draw_networkx(G, **options)
ax = plt.gca()
ax.margins(0.20)
plt.axis("off")
plt.show()
