#!/usr/bin/env python3
import csv,json,sys,pathlib
m=pathlib.Path(sys.argv[1]); cfg=json.load(open(m)); root=m.parent
files=[]
base=cfg.get('frozen_base')
if base: files.append((root/base).resolve())
files += [(root/p).resolve() for p in cfg.get('parts',[])]
seen=set(); writer=None
for p in files:
 with open(p,newline='') as f:
  r=csv.DictReader(f)
  if writer is None:
   writer=csv.DictWriter(sys.stdout,fieldnames=r.fieldnames); writer.writeheader()
  elif r.fieldnames!=writer.fieldnames: raise SystemExit(f'schema mismatch: {p}')
  for row in r:
   key=row.get('quote_id') or tuple(row.items())
   if key in seen: continue
   seen.add(key);writer.writerow(row)
