#!/usr/bin/env python3
"""Fetch public Gdansk BIP data into a normalized static JSON file."""
import json, re, urllib.request, html, urllib.parse, time
from datetime import datetime, timezone
from pathlib import Path
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'public'/'data'/'latest.json'
PARCEL_CACHE=ROOT/'public'/'data'/'parcel_cache.json'
ULDK_BASE='https://uldk.gugik.gov.pl/'
GDANSK_TERYT='226101_1'
HEADERS={'User-Agent':'GdanskRadar/0.2 (public-source monitor; contact: racibo.pl)'}
SOURCES=[
 ('interpelacje','Interpelacje','https://bip.gdansk.pl/rada-miasta/publikacja-interpelacji-radnych-miasta-gdanska','council'),
 ('zapytania','Zapytania radnych','https://bip.gdansk.pl/rada-miasta/publikacja-zapytan-radnych-miasta-gdanska','council'),
 ('petycje','Petycje','https://bip.gdansk.pl/urzad-miejski/publikacja-petycji-do-rady-miasta-gdanska','council'),
 ('decyzje','Decyzje WUIA','https://files.cloudgdansk.pl/d/otwarte-dane/bip-umg/publikacja-decyzji-wuia.json','json','https://bip.gdansk.pl/urzad-miejski/raporty-i-publikacje/publikacja-decyzji-wuia'),
 ('zgloszenia','Zgłoszenia budowlane','https://files.cloudgdansk.pl/d/otwarte-dane/bip-umg/publikacja-zgloszen-wuia.json','json','https://bip.gdansk.pl/urzad-miejski/raporty-i-publikacje/publikacja-zgloszen-wuia'),
]
LABELS={s[0]:s[1] for s in SOURCES}
def request(url,headers=None):
 req=urllib.request.Request(url,headers={**HEADERS,**(headers or {})})
 with urllib.request.urlopen(req,timeout=60) as resp:return resp.read().decode('utf-8','replace')
def normdate(value):
 if not value:return ''
 value=str(value).strip()
 for fmt in ('%Y-%m-%d','%d.%m.%Y','%Y/%m/%d'):
  try:return datetime.strptime(value,fmt).date().isoformat()
  except ValueError:pass
 return value
def makeitem(source,title,date='',url='',description='',author='',address='',parcel='',investor='',status='',response='',summary='',response_date='',response_url='',lat='',lon='',parcel_id=''):
 ident='-'.join(filter(None,[source,re.sub(r'[^a-zA-Z0-9]+','-',str(title)+str(date)+str(address))[:90].strip('-')]))
 return {'id':ident,'type':source,'category':LABELS.get(source,source),'title':title,'date':normdate(date),'url':url,'description':description,'summary':summary,'author':author,'address':address,'parcel':parcel,'investor':investor,'status':status,'response':response,'responseDate':normdate(response_date),'responseUrl':response_url,'lat':lat,'lon':lon,'parcelId':parcel_id}
def first_value(row,*keys):
 for key in keys:
  value=row.get(key)
  if value is not None and str(value).strip():return str(value).strip()
 return ''
def parse_json_source(key,label,feed_url,public_url):
 data=json.loads(request(feed_url))
 rows=data.get('results',data.get('data',data if isinstance(data,list) else []))
 if isinstance(rows,dict):rows=rows.get('results',rows.get('items',[]))
 if not isinstance(rows,list):raise RuntimeError('Unexpected JSON records structure')
 items=[]
 for r in rows:
  if not isinstance(r,dict):continue
  address=first_value(r,'adres_inwestycji','adres','adres_inwestora','ulica','lokalizacja')
  parcel=first_value(r,'obreb_dzialka','obręb_działka','obreb i dzialka','dzialka','działka','nr_dzialki','numer_dzialki')
  if key=='decyzje':
   title=first_value(r,'rodzaj_inwestycji','nazwa_inwestycji','przedmiot','rodzaj decyzji') or 'Decyzja administracyjna'
   raw_status=' · '.join(filter(None,[first_value(r,k) for k in ('typ_decyzji','rodzaj_decyzji','wynik','status','rozstrzygniecie','rozstrzygnięcie')]))
   detail=' · '.join(filter(None,[raw_status,('nr '+first_value(r,'nr_decyzji','numer_decyzji')) if first_value(r,'nr_decyzji','numer_decyzji') else '']))
   date=first_value(r,'data_decyzji','data')
   items.append(makeitem(key,title,date,first_value(r,'url','link') or public_url,detail,address=address,parcel=parcel,status=raw_status,summary=title))
  else:
   title=first_value(r,'rodzaj_inwestycji','nazwa_inwestycji','przedmiot') or 'Zgłoszenie budowlane'
   raw_status=' · '.join(filter(None,[first_value(r,k) for k in ('status','sprzeciw','wynik')]))
   detail=' · '.join(filter(None,['Numer zgłoszenia: '+first_value(r,'numer_wniosku','nr_wniosku'),raw_status]))
   date=first_value(r,'data_wplywu','data_zgloszenia','data')
   items.append(makeitem(key,title,date,first_value(r,'url','link') or public_url,detail,address=address,parcel=parcel,investor=first_value(r,'inwestor'),status=raw_status,summary=title))
 return items,{'source':label,'ok':bool(items),'count':len(items),'updated':data.get('description',{}).get('generationDate') if isinstance(data,dict) else None,'url':public_url,'dataUrl':feed_url}
def load_parcel_cache():
 try:return json.loads(PARCEL_CACHE.read_text(encoding='utf-8'))
 except Exception:return {}
def parcel_identifier(value):
 match=re.search(r'(?<!\d)(\d{4})\s*[. ]\s*(\d+(?:/\d+)?)(?!\d)',str(value or ''))
 return (match.group(1),match.group(2)) if match else None
def resolve_parcel(value):
 parsed=parcel_identifier(value)
 if not parsed:return None
 region,number=parsed
 identifier=GDANSK_TERYT+'.'+region+'.'+number
 params=urllib.parse.urlencode({'request':'GetParcelByIdOrNr','id':identifier,'result':'geom_wkt,teryt,parcel,region,commune','srid':'4326'})
 raw=request(ULDK_BASE+'?'+params)
 lines=raw.strip().splitlines()
 if not lines or lines[0].strip()!='0':return None
 wkt=' '.join(lines[1:])
 pairs=re.findall(r'(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)',wkt)
 if not pairs:return None
 coords=[(float(a),float(b)) for a,b in pairs]
 lon=sum(p[0] for p in coords)/len(coords);lat=sum(p[1] for p in coords)/len(coords)
 return {'parcelId':identifier,'lat':round(lat,7),'lon':round(lon,7)}
def enrich_parcels(items):
 cache=load_parcel_cache();new=0
 candidates=sorted(items,key=lambda x:x.get('date',''),reverse=True)
 for item in candidates:
  if item.get('lat') and item.get('lon'):continue
  parsed=parcel_identifier(item.get('parcel',''))
  if not parsed:continue
  cache_key='.'.join(parsed)
  if cache_key not in cache and new<250:
   try:cache[cache_key]=resolve_parcel(item.get('parcel','')) or {}
   except Exception as exc:cache[cache_key]={'error':str(exc)[:160]}
   new+=1;time.sleep(.15)
  result=cache.get(cache_key) or {}
  if result.get('lat') is not None:item.update(result)
 PARCEL_CACHE.parent.mkdir(parents=True,exist_ok=True)
 PARCEL_CACHE.write_text(json.dumps(cache,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Parcel locations cached:',sum(1 for v in cache.values() if v.get('lat') is not None),'| new lookups:',new)
class PageParser(HTMLParser):
 def __init__(self):
  super().__init__();self.text=[];self.links=[];self.anchor=None;self.meta={};self.base=''
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if tag=='meta' and d.get('property') in ('article:published_time','og:title'):self.meta[d.get('property')]=d.get('content','')
  if tag=='a':self.anchor={'href':urllib.parse.urljoin(self.base,d.get('href','')),'text':''}
 def handle_data(self,data):
  value=re.sub(r'\s+',' ',data).strip()
  if value:self.text.append(value)
  if self.anchor is not None:self.anchor['text']+=' '+value
 def handle_endtag(self,tag):
  if tag=='a' and self.anchor is not None:
   if self.anchor['href'].startswith('http'):self.links.append(self.anchor)
   self.anchor=None
def parse_finance_sources():
 pages=[
  ('Wieloletnia Prognoza Finansowa Gdańska 2027–2051','https://www.gdansk.pl/urzad-miejski/2027-2051%2Ca%2C322561','WPF i przedsięwzięcia wieloletnie'),
  ('Projekt budżetu Gdańska na 2027 rok','https://media.gdansk.pl/komunikaty/879887/co-gdansk-zrobi-dla-ciebie-w-2027-roku','Projekt budżetu; wartości są planem, nie wykonaniem.')
 ]
 items=[];status=[]
 for fallback,url,summary in pages:
  try:
   parser=PageParser();parser.base=url;parser.feed(request(url))
   body=' '.join(parser.text);title=parser.meta.get('og:title') or fallback
   stamp=parser.meta.get('article:published_time','')
   date=stamp[:10] if stamp else ('2026-11-13' if '2027-2051' in url else '')
   amounts=re.findall(r'\d[\d\s.,]*\s*(?:mln\s*zł|mld\s*zł|zł)',body,re.I)
   description=summary+(' W publikacji wykryto wartości: '+', '.join(amounts[:8])+'.' if amounts else '')
   items.append(makeitem('finanse',title,date,url,description,summary=description))
   attachment_count=0
   for link in parser.links:
    href=link['href'];label=re.sub(r'\s+',' ',link['text']).strip()
    if re.search(r'\.(pdf|xlsx?|docx?|zip)(?:$|\?)',href,re.I) and attachment_count<20:
     items.append(makeitem('finanse',label or 'Załącznik finansowy',date,href,'Załącznik do oficjalnej publikacji: '+title,summary='Załącznik źródłowy — otwórz plik, aby sprawdzić tabele i kwoty.'))
     attachment_count+=1
   status.append({'source':fallback,'ok':True,'count':1+attachment_count,'url':url})
  except Exception as exc:status.append({'source':fallback,'ok':False,'count':0,'error':str(exc)[:220],'url':url})
 return items,status

def parse_council(key,label,url):
 page=request(url)
 class ScriptParser(HTMLParser):
  def __init__(self):super().__init__();self.scripts=[]
  def handle_starttag(self,tag,attrs):
   if tag=='script':self.scripts.append(dict(attrs))
 sp=ScriptParser();sp.feed(page)
 endpoint=url.rstrip('/').split('/')[-1];script_url=''
 for attrs in sp.scripts:
  src=attrs.get('src','')
  if endpoint in src:
   if src.startswith('//'):src='https:'+src
   elif src.startswith('/'):src='https://bip.gdansk.pl'+src
   elif not src.startswith('http'):src=url.rsplit('/',1)[0]+'/'+src
   script_url=src;break
 if not script_url:raise RuntimeError('BIP API script not found')
 script=request(script_url)
 auth=re.search(r'Authorization\s*:\s*["\']([^"\']+)["\']',script)
 if not auth:raise RuntimeError('BIP API authorization header not found')
 api='https://bip.gdansk.pl/picklock/'+endpoint+'?'+urllib.parse.urlencode({'rok':'2026','wyszukiwana_tresc':''})
 payload=json.loads(request(api,{'Authorization':auth.group(1),'Accept':'application/json, text/plain, */*','Referer':url,'Content-Type':'application/json'}))
 if payload.get('status') not in (200,'200'):raise RuntimeError('BIP API status: '+str(payload.get('status')))
 markup=payload.get('results','')
 if not isinstance(markup,str):raise RuntimeError('Unexpected BIP API results type')
 class RecordParser(HTMLParser):
  def __init__(self):super().__init__();self.rows=[];self.row=None;self.cell=None;self.anchor=None
  def handle_starttag(self,tag,attrs):
   d=dict(attrs)
   if tag=='tr':self.row=[]
   elif tag in ('td','th') and self.row is not None:self.cell={'text':'','links':[]}
   elif tag=='a':
    self.anchor={'url':d.get('href',''),'text':''}
    if self.cell is not None:self.cell['links'].append(self.anchor)
  def handle_data(self,data):
   if self.cell is not None:self.cell['text']+=' '+data
   if self.anchor is not None:self.anchor['text']+=' '+data
  def handle_endtag(self,tag):
   if tag=='a':self.anchor=None
   elif tag in ('td','th') and self.cell is not None:self.row.append(self.cell);self.cell=None
   elif tag=='tr' and self.row is not None:
    if self.row:self.rows.append(self.row)
    self.row=None
 rp=RecordParser();rp.feed(markup);records=[];current=None
 def clean(v):return re.sub(r'\s+',' ',html.unescape(v or '')).strip(' :|')
 def finish():
  if not current:return
  fields=current['fields'];title=fields.get('Przedmiot interpelacji') or fields.get('Przedmiot wniosku') or fields.get('Przedmiot petycji') or fields.get('Przedmiot')
  if not title:return
  date=fields.get('Data wpływu do Rady Miasta') or fields.get('Data wpływu') or ''
  author=fields.get('Imię i nazwisko radnej/radnego') or fields.get('Osoba wytwarzająca informację') or ''
  ezd=fields.get('Numer EZD','');answer_date=fields.get('Data odpowiedzi','')
  response=next((v for k,v in fields.items() if re.search(r'(treść odpowiedzi|odpowiedź na|odpowiedz|sposób załatwienia|rozpatrzenie)',k,re.I) and v and v.lower() not in ('tak','nie')), '')
  detail=' · '.join(filter(None,[current['ident'],('EZD '+ezd) if ezd else '',('Data odpowiedzi: '+answer_date) if answer_date else '']))
  records.append(makeitem(key,title,date,current.get('url') or url,detail,author=author,response=response,summary=title,response_date=answer_date,response_url=current.get('responseUrl','')))
 for row in rp.rows:
  if len(row)<2:continue
  field_label=clean(row[0]['text']);value=clean(row[1]['text'])
  if (key=='petycje' and field_label.lower()=='numer') or (key!='petycje' and field_label.upper() in ('CRI','CRZ')):
   finish();current={'ident':field_label+' '+value,'fields':{},'url':url,'responseUrl':''}
  if current:
   if field_label:current['fields'][field_label]=value
   for link in row[1].get('links',[]):
    href=link.get('url','')
    if href.startswith('http'):
     if re.search(r'odpowied',field_label,re.I):current['responseUrl']=href
     current['url']=href
     break
 finish()
 return records,{'source':label,'ok':bool(records),'count':len(records),'note':'Records extracted from BIP Picklock API HTML.' if records else 'API returned HTML but no records were parsed.','url':url}
def main():
 allitems=[];status=[]
 for source in SOURCES:
  key,label,url,kind=source[:4]
  try:
   items,st=parse_json_source(key,label,url,source[4]) if kind=='json' else parse_council(key,label,url)
   allitems.extend(items);status.append(st)
  except Exception as e:
   status.append({'source':label,'ok':False,'count':0,'error':str(e),'url':source[4] if len(source)>4 else url})
 finance_items,finance_status=parse_finance_sources();allitems.extend(finance_items);status.extend(finance_status)
 enrich_parcels(allitems)
 unique={x['id']:x for x in allitems}
 payload={'lastUpdated':datetime.now(timezone.utc).isoformat(),'items':list(unique.values()),'sourceStatus':status}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Fetched records:',len(unique));print(json.dumps(status,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
