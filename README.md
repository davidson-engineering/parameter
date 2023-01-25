# graph-network
### A simple graph network comprising of nodes and edges for network analysis

This module implements basic *Node*, *Edge* and *GraphNetwork* classes.


```
from graphnet.node import Node
from graphnet.edge import Edge
from graphnet.network import GraphNetwork

# create nodes
node0 = Node()
node1 = Node()
node2 = Node()
nodes = [node0, node1, node2]
    
# create edge
path0 = Edge(nodes=set((node0, node1)))
path1 = Edge(nodes=set((node1, node2)))
path2 = Edge(nodes=set((node2, node0)))

# create graph network
network = GraphNetwork(nodes=nodes)
```
It supports building of a graph network from an excel file template.
```
from graphnet.network import read_graph_network_from_xls

filepath = "tests\example_graph_network_input.xlsx"
network = read_graph_network_from_xls(filepath)
```
