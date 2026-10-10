from pathlib import Path


MODEL_PATH = Path("models_saved") / "network_shared_ppo"
CURRENT_ONLY_MODEL_PATH = Path("models_saved") / "network_shared_ppo_current_only"


def _rl_dependencies():
    try:
        import gymnasium as gym
        import numpy as np
        from gymnasium import spaces
        from stable_baselines3 import PPO
    except ImportError as exc:
        raise ImportError(
            "PPO support is optional. Install it with "
            "`pip install -r requirements-rl.txt` and retry."
        ) from exc
    return gym, np, spaces, PPO


def create_environment(config):
    gym, np, spaces, _ = _rl_dependencies()
    from simulation.network_simulator import NetworkTrafficSimulator

    class NetworkSignalEnv(gym.Env):
        metadata = {"render_modes": []}

        def __init__(self):
            super().__init__()
            self.simulator = NetworkTrafficSimulator(config)
            self.action_space = spaces.MultiDiscrete([2] * len(config.nodes))
            self.observation_space = spaces.Box(
                low=0.0,
                high=1.0,
                shape=(len(config.nodes) * 19,),
                dtype=np.float32,
            )

        def reset(self, seed=None, options=None):
            super().reset(seed=seed)
            if seed is not None:
                self.simulator.cfg.seed = seed
            observation = self.simulator.reset()
            return np.asarray(observation, dtype=np.float32), {}

        def step(self, action):
            previous_served = self.simulator.throughput
            previous_blocked = self.simulator.spillback_blocked
            observation, _ = self.simulator.step("ppo", actions=action)
            served = self.simulator.throughput - previous_served
            blocked = self.simulator.spillback_blocked - previous_blocked
            queue = sum(len(lane) for lane in self.simulator.queues.values())
            reward = float(served - 0.03 * queue - 0.25 * blocked)
            terminated = self.simulator.tick >= config.steps
            info = {
                "vehicles_served": self.simulator.throughput,
                "queue": queue,
                "spillback_blocked": self.simulator.spillback_blocked,
            }
            return (
                np.asarray(observation, dtype=np.float32),
                reward,
                terminated,
                False,
                info,
            )

    return NetworkSignalEnv()


def train_ppo(config, total_timesteps=50_000, model_path=MODEL_PATH):
    if total_timesteps < 1:
        raise ValueError("total_timesteps must be at least 1.")
    _, _, _, PPO = _rl_dependencies()
    env = create_environment(config)
    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=3e-4,
        n_steps=128,
        batch_size=64,
        gamma=0.99,
        gae_lambda=0.95,
        ent_coef=0.01,
        policy_kwargs={"net_arch": {"pi": [64, 64], "vf": [64, 64]}},
        seed=config.seed,
        verbose=1,
    )
    try:
        model.learn(total_timesteps=total_timesteps)
    except KeyboardInterrupt:
        model.save(str(model_path))
        raise
    finally:
        env.close()
    model.save(str(model_path))
    return model_path


def load_ppo(model_path=MODEL_PATH):
    _, _, _, PPO = _rl_dependencies()
    model_path = Path(model_path)
    if not model_path.with_suffix(".zip").exists() and not model_path.exists():
        raise FileNotFoundError(
            f"No trained PPO model at {model_path}. "
            "Train one first with `python main.py --network --train-ppo`."
        )
    return PPO.load(str(model_path))
