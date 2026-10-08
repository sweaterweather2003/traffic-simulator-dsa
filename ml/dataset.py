from pathlib import Path
import numpy as np,pandas as pd
def load_flow_csv(path):
    p=Path(path)
    if not p.exists():raise FileNotFoundError(p)
    df=pd.read_csv(p);num=df.select_dtypes(include=[np.number]).replace([np.inf,-np.inf],np.nan).interpolate().ffill().bfill()
    if num.empty:raise ValueError("No numeric traffic columns found")
    return num
def aggregate_flow(df):return df.mean(axis=1).astype(float).values
def make_supervised(series,lookback=12,horizon=1):
    X=[];y=[]
    for i in range(lookback,len(series)-horizon+1):X.append(series[i-lookback:i]);y.append(series[i+horizon-1])
    return np.asarray(X),np.asarray(y)
