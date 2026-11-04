"""Frozen inference only. No training, tuning, or serialized temporary models."""
import json,hashlib
from pathlib import Path
import numpy as np
PARAMETERS=Path(__file__).resolve().parents[1]/'player_projection_refresh_20261103/fixed_fit_parameters.json'
class FixedModel:
    def __init__(self, p): self.p=p
    def predict(self, X):
        return np.asarray(X,dtype=float) @ np.asarray(self.p['coef']) + self.p['intercept']
    def predict_proba(self, X):
        p=self.p
        z=((np.asarray(X,dtype=float)-p['mean'])/p['scale']) @ np.asarray(p['coef'])[0] + p['intercept'][0]
        q=1/(1+np.exp(-z))
        return np.column_stack([1-q,q])
def load_models():
    blob=PARAMETERS.read_bytes()
    if hashlib.sha256(blob).hexdigest()!='0754d43d0edd7fa9a6827e10d8dacfa4f67ba1f0a534eb18848aba95c625f266':raise ValueError('Fixed fitted parameter fingerprint changed; stop for model review')
    return {k:FixedModel(v) for k,v in json.loads(blob).items()}
