from pathlib import Path
import numpy as np,pandas as pd
rng=np.random.default_rng(42);n=2000;t=np.arange(n);base=80+25*np.sin(t/40)+15*np.sin(t/11)
df=pd.DataFrame({f"sensor_{i:03d}":np.maximum(0,base*(.8+i*.08)+rng.normal(0,8,n)) for i in range(1,5)})
Path("data").mkdir(exist_ok=True);df.to_csv("data/sample_traffic.csv",index=False);print("created data/sample_traffic.csv")
