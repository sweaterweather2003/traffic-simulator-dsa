import heapq


class Graph:
    def __init__(self):
        self.adj = {}
        self.adjacency_list = self.adj

    def add_vertex(self, vertex):
        self.adj.setdefault(vertex, [])

    def add_edge(self, source, destination, weight, bidirectional=True):
        if weight < 0:
            raise ValueError("Dijkstra's algorithm requires non-negative edge weights.")
        self.add_vertex(source)
        self.add_vertex(destination)
        if not any(node == destination for node, _ in self.adj[source]):
            self.adj[source].append((destination, weight))
        if bidirectional and not any(node == source for node, _ in self.adj[destination]):
            self.adj[destination].append((source, weight))

    def get_neighbors(self, vertex):
        return self.adj.get(vertex, [])

    def dijkstra(self, start, destination=None):
        if start not in self.adj:
            if destination is not None:
                return float("inf"), []
            return {}, {}

        distances = {vertex: float("inf") for vertex in self.adj}
        previous = {vertex: None for vertex in self.adj}
        distances[start] = 0
        pending = [(0, start)]

        while pending:
            distance, current = heapq.heappop(pending)
            if distance != distances[current]:
                continue
            if current == destination:
                break
            for neighbor, weight in self.adj[current]:
                candidate = distance + weight
                if candidate < distances[neighbor]:
                    distances[neighbor] = candidate
                    previous[neighbor] = current
                    heapq.heappush(pending, (candidate, neighbor))

        if destination is None:
            return distances, previous
        if destination not in distances or distances[destination] == float("inf"):
            return float("inf"), []
        path = []
        current = destination
        while current is not None:
            path.append(current)
            current = previous[current]
        return distances[destination], path[::-1]

    def shortest_path(self, source, destination):
        distance, path = self.dijkstra(source, destination)
        return path, distance

    def display(self):
        print("\n========== ROAD NETWORK ==========")
        for vertex, neighbors in self.adj.items():
            connections = ", ".join(f"{neighbor}({weight})" for neighbor, weight in neighbors)
            print(f"{vertex} -> {connections}")
