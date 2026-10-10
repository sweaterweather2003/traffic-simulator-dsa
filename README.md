# ML + DSA Intelligent Traffic Signal Optimization

Traffic simulation with FIFO lane queues, adaptive signal controllers, temporal forecasting, spillback-aware routing, a four-intersection road network, and an optional shared-policy PPO experiment.

## Install

```powershell
pip install -r requirements.txt
```

## Interactive animation

Start the single-intersection simulator:

```powershell
python main.py --animate
```

Optionally initialize forecasts using historical traffic data:

```powershell
python main.py --animate --data data/PEMS04.npz --model random_forest
```

The single-intersection view opens paused with a live coach. Drag vehicles between approaches, use **N** to simulate one step, or press **Space** to let the selected controller run. Arrivals vary randomly around the configured mean. Each completed step is appended to `data/simulation_log.csv`; an online queue forecaster learns from each observed state transition, saves to `models_saved/interactive_queue_sgd.joblib`, and reports its forecast error in the coach panel. It warms up on eight transitions and continues learning across resets and launches. This forecast is advisory; it does not replace the selected signal controller.

For the connected four-intersection network:

```powershell
python main.py --network --animate --controller spillback
python main.py --network --animate --data data/PEMS04.npz --model random_forest --controller forecast
```

The network view starts paused in manual traffic mode. Click a node to set a trip start, Shift-click another node to set a destination, and press **V** to release a car onto its graph route. Cars travel along links for multiple one-second simulation steps and wait at junctions for their signal phase. Press **I** and click a road to create a two-minute closure; queued traffic builds upstream, route advice avoids the closed road, and **C** clears incidents. Press **M** to toggle background demand. These are discrete car-following/queue dynamics for instruction and controller evaluation, not calibrated vehicle physics or real-world ETA predictions.

For PEMS-guided game learning, start the network view with `--data data/PEMS04.npz`. The PEMS-trained Random Forest provides aggregate historical-flow forecasts as input; each simulated game step is then scored against its observed next network queue before an online SGD queue model updates. Its prequential MAE measures predictions on game-generated data, not PEMS test error. The online game model persists separately at `models_saved/interactive_network_queue_sgd.joblib`; the per-step game records are saved to `data/network_simulation_log_v2.csv`.

The route buddy ranks open paths using current road queues, link travel time, capacity and signal delay. It highlights the lowest estimated-time route and compares alternatives using one simulated second per step. Estimates are simulation-time comparisons, not real-world ETAs.

The network display shows connected intersections, signal phases and clearance intervals, queues, network throughput, completed trips, wait/travel-time metrics, spillback and incident blockages. Each car follows a shortest open route and has a per-link travel time; a signal or road closure can hold it at a junction and cause an upstream queue.

Each single-intersection step is appended to `data/simulation_log.csv`. Network animation runs append one row per intersection per step to `data/network_simulation_log_v2.csv`. Both logs include run IDs and timestamps, preserve previous runs, and leave `data/sample_traffic.csv` untouched.

### Keyboard controls

- **Space**: pause or resume
- **N**: advance one step while paused
- **R**: reset; start a new log run
- Single intersection: drag vehicles between approaches while paused; **WASD** or right-drag pans the street view
- Single intersection **1–4**: fixed-time, longest-queue, max-pressure, or forecast-informed controller
- Network **1–5**: fixed-time, longest-queue, max-pressure, forecast-aware, or spillback-aware controller
- Network **6**: choose PPO when a trained policy has been loaded
- Network: click a node to choose the trip start; **Shift-click** another node to choose the destination and compare congestion-aware paths
- Network **V**: release one car on the selected route; **M** toggles background traffic
- Network **I** then click a road: create a timed accident closure; **C** clears all accidents
- **Up/Down**: increase or decrease vehicle arrivals
- **Esc**: quit

PEMS `.npz` files contain aggregated sensor measurements, not individual car trajectories; the matching `.csv` files contain directed road edges and costs. Use the `.npz` file with `--data` for Random Forest training and forecasts. These sensor measurements cannot identify individual cars or their exact paths. In the four-intersection network simulator, the trained temporal model predicts aggregate sensor-flow trends and uses the bounded trend as a multiplier on recent simulated arrival forecasts. Without `--data`, forecasts are moving averages of arrivals generated in the simulation. The four-intersection view is still an abstract queue-based demonstration, not a simulation of the full 307-sensor PEMS road network.

## Other commands

```powershell
python tools/generate_sample_data.py
python main.py --train-ml --data data/PEMS04.npz --model random_forest
python main.py --network --animate --data data/PEMS04.npz --model random_forest --controller forecast
python main.py --network --robustness --steps 300 --seeds 3 --data data/PEMS04.npz
python main.py --train-ml --data data/sample_traffic.csv --model random_forest
python main.py --compare --data data/sample_traffic.csv --model random_forest
python main.py --run-fpac --data data/sample_traffic.csv --model random_forest
python main.py --network --steps 300 --controller spillback
python main.py --network --robustness --steps 300 --seeds 3
```

The robustness suite compares fixed-time, longest-queue, forecast-aware, and spillback-aware controllers on matched seeds under nominal, low/peak demand, noisy/missing sensors, a reduced-capacity road incident, and combined stress. It reports average wait, average queue, completed-trip travel time, throughput, and spillback, with across-seed standard deviation and an approximate 95% confidence interval. Detailed per-seed measurements are written to `results/network_robustness.csv`.

## Shared-policy PPO (optional)

Install the reinforcement-learning dependencies:

```powershell
pip install -r requirements-rl.txt
```

Train forecast-enabled PPO and a matched current-state-only ablation:

```powershell
python main.py --network --train-ppo --timesteps 50000
python main.py --network --train-ppo-current-only --timesteps 50000
python main.py --network --controller ppo --steps 300
python main.py --network --controller ppo --current-only --steps 300
python main.py --network --controller ppo --robustness --steps 300 --seeds 3
python main.py --network --controller ppo --current-only --robustness --steps 300 --seeds 3
```

One policy is shared across intersections and emits one phase action per intersection. Minimum green duration and an all-red clearance interval are enforced by the simulator. PPO reward accounts for vehicles served, network queues, and blocked movements. Compare the forecast-enabled and current-state-only models using matched seeds and scenarios; measure results rather than assuming forecasts improve performance.

The CLI defaults to 5,000 PPO steps for a shorter initial run; use a larger `--timesteps` value for research training. Training reports progress periodically. If you press Ctrl+C, the current partial model is saved and the program exits cleanly; evaluate it only as an intermediate checkpoint, not as a converged policy.

The two PPO robustness commands save their per-seed results separately (`network_robustness.csv` and `network_robustness_current_only.csv`) so the ablation outputs are easy to compare.

## Project structure

- `models/`: vehicles, lanes, and intersections
- `simulation/`: single and multi-intersection engines, PPO environment, robustness scenarios, CSV logs, and Pygame viewers
- `algorithms/`: signal control and routing
- `ml/`: traffic-flow data, forecasting, and model training
- `data/`: sample and PEMS traffic datasets
