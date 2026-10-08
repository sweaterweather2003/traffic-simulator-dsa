<<<<<<< HEAD
# ML + DSA Intelligent Traffic Signal Optimization

This is the merged version of the earlier plain-DSA traffic project.

## Preserved DSA layer
- FIFO lane queues
- emergency priority queue
- max heap for phase ranking
- graph + Dijkstra route planner
- fixed-time baseline
- longest-queue baseline
- Max-Pressure baseline

## New research layer
- traffic-flow forecasting
- Historical Average baseline
- Random Forest
- XGBoost
- forecast-informed pressure/priority controller (FPAC)
- MAE/RMSE/R2 evaluation
- controller comparison

## Run

1. Install:
   `pip install -r requirements.txt`
2. Generate demo traffic:
   `python tools/generate_sample_data.py`
3. Train ML:
   `python main.py --train-ml --data data/sample_traffic.csv --model random_forest`
4. Compare controllers:
   `python main.py --compare --data data/sample_traffic.csv --model random_forest`
5. Run FPAC:
   `python main.py --run-fpac --data data/sample_traffic.csv --model random_forest`

Put PEMS04.csv in data/ when you are ready to use real traffic data.

## Research direction
ML predicts near-future traffic; DSA makes the interpretable control decision. The project keeps fixed-time, longest-queue and Max-Pressure baselines so the research claim can be tested rather than assumed.
=======
# Traffic Signal & Traffic Flow Simulator

A Python DSA project that simulates traffic at multiple intersections and compares fixed traffic signals with adaptive traffic signals.

## DSA Concepts
- Queue
- Priority Queue / Heap
- Graph
- Dijkstra's Algorithm
- Greedy Algorithm
- Dictionaries / Hash Maps
- Simulation

## Run
Open a terminal in this folder and run:

    python main.py

## Menu
1. Run Adaptive Traffic Simulation
2. Run Fixed Traffic Simulation
3. Display Road Network
4. Test Shortest Route
5. Compare Adaptive vs Fixed
6. Exit

## Project Structure

traffic_signal_simulator/
├── main.py
├── config.py
├── requirements.txt
├── README.md
├── models/
├── data_structures/
├── algorithms/
├── simulation/
└── utils/

No external Python packages are required.
>>>>>>> origin/main
