"""CBB v0 fixed-rule predictor. No fitting, network, wagering or accuracy claims.
Consumes normalized, evidence-checked games and targets; the raw artifact adapter
must independently verify hashes, row/team binding and final/completeness flags.
This module does not turn caller assertions into authenticated source evidence.
"""
from datetime import datetime, timezone
from math import isfinite

VERSION = 'cbb-form-v0-fixed-shrink5'
PRIOR_EQUIVALENTS = 5.0

def time(s):
    t=datetime.fromisoformat(s.replace('Z','+00:00'))
    if t.tzinfo is None: raise ValueError('timezone required')
    return t.astimezone(timezone.utc)

def number(x):
    return not isinstance(x,bool) and isinstance(x,(int,float)) and isfinite(x) and x>=0

def eligible(g,target,issuance):
    try:
        # Only current prospective evidence, never protected historical postseason.
        if g['season']!=2027 or g['season_type']!=2: return False
        if g['event_id']==target['event_id']: return False
        if not all(g[k] is True for k in ('integrity_verified','identity_verified','complete','final')): return False
        if g['home_id']==g['away_id'] or not g['home_id'] or not g['away_id']: return False
        if not all(number(g[k]) for k in ('home_points','away_points')): return False
        if g['home_points']==g['away_points']: return False
        t=time(issuance); c=time(target['cutoff_estimate'])
        return (time(g['received_at'])<t and time(g['preserved_at'])<t
                and time(g['received_at'])<c and time(g['preserved_at'])<c
                and time(g['game_start_observed'])<min(t,c))
    except (KeyError,ValueError,TypeError,AttributeError): return False

def predict(games,target,issuance):
    base={'model_version':VERSION,'issuance':issuance,'target_event_id':target.get('event_id'),
          'clock_status':'unsigned observed clocks; cutoff estimate is not actual-start proof',
          'home_points':None,'away_points':None,'margin_home_minus_away':None,'total_points':None,
          'status':'withheld','reason':None,'prior_games':{},'pooled_team_points':None,'input_event_ids':[]}
    try:
        if target['season']!=2027 or target['season_type']!=2: raise ValueError('target outside prospective season')
        if not all(target[k] is True for k in ('integrity_verified','identity_verified')): raise ValueError('target evidence unresolved')
        if target.get('schedule_conflict') is not False: raise ValueError('schedule conflict or unknown status')
        if target['observed_state']!='pre': raise ValueError('target not observed pregame')
        if target['home_id']==target['away_id'] or not target['home_id'] or not target['away_id']: raise ValueError('invalid target teams')
        if not (time(target['snapshot_received_at'])<time(issuance)<time(target['cutoff_estimate'])
                and time(target['snapshot_preserved_at'])<time(issuance)): raise ValueError('target timing boundary')
    except (KeyError,ValueError,TypeError,AttributeError) as e:
        base['reason']='target_ineligible: '+str(e);return base
    candidates=[g for g in games if eligible(g,target,issuance)]
    # Freeze earliest complete available version. Later corrected scores cannot replace it.
    candidates.sort(key=lambda g:(time(g['received_at']),time(g['preserved_at']),g['event_id']))
    frozen={}
    for g in candidates:
        old=frozen.get(g['event_id'])
        if old and (old['home_id'],old['away_id'])!=(g['home_id'],g['away_id']):
            base['reason']='conflicting prior-game identity';return base
        frozen.setdefault(g['event_id'],g)
    pool=list(frozen.values());base['input_event_ids']=sorted(frozen)
    if not pool:base['reason']='no_verified_prior_games';return base
    mu=sum(g['home_points']+g['away_points'] for g in pool)/(2*len(pool));base['pooled_team_points']=mu
    form={}
    for team in (target['home_id'],target['away_id']):
        records=[]
        for g in pool:
            if g['home_id']==team:records.append((g['home_points'],g['away_points'],g['event_id']))
            elif g['away_id']==team:records.append((g['away_points'],g['home_points'],g['event_id']))
        n=len(records);base['prior_games'][team]={'count':n,'events':sorted(r[2] for r in records)}
        if n:form[team]=((sum(r[0] for r in records)+PRIOR_EQUIVALENTS*mu)/(n+PRIOR_EQUIVALENTS),
                         (sum(r[1] for r in records)+PRIOR_EQUIVALENTS*mu)/(n+PRIOR_EQUIVALENTS))
    if len(form)!=2:base['reason']='missing_prior_form_for_one_or_both_teams';return base
    h,a=target['home_id'],target['away_id'];hp=(form[h][0]+form[a][1])/2;ap=(form[a][0]+form[h][1])/2
    base.update(home_points=hp,away_points=ap,margin_home_minus_away=hp-ap,total_points=hp+ap,
                status='prediction_computed_not_issued',reason=None)
    return base
