class RoutePlanner:
    def __init__(self, graph):
        self.graph = graph

    def find_shortest_route(self, source, destination):
        return self.graph.dijkstra(source, destination)

    def print_route(self, source, destination):
        distance, path = self.find_shortest_route(source, destination)
        if not path:
            print(f"No route found from {source} to {destination}")
            return
        print(f"\nShortest route: {' -> '.join(path)}")
        print(f"Distance: {distance}")
