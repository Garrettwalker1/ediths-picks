"""Week-10 established skill shares - provenance script (matches the fitted definition exactly).
Fitted definition (strict_absence_build.py): established at game G = >=2 prior appearances AND
>=2% of team trailing volume (attempts+carries+receptions), computed strictly from games BEFORE G.
For Week-10 application, G = each upcoming Nov 15-16 game, so the trailing state uses every
completed 2026 REG game through Nov 12 (incl. WAS@NYG TNF). Appearances = any player-game row
(2026 file records zero-touch active rows, same handling as the fit). Identity = nflverse
player_id (gsis). Full precision: no rounding anywhere in the output.
"""
import pandas as pd

D = pd.read_csv('/tmp/inj/nfl/player_stats_2026.csv', low_memory=False)
D = D[D.season_type == 'REG'].copy()
for c in ['attempts', 'carries', 'receptions']:
    D[c] = pd.to_numeric(D[c], errors='coerce').fillna(0)
D['vol'] = D[['attempts', 'carries', 'receptions']].sum(axis=1)
max_completed_week = 10  # week-10 TNF (Nov 12) is complete; only WAS/NYG have a week-10 row
D = D[(D.week < 10) | (D.team.isin(['WAS', 'NYG']))]

rows = []
for tm, d in D.groupby('team'):
    hv = d.groupby('player_id').vol.sum()
    ha = d.groupby('player_id').size()
    tot = hv.sum()
    meta = d.groupby('player_id').agg(pos=('position', 'last'), name=('player_display_name', 'last'))
    for pid in hv.index:
        if ha[pid] >= 2 and tot > 0 and hv[pid] / tot >= 0.02 and meta.pos.get(pid) in ('RB', 'WR', 'TE'):
            rows.append(dict(team=tm, pid=pid, name=meta['name'].get(pid), pos=meta.pos.get(pid),
                             apps=int(ha[pid]), vol=float(hv[pid]), team_vol=float(tot),
                             share=float(hv[pid] / tot)))
E = pd.DataFrame(rows).sort_values(['team', 'share'], ascending=[True, False])
E.to_csv('/tmp/inj/overlay/wk10_established_skill_shares.csv', index=False)
print('established skill players:', len(E))
print(E[E.name.isin(['TreVeyon Henderson', 'T.J. Hockenson', 'Carnell Tate', 'CJ Donaldson',
                     'Josh Jacobs', 'Jake Ferguson', 'Tyler Goodson'])].to_string(index=False))
