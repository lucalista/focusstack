import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

import networkx as nx
import matplotlib.pyplot as plt

options = {
    "font_size": 12,
    "node_size": 1000,
    "node_color": "white",
    "edgecolors": "#f0f0f0",
    "linewidths": 3,
    "edge_color": "#a0a0a0",
    "width": 3,
    "labels": {1: "working path", 2: "input path", 3: "job",
               4: "combined actions", 5: "align", 6: "balance", 7: "stack"},
    "bbox": {"ec": "k", "fc": "white", "alpha": 0.7},
}
G = nx.Graph()
G.add_edge(1, 2)
G.add_edge(2, 3)
G.add_edge(3, 1)
G.add_edge(3, 2)
G.add_edge(4, 3)
G.add_edge(5, 4)
G.add_edge(6, 4)
G.add_edge(7, 3)
edge_nodes = set(G) - {1}
pos = nx.circular_layout(G.subgraph(edge_nodes))
pos[1] = np.array([0, 10])
nx.draw_networkx(G, pos, **options)
ax = plt.gca()
ax.margins(0.20)
plt.axis("off")
plt.show()
