<<<<<<< HEAD
import argparse
from config import SimulationConfig
from simulation.traffic_simulator import TrafficSimulator
from ml.forecasting import train,load_or_train
from utils.display import comparison

def main():
 p=argparse.ArgumentParser();p.add_argument("--demo",action="store_true");p.add_argument("--train-ml",action="store_true");p.add_argument("--compare",action="store_true");p.add_argument("--run-fpac",action="store_true");p.add_argument("--data");p.add_argument("--model",default="random_forest",choices=["historical_average","random_forest","xgboost"]);p.add_argument("--steps",type=int,default=100);p.add_argument("--lookback",type=int,default=12);a=p.parse_args();cfg=SimulationConfig(steps=a.steps)
 if a.train_ml:
  model,metrics,path=train(a.data,a.model,a.lookback);print("ML metrics:",metrics);print("Saved:",path);return
 f=None
 if a.data:f=load_or_train(a.data,a.model,a.lookback)
 if a.compare:
  rs=[TrafficSimulator(cfg,f).run(c) for c in ("fixed","longest_queue","max_pressure","fpac")];comparison(rs);return
 r=TrafficSimulator(cfg,f).run("fpac" if a.run_fpac else "longest_queue");print(r.summary())
if __name__=="__main__":main()
=======
import random
from config import DEFAULT_SIMULATION_STEPS, RANDOM_SEED
from models.intersection import Intersection
from data_structures.graph import Graph
from algorithms.routing import RoutePlanner
from simulation.simulator import TrafficSimulator
from utils.display import print_title, print_menu, get_choice

def create_road_network():
    graph = Graph()
    graph.add_edge("A", "B", 5)
    graph.add_edge("A", "C", 3)
    graph.add_edge("B", "C", 2)
    graph.add_edge("B", "D", 4)
    graph.add_edge("C", "D", 6)
    graph.add_edge("C", "E", 5)
    graph.add_edge("D", "E", 2)
    return graph

def create_intersections():
    intersections = {}
    lane_map = {
        "A": [("A_B","A","B"), ("A_C","A","C")],
        "B": [("B_A","B","A"), ("B_C","B","C"), ("B_D","B","D")],
        "C": [("C_A","C","A"), ("C_B","C","B"), ("C_D","C","D"), ("C_E","C","E")],
        "D": [("D_B","D","B"), ("D_C","D","C"), ("D_E","D","E")],
        "E": [("E_C","E","C"), ("E_D","E","D")],
    }
    for node, lanes in lane_map.items():
        intersection = Intersection(node)
        for lane_id, source, destination in lanes:
            intersection.add_lane(lane_id, source, destination)
        intersections[node] = intersection
    return intersections

def run_simulation(adaptive):
    random.seed(RANDOM_SEED)
    mode = "ADAPTIVE" if adaptive else "FIXED"
    print_title(f"{mode} TRAFFIC SIGNAL SIMULATION")
    simulator = TrafficSimulator(create_intersections(), create_road_network(), adaptive)
    simulator.run(DEFAULT_SIMULATION_STEPS)
    return simulator

def display_network():
    create_road_network().display()

def test_shortest_route():
    planner = RoutePlanner(create_road_network())
    print_title("DIJKSTRA SHORTEST PATH")
    source = input("Enter source intersection (A-E): ").upper()
    destination = input("Enter destination intersection (A-E): ").upper()
    planner.print_route(source, destination)

def compare_algorithms():
    print_title("ADAPTIVE VS FIXED SIGNAL COMPARISON")
    adaptive = run_simulation(True)
    fixed = run_simulation(False)
    a = adaptive.statistics.average_waiting_time()
    f = fixed.statistics.average_waiting_time()
    print_title("FINAL COMPARISON")
    print(f"Adaptive Signal Average Wait: {a:.2f}")
    print(f"Fixed Signal Average Wait:    {f:.2f}")
    if f > 0:
        improvement = ((f - a) / f) * 100
        print(f"Adaptive improvement: {improvement:.2f}%")

def main():
    while True:
        print_menu()
        choice = get_choice()
        if choice == 1:
            run_simulation(True)
        elif choice == 2:
            run_simulation(False)
        elif choice == 3:
            display_network()
        elif choice == 4:
            test_shortest_route()
        elif choice == 5:
            compare_algorithms()
        else:
            print("\nThank you for using Traffic Signal Simulator!")
            break

if __name__ == "__main__":
    main()
>>>>>>> origin/main
