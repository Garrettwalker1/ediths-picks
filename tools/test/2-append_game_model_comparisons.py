#!/usr/bin/env python3
"""Create one immutable model-vs-book comparison part from a FanDuel capture.
Input is the frozen model catalog JSON and capture JSON (`rows`) or CSV.
Never overwrites an existing output. One output row per capture quote.
"""
import argparse,csv,json,os,sys,uuid
p=argparse.ArgumentParser();p.add_argument('--catalog',required=True);p.add_argument('--capture',required=True);p.add_argument('--output',required=True);p.add_argument('--current-json');a=p.parse_args()
if os.path.exists(a.output): raise SystemExit('refusing to replace existing immutable part: '+a.output)
cat=json.load(open(a.catalog)); idx={(str(r['event_id']),r['market_type'],str(r['selection_id'])):r for r in cat['rows']}
if a.capture.lower().endswith('.csv'): quotes=list(csv.DictReader(open(a.capture,newline='')))
else: quotes=json.load(open(a.capture));quotes=quotes['rows'] if isinstance(quotes,dict) else quotes
# Normalize paired moneyline probabilities within each event/capture before joining.
def implied(price): return 100/(price+100) if price>0 else -price/(-price+100)
mlsum={}
for q in quotes:
 if q.get('market_type')=='moneyline' and q.get('american_price') not in ('',None):
  g=(str(q.get('event_id')),q.get('observed_at',q.get('captured_at')));mlsum[g]=mlsum.get(g,0)+implied(int(float(q['american_price'])))
out=[];missing=[]
for q in quotes:
 k=(str(q['event_id']),q['market_type'],str(q['selection_id']));m=idx.get(k)
 if not m: missing.append(k);continue
 line=q.get('handicap',q.get('line')); line=None if line in ('',None) else float(line)
 price=q.get('american_price');price=None if price in ('',None) else int(float(price))
 r={'comparison_id':str(uuid.uuid5(uuid.NAMESPACE_URL,'|'.join(map(str,[q.get('observed_at',q.get('captured_at')),q.get('event_id'),q.get('market_id'),q.get('selection_id'),line,price])))),'observed_at':q.get('observed_at',q.get('captured_at')),'event_id':str(q['event_id']),'event_name':q.get('event_name'),'kickoff':q.get('kickoff'),'book':q.get('book','FanDuel'),'state':q.get('state','VA'),'price_scope':q.get('price_scope',m['price_scope']),'market_type':q['market_type'],'captured_market_id':str(q.get('market_id','')),'market_id_at_freeze':m['market_id_at_freeze'],'selection_id':str(q['selection_id']),'selection':q.get('selection'),'book_line':line,'american_price':price,'model_metric':m['model_metric'],'model_value':m['model_value'],'model_value_unit':m['model_value_unit'],'model_version':m['model_version'],'model_generated_at':m['model_generated_at'],'post_line_generated':m['post_line_generated'],'eligible_for_preregistered_week1_grade':m['eligible_for_preregistered_week1_grade']}
 r['model_minus_book']=round(float(m['model_value'])-line,6) if m['model_metric']=='line' and line is not None else None
 if m['model_metric']=='win_probability':
  if price is not None:
   r['book_raw_implied_probability']=round(implied(price),6)
   den=mlsum.get((str(q.get('event_id')),q.get('observed_at',q.get('captured_at'))))
   r['book_devig_probability']=round(implied(price)/den,6) if den else None
  r['model_minus_book_devig_probability']=round(float(m['model_value'])-r['book_devig_probability'],6) if price is not None and r.get('book_devig_probability') is not None else None
 out.append(r)
if missing: raise SystemExit(f'catalog miss for {len(missing)} rows; preserving prior good parts. sample={missing[:5]}')
if len(out)!=len(quotes):raise SystemExit('row count mismatch; preserving prior good parts')
fields=list(out[0])
with open(a.output,'x',newline='') as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(out)
if a.current_json:
 tmp=a.current_json+'.tmp';json.dump({'schema_version':'1.0.0','observed_at':out[0]['observed_at'] if out else None,'rows':out},open(tmp,'w'),indent=2);os.replace(tmp,a.current_json)
print(json.dumps({'output':a.output,'current_json':a.current_json,'rows':len(out),'catalog_misses':0,'unique_comparison_ids':len({r['comparison_id'] for r in out})}))
