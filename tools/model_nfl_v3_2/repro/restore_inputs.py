#!/usr/bin/env python3
"""Fetch public historical input files and verify this reproduction's hashes.

This only restores raw nflverse sources to scratch. It never changes the public
board or deploys the diagnostic. Requires pandas, pyarrow and network access.
"""
import argparse,hashlib,json,os,tempfile,urllib.request
from pathlib import Path
import pandas as pd
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
MANIFEST=json.loads((HERE/'source_manifest.json').read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def check(p,record):
 actual=sha(p)
 if actual!=record['sha256']:raise RuntimeError(f'checksum mismatch {p}: expected {record["sha256"]}; got {actual}')
def restore(dest):
 dest.mkdir(parents=True,exist_ok=True)
 for f in MANIFEST['source_files']:
  local=REPO/f['file'] if f['file'].startswith('tools/') else dest/f['file']
  if local.exists():check(local,f);print(f'verified {local}',flush=True);continue
  if f['file'].startswith('tools/'):raise FileNotFoundError(f'Repository snap-count input missing: {local}')
  source=f['source_url'];fd,tmp=tempfile.mkstemp(dir=dest,prefix='.download-');os.close(fd);tmp=Path(tmp)
  try:
   with urllib.request.urlopen(source,timeout=60) as src,tmp.open('wb') as dst:
    while chunk:=src.read(1<<20):dst.write(chunk)
   if f['file'].startswith('inj_'):
    # The manifest hashes local parquet conversion, not upstream CSV bytes.
    frame=pd.read_csv(tmp);frame.to_parquet(local,index=False)
    check(local,f)
   else:
    check(tmp,f);tmp.replace(local)
   print(f'restored {local}',flush=True)
  finally:tmp.unlink(missing_ok=True)
 # Legacy builders expect this alias for the repository's snap-count files.
 alias=Path('/tmp/ediths-picks')
 if not alias.exists():alias.symlink_to(REPO,target_is_directory=True)
 elif alias.resolve()!=REPO.resolve():raise RuntimeError(f'{alias} points elsewhere: {alias.resolve()}')
 print('All source hashes verified. Builders still contain chronology leaks; see README.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--scratch',type=Path,default=Path('/tmp/training/nflv32'));a=p.parse_args();restore(a.scratch)
