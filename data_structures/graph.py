import heapq

class Graph:
    def __init__(self):
        self.adjacency_list = {}

    def add_vertex(self, vertex):
        self.adjacency_list.setdefault(vertex, [])

    def add_edge(self, source, destination, weight):
        self.add_vertex(source)
        self.add_vertex(destination)
        self.adjacency_list[source].append((destination, weight))
        self.adjacency_list[destination].append((source, weight))

    def get_neighbors(self, vertex):
        return self.adjacency_list.get(vertex, [])

    def dijkstra(self, start, destination):
        if start not in self.adjacency_list or destination not in self.adjacency_list:
            return float("inf"), []

        distances = {v: float("inf") for v in self.adjacency_list}
        previous = {v: None for v in self.adjacency_list}
        distances[start] = 0
        priority_queue = [(0, start)]

        while priority_queue:
            current_distance, current_vertex = heapq.heappop(priority_queue)
            if current_distance > distances[current_vertex]:
                continue
            if current_vertex == destination:
                break

            for neighbor, weight in self.adjacency_list[current_vertex]:
                distance = current_distance + weight
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous[neighbor] = current_vertex
                    heapq.heappush(priority_queue, (distance, neighbor))

        if distances[destination] == float("inf"):
            return float("inf"), []

        path = []
        current = destination
        while current is not None:
            path.append(current)
            current = previous[current]
        path.reverse()
        return distances[destination], path

    def display(self):
        print("\n========== ROAD NETWORK ==========")
        for vertex, neighbors in self.adjacency_list.items():
            connections = ", ".join(f"{neighbor}({weight})" for neighbor, weight in neighbors)
            print(f"{vertex} -> {connections}")
