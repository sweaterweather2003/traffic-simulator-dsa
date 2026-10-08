<<<<<<< HEAD
from dataclasses import dataclass
@dataclass
class SimulationConfig:
    seed:int=42; steps:int=100; arrivals_per_step:int=6; lane_capacity:int=80
    fixed_green_steps:int=3; min_green_steps:int=2; max_green_steps:int=8
    alpha_queue:float=1.0; beta_forecast:float=.75; gamma_wait:float=.15; delta_emergency:float=20.0
    forecast_scale:float=.08; directions:tuple=("N","E","S","W")
=======
# config.py
DEFAULT_SIMULATION_STEPS = 50
VEHICLE_ARRIVAL_PROBABILITY = 0.35
EMERGENCY_PROBABILITY = 0.05
NORMAL_VEHICLES_PER_STEP = 2
EMERGENCY_VEHICLES_PER_STEP = 1
FIXED_SIGNAL_DURATION = 5
MIN_GREEN_TIME = 3
MAX_GREEN_TIME = 8
RANDOM_SEED = 42
>>>>>>> origin/main
