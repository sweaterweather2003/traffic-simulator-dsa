from pathlib import Path
import numpy as np,pandas as pd
def load_flow_csv(path):
    p=Path(path)
    if not p.exists():raise FileNotFoundError(p)
    if p.suffix.lower()==".npz":
        with np.load(p) as archive:
            if "data" not in archive:
                raise ValueError(f"No 'data' tensor found in traffic archive: {p}")
            values=archive["data"]
        if values.ndim!=3 or values.shape[2]<1:
            raise ValueError(f"Expected time x sensor x feature traffic data in {p}")
        return pd.DataFrame(values[:,:,0],columns=[f"sensor_{i}" for i in range(values.shape[1])])

    df=pd.read_csv(p)
    if {"from","to","cost"}.issubset(df.columns):
        raise ValueError(
            f"{p} is a road-edge list, not traffic history. Use the matching PEMS .npz file for ML data."
        )
    num=df.select_dtypes(include=[np.number]).replace([np.inf,-np.inf],np.nan).interpolate().ffill().bfill()
    if num.empty:raise ValueError("No numeric traffic columns found")
    return num
def aggregate_flow(df):return df.mean(axis=1).astype(float).values
def make_supervised(series,lookback=12,horizon=1):
    X=[];y=[]
    for i in range(lookback,len(series)-horizon+1):X.append(series[i-lookback:i]);y.append(series[i+horizon-1])
    return np.asarray(X),np.asarray(y)
