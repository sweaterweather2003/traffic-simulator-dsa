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
