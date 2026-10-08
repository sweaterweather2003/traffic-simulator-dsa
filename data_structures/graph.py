import heapq
class Graph:
    def __init__(self):self.adj={}
    def add_edge(self,u,v,w):self.adj.setdefault(u,[]).append((v,w));self.adj.setdefault(v,[])
    def dijkstra(self,src):
        dist={v:float('inf') for v in self.adj};prev={v:None for v in self.adj};dist[src]=0;h=[(0,src)]
        while h:
            d,u=heapq.heappop(h)
            if d!=dist[u]:continue
            for v,w in self.adj[u]:
                nd=d+w
                if nd<dist[v]:dist[v]=nd;prev[v]=u;heapq.heappush(h,(nd,v))
        return dist,prev
    def shortest_path(self,src,dst):
        dist,prev=self.dijkstra(src)
        if dist.get(dst,float('inf'))==float('inf'):return [],float('inf')
        p=[];u=dst
        while u is not None:p.append(u);u=prev[u]
        return p[::-1],dist[dst]
