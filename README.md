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
