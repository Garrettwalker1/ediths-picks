from pathlib import Path
import json,sys,numpy as np,pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
REPO=Path(sys.argv[1]);OUT=Path(sys.argv[2]);sys.argv=['wx',str(REPO),str(OUT)]
source=(REPO/'tools/cfb/29-score_week6_initial.py').read_text().split('# ---- Week 6 full slate')[0]
exec(compile(source,'setup','exec'))
# Predeclared single specification: residual margin correction from sustained wind and
# wet conditions interacting with DIFFERENCE in pregame passing-yard share.
# No book inputs, no tuned manual penalties. Dry/calm correction is exactly zero.
wx=pd.concat([pd.read_csv(OUT/f'line-{yr}.csv',low_memory=False)[['game_id','temperature','precipitation','wind_speed']] for yr in range(2020,2026)])
wx['event_id']=wx.game_id.astype(str);gm['event_id']=gm.event_id.astype(str)
s=gm.merge(wx,on='event_id',validate='one_to_one').dropna(subset=FEATS+['margin','wind_speed','precipitation'])
s['passshare_h']=s.h_pyf_r4/(s.h_pyf_r4+s.h_ryf_r4);s['passshare_a']=s.a_pyf_r4/(s.a_pyf_r4+s.a_ryf_r4);s['d_passshare']=s.passshare_h-s.passshare_a
s['wind_pass']=s.wind_speed/10*s.d_passshare;s['wet_pass']=(s.precipitation>=.01).astype(float)*s.d_passshare
s=s.dropna(subset=['wind_pass','wet_pass']);wf=['wind_pass','wet_pass']
trall=hist[hist.season<=2023];b=make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(trall[FEATS],trall.margin)
tr=s[s.season<=2023];va=s[s.season==2024];te=s[s.season==2025]
x=StandardScaler(with_mean=False).fit(tr[wf]);m=Ridge(alpha=10,fit_intercept=False).fit(x.transform(tr[wf]),tr.margin-b.predict(tr[FEATS]))
def metric(q):
 bp=b.predict(q[FEATS]);delta=m.predict(x.transform(q[wf]));cp=bp+delta;y=q.margin.to_numpy();d=abs(y-cp)-abs(y-bp);rng=np.random.default_rng(20261010);boots=np.array([d[rng.integers(len(d),size=len(d))].mean() for _ in range(5000)])
 return {'n':len(q),'baseline_mae':float(abs(y-bp).mean()),'weather_mae':float(abs(y-cp).mean()),'baseline_winners':float((np.sign(y)==np.sign(bp)).mean()),'weather_winners':float((np.sign(y)==np.sign(cp)).mean()),'mae_delta':float(d.mean()),'delta_ci95':np.quantile(boots,[.025,.975]).tolist()}
results={'protocol':'One predeclared residual Ridge alpha10, no intercept,2020-23train,2024validation,2025previously examined historical test. Weather columns only wind*pregame passing-yard-share differential and wet(.01in or more)*same differential. Observed historical kickoff weather, NOT archived pregame forecasts. No book input.','validation':metric(va),'historical_test':metric(te),'coefs_raw':dict(zip(wf,(m.coef_/x.scale_).tolist()))}
print(json.dumps(results,indent=2));json.dump(results,open(OUT/'weather-results.json','w'),indent=2)
s.to_csv(OUT/'weather-historical-rows.csv',index=False)
# Refit residual coefficients on all complete2020-25rows against current v2.2 historical fit.
xl=StandardScaler(with_mean=False).fit(s[wf]);ml=Ridge(alpha=10,fit_intercept=False).fit(xl.transform(s[wf]),s.margin-model.predict(s[FEATS]));co=ml.coef_/xl.scale_
board=json.load(open(REPO/'tools/cfb/29-cfb_board_2026_week6_initial_v2_2.json'));vs=json.load(open(OUT/'window-summary.json'));vmap={v['name']:v for v in vs};pred=[]
for g in board['games']:
 if g.get('book_frozen_pregame') or g['name'] not in vmap:continue
 v=vmap[g['name']];w=json.load(open(OUT/f"wx-{v['id']}.json"))['response']['hourly'];dt=pd.Timestamp(v['kickoff']).tz_localize(None);i=min(range(len(w['time'])),key=lambda i:abs(pd.Timestamp(w['time'][i])-dt));wind=w['wind_speed_10m'][i];rain=w['precipitation'][i]
 hr=feat26.loc[g['home']];ar=feat26.loc[g['away']];share=float(hr.pyf_r4/(hr.pyf_r4+hr.ryf_r4)-ar.pyf_r4/(ar.pyf_r4+ar.ryf_r4));indoors=v['venue']['indoor'];features=np.array([wind/10*share,float(rain>=.01)*share]) if not indoors else np.zeros(2);delta=float(features@co)
 pred.append({'event_id':g['event_id'],'name':g['name'],'baseline_margin_home':g['predicted_margin_home'],'weather_delta_home':delta,'weather_margin_home':g['predicted_margin_home']+delta,'wind_mph_kickoff':wind,'precipitation_in_kickoff':rain,'forecast_hour_utc':w['time'][i],'indoor':indoors,'d_pregame_pass_yards_share':share,'window':{k:v[k] for k in ['rain_chance_max','rain_inches','wind_max','gust_max']},'venue':v['venue'],'location':v['location']})
json.dump({'results':results,'live_raw_coefficients':dict(zip(wf,co.tolist())),'games':pred},open(OUT/'weather-candidate.json','w'),indent=2)
for p in pred:
 if abs(p['weather_delta_home'])>=.25:print(p['name'],p['baseline_margin_home'],round(p['weather_delta_home'],3),round(p['weather_margin_home']*2)/2)
