from data_structures.graph import Graph
class RoutePlanner:
    def __init__(self):
        self.graph=Graph()
        for u,v,w in [("A","B",5),("B","C",4),("A","D",7),("D","C",3)]:self.graph.add_edge(u,v,w);self.graph.add_edge(v,u,w)
    def shortest_route(self,source,target):return self.graph.shortest_path(source,target)
