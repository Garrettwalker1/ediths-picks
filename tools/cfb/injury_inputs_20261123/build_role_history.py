"""Build descriptive, event-scoped role history for injury-input development.
Never changes baseline observations or forecasts and never supplies future shares.
"""
import csv,json,pathlib,gzip,os
from official_lineup_adapter import role_for_attempt
P=pathlib.Path(__file__).parent
B=pathlib.Path(os.environ.get('CFB_CURRENT_ROOT',str(P/'baseline')))
def build():
    evidence=json.load(open(P/'two_team_official_lineup_adapter.json'))
    overrides={(x['team_id'],x['event_id'],x['athlete_id']):x['role'] for x in evidence['role_overrides']}
    roles={}
    for tid in ['249','248']:
        r=json.load(gzip.open(B/f'sources/rosters/{tid}.json.gz','rt'))
        for group in r['athletes']:
            for a in group['items']:roles[tid,str(a['id'])]=a.get('position',{}).get('abbreviation')
    reference=json.load(open(P/'unt_verified_role_lineup_evidence.json'))['baseline_passing']
    stats=list(csv.DictReader(open(B/'current_player_games.csv')))
    histories=[]
    for ref in reference:
        tid={'North Texas Mean Green':'249','Houston Cougars':'248'}[ref['team']]
        rows=[]
        for s in stats:
            if s['team']!=ref['team'] or s['event_id']not in ref['history_event_ids'] or s['date']>=ref['cutoff'] or float(s['pass_att'])<=0:continue
            position=roles.get((tid,s['player_id']))
            role=role_for_attempt(position,tid,s['event_id'],s['player_id'],overrides)
            rows.append(dict(team_id=tid,event_id=s['event_id'],athlete_id=s['player_id'],roster_position=position,event_role=role,channel='quarterback_passing'if role in ['QB','QB_EMERGENCY']else 'non_qb_passing_unresolved',pass_att=float(s['pass_att']),pass_cmp=float(s['pass_cmp']),pass_yds=float(s['pass_yds']),pass_td=float(s['pass_td']),pass_int=float(s['pass_int']),role_source=next((x['source_url'] for x in evidence['role_overrides']if x['team_id']==tid and x['event_id']==s['event_id']and x['athlete_id']==s['player_id']),None)))
        assert sum(x['pass_att']for x in rows)==ref['passing_total']
        histories.append(dict(team=ref['team'],forecast_event_id=ref['forecast_event_id'],baseline_pass_attempts=ref['passing_total'],history_event_ids=ref['history_event_ids'],rows=rows,prospective_allocation=None))
    return dict(status='INCORPORATED_DESCRIPTIVE_INPUT_LAYER',numerical_forecast_effect=False,baseline_values_changed=False,protected_evaluation_changed=False,histories=histories,lineup_artifact='two_team_official_lineup_adapter.json',limitations=['Event roles do not imply future availability or workload','Non-QB passing is not automatically a fixed trick-play share','No missing identity or lineup member is imputed','Original FBS history and denominators are preserved'])
if __name__=='__main__':
    (P/'role_aware_history.json').write_text(json.dumps(build(),indent=2)+'\n')
