from pathlib import Path
import joblib,numpy as np
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score
from ml.dataset import load_flow_csv,aggregate_flow,make_supervised
from ml.models import make_model
MODEL_DIR=Path("models_saved");MODEL_DIR.mkdir(exist_ok=True)
def train(path,model_name="random_forest",lookback=12,horizon=1):
    s=aggregate_flow(load_flow_csv(path));X,y=make_supervised(s,lookback,horizon);n=len(X);a=int(.7*n);b=int(.85*n);model=make_model(model_name,lookback);model.fit(X[:a],y[:a]);pred=model.predict(X[b:]);m={"MAE":float(mean_absolute_error(y[b:],pred)),"RMSE":float(np.sqrt(mean_squared_error(y[b:],pred))),"R2":float(r2_score(y[b:],pred))};p=MODEL_DIR/f"{model_name}_h{horizon}_lb{lookback}.joblib";joblib.dump(model,p);return model,m,p
def load_or_train(path,model_name="random_forest",lookback=12,horizon=1):
    p=MODEL_DIR/f"{model_name}_h{horizon}_lb{lookback}.joblib"
    if p.exists():return joblib.load(p)
    return train(path,model_name,lookback,horizon)[0]
