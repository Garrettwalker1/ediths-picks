"""Official free team gamebook lineup harvest. Historical observed starts, not pregame availability.
Source-local athlete roster URLs preserved, no guessed ESPN ID mapping.
"""
import requests,bs4,pathlib,json,time,hashlib,datetime,urllib.parse
O=pathlib.Path(__file__).parent;P=O/'houston-official-lineups';P.mkdir(exist_ok=True)
def main():
 source='https://uhcougars.com/sports/football/schedule/2026';raw=(O/'houston-schedule-2026.html').read_text();s=bs4.BeautifulSoup(raw,'html.parser');links=sorted({urllib.parse.urljoin(source,a['href'])for a in s.find_all('a',href=True)if '/stats/2026/'in a['href']and'/boxscore/'in a['href']});manifest=[];rows=[]
 for u in links:
  bid=u.rstrip('/').split('/')[-1];p=P/(bid+'.html')
  if not p.exists():
   if bid=='16252':p.write_bytes((O/'houston-wvu-official-box.html').read_bytes())
   else:
    r=requests.get(u,timeout=25);r.raise_for_status();p.write_bytes(r.content);time.sleep(.5)
  data=p.read_bytes();s=bs4.BeautifulSoup(data,'html.parser');date=s.get_text(' ',strip=True);tables=[]
  for t in s.find_all('table'):
   label=t.get('aria-label','')
   if not __import__('re').sub(r'^#\d+\s+','',label).startswith('Houston ')or not any(k in label for k in ['Starters','Player Participation']):continue
   entries=[]
   for tr in t.select('tbody tr'):
    cells=[x.get_text(' ',strip=True)for x in tr.find_all('td')]
    if not cells:continue
    a=tr.find('a',href=True);entry=dict(jersey=cells[0],name=cells[1],position=cells[2]if len(cells)>2 else None,athlete_source_url=urllib.parse.urljoin(u,a['href'])if a else None);entries.append(entry);rows.append(dict(source_url=u,boxscore_id=bid,table=label,**entry))
   tables.append(dict(label=label,entries=len(entries)))
  manifest.append(dict(boxscore_id=bid,url=u,path=str(p),sha256=hashlib.sha256(data).hexdigest(),observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),title=s.title.get_text(' ',strip=True),date_candidates=__import__('re').findall(r'\b\d{1,2}/\d{1,2}/2026\b',date)[:5],tables=tables))
 out=dict(source_schedule=source,games=len(links),lineup_rows=len(rows),manifest=manifest,rows=rows,limitations=['Official postgame observed starts and participation, not snap counts, injury cause, clearance or pregame publication proof','Team-local roster URL is stable local identity; no guessed ESPN join','Participation list may separate starters from reserves; do not infer absent from one table','Season includes FCS game; caller must preserve exact model FBS history scope']);(O/'houston_official_lineup_harvest.json').write_text(json.dumps(out,indent=2));print('games',len(links),'rows',len(rows));print([(r['boxscore_id'],r['date_candidates'],r['tables'])for r in manifest])
if __name__=='__main__':main()
