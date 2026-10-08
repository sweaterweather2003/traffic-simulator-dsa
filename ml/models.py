import numpy as np
from sklearn.ensemble import RandomForestRegressor
class HistoricalAverage:
    def fit(self,X,y):self.v=float(np.mean(y));return self
    def predict(self,X):return np.full(len(X),self.v)
    def predict_online(self,x):return self.v
class RandomForest:
    def __init__(self):self.m=RandomForestRegressor(n_estimators=200,max_depth=18,min_samples_leaf=2,n_jobs=-1,random_state=42)
    def fit(self,X,y):self.m.fit(X,y);return self
    def predict(self,X):return self.m.predict(X)
    def predict_online(self,x):return float(self.m.predict(np.asarray(x).reshape(1,-1))[0])
class XGBoost:
    def __init__(self):
        from xgboost import XGBRegressor
        self.m=XGBRegressor(n_estimators=300,max_depth=6,learning_rate=.05,subsample=.85,colsample_bytree=.85,objective="reg:squarederror",random_state=42)
    def fit(self,X,y):self.m.fit(X,y);return self
    def predict(self,X):return self.m.predict(X)
    def predict_online(self,x):return float(self.m.predict(np.asarray(x).reshape(1,-1))[0])
def make_model(name,lookback=12):
    if name=="historical_average":return HistoricalAverage()
    if name=="random_forest":return RandomForest()
    if name=="xgboost":return XGBoost()
    if name in ("lstm","gru"):
        raise ImportError("LSTM/GRU are included as research extensions; install tensorflow and add a Keras sequence model before running them.")
    raise ValueError(name)
