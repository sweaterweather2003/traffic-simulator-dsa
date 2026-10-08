import random
from models.vehicle import Vehicle
from models.intersection import Intersection
from algorithms.signal_controller import AdaptiveSignalOptimizer
from simulation.statistics import SimulationResult
class TrafficSimulator:
    def __init__(self,cfg,forecaster=None):self.cfg=cfg;self.forecaster=forecaster;self.opt=AdaptiveSignalOptimizer(cfg);self.r=random.Random(cfg.seed)
    def forecast(self,x):
        if self.forecaster is not None:
            try:return self.forecaster.predict_online([x.total_queue("NS"),x.total_queue("EW")])
            except Exception:pass
        return {"NS":x.total_queue("NS")*1.1+self.cfg.arrivals_per_step*.5,"EW":x.total_queue("EW")*1.1+self.cfg.arrivals_per_step*.5}
    def run(self,controller_name="fpac"):
        x=Intersection(capacity=self.cfg.lane_capacity);phase="NS";remaining=self.cfg.fixed_green_steps;total_wait=em_wait=maxq=throughput=stops=0;vid=0
        for step in range(self.cfg.steps):
            for _ in range(self.cfg.arrivals_per_step):
                d=self.r.choice(self.cfg.directions);x.lanes[d].enqueue(Vehicle(vid,d,self.r.random()<.04,step));vid+=1
            fc=self.forecast(x)
            if remaining<=0:
                if controller_name=="fixed":phase=self.opt.opposite(phase);remaining=self.cfg.fixed_green_steps
                elif controller_name=="longest_queue":phase=self.opt.choose_longest_queue(x);remaining=self.opt.green_time(x,phase,{})
                elif controller_name=="max_pressure":phase=self.opt.choose_max_pressure(x);remaining=self.opt.green_time(x,phase,{})
                elif controller_name=="fpac":
                    if isinstance(fc,(int,float)):fc={"NS":fc/2,"EW":fc/2}
                    phase=self.opt.choose_fpac(x,fc);remaining=self.opt.green_time(x,phase,fc)
                else:raise ValueError(controller_name)
            for d in self.opt.dirs(phase):
                done=x.lanes[d].dequeue(1);throughput+=len(done)
            q=sum(len(x.lanes[d]) for d in self.cfg.directions);maxq=max(maxq,q);stops+=q
            for d in self.cfg.directions:
                for v in x.lanes[d].queue:v.wait_time+=1;total_wait+=1;em_wait+=int(v.emergency)
            remaining-=1
        return SimulationResult(controller_name,total_wait/max(1,throughput+sum(len(x.lanes[d]) for d in self.cfg.directions)),maxq,throughput,stops,em_wait/max(1,vid))
