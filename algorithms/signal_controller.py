from data_structures.max_heap import MaxHeap
class AdaptiveSignalOptimizer:
    def __init__(self,cfg):self.cfg=cfg
    @staticmethod
    def dirs(p):return ("N","S") if p=="NS" else ("E","W")
    @staticmethod
    def opposite(p):return "EW" if p=="NS" else "NS"
    def choose_longest_queue(self,x):return "NS" if x.total_queue("NS")>=x.total_queue("EW") else "EW"
    def choose_max_pressure(self,x):return self.choose_longest_queue(x)
    def fpac_scores(self,x,forecast):
        s={}
        for p in ("NS","EW"):
            wait=sum(v.wait_time for d in self.dirs(p) for v in x.lanes[d].queue)
            s[p]=(self.cfg.alpha_queue*x.total_queue(p)+self.cfg.beta_forecast*forecast.get(p,0)+self.cfg.gamma_wait*wait+self.cfg.delta_emergency*x.total_emergency(p))
        return s
    def choose_fpac(self,x,forecast):
        h=MaxHeap()
        for p,v in self.fpac_scores(x,forecast).items():h.push(v,p)
        return h.pop()
    def green_time(self,x,p,forecast):
        extra=int(forecast.get(p,0)*self.cfg.forecast_scale);g=self.cfg.min_green_steps+x.total_queue(p)//4+extra
        return max(self.cfg.min_green_steps,min(self.cfg.max_green_steps,g))
