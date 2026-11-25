#!/usr/bin/env python3
"""Fetch public Gdansk BIP data into a normalized static JSON file."""
import json, re, urllib.request, html, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'public'/'data'/'latest.json'
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
def makeitem(source,title,date='',url='',description='',author='',address='',parcel='',investor='',status='',response='',summary=''):
 ident='-'.join(filter(None,[source,re.sub(r'[^a-zA-Z0-9]+','-',str(title)+str(date)+str(address))[:90].strip('-')]))
 return {'id':ident,'type':source,'category':LABELS.get(source,source),'title':title,'date':normdate(date),'url':url,'description':description,'summary':summary,'author':author,'address':address,'parcel':parcel,'investor':investor,'status':status,'response':response}
def parse_json_source(key,label,feed_url,public_url):
 data=json.loads(request(feed_url));rows=data.get('results',[])
 items=[]
 for r in rows:
  if key=='decyzje':
   title=r.get('rodzaj_inwestycji') or 'Decyzja administracyjna'
   address=r.get('adres_inwestycji','');parcel=r.get('obreb_dzialka','')
   raw_status=' · '.join(str(r.get(k,'')) for k in ('typ_decyzji','rodzaj_decyzji','wynik','status','rozstrzygniecie') if r.get(k))
   detail=' · '.join(filter(None,[raw_status,('nr '+str(r.get('nr_decyzji'))) if r.get('nr_decyzji') else '']))
   items.append(makeitem(key,title,r.get('data_decyzji'),public_url,detail,address=address,parcel=parcel,status=raw_status,summary=title))
  else:
   title=r.get('rodzaj_inwestycji') or 'Zgłoszenie budowlane'
   address=r.get('adres_inwestycji','')
   raw_status=' · '.join(str(r.get(k,'')) for k in ('status','sprzeciw','wynik') if r.get(k))
   detail='Numer zgłoszenia: '+str(r.get('numer_wniosku',''))+(' · '+raw_status if raw_status else '')
   items.append(makeitem(key,title,r.get('data_wplywu'),public_url,detail,address=address,parcel=r.get('obreb_dzialka',address),investor=r.get('inwestor',''),status=raw_status,summary=title))
 return items,{'source':label,'ok':bool(items),'count':len(items),'updated':data.get('description',{}).get('generationDate'),'url':public_url,'dataUrl':feed_url}
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
 auth=re.search(r'Authorization\\s*:\\s*["\\']([^"\\']+)["\\']',script)
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
 def clean(v):return re.sub(r'\\s+',' ',html.unescape(v or '')).strip(' :|')
 def finish():
  if not current:return
  fields=current['fields'];title=fields.get('Przedmiot interpelacji') or fields.get('Przedmiot wniosku') or fields.get('Przedmiot petycji') or fields.get('Przedmiot')
  if not title:return
  date=fields.get('Data wpływu do Rady Miasta') or fields.get('Data wpływu') or ''
  author=fields.get('Imię i nazwisko radnej/radnego') or fields.get('Osoba wytwarzająca informację') or ''
  ezd=fields.get('Numer EZD','');answer_date=fields.get('Data odpowiedzi','')
  response=next((v for k,v in fields.items() if re.search(r'(treść odpowiedzi|odpowiedź na|odpowiedz|sposób załatwienia|rozpatrzenie)',k,re.I) and v and v.lower() not in ('tak','nie')), '')
  detail=' · '.join(filter(None,[current['ident'],('EZD '+ezd) if ezd else '',('Data odpowiedzi: '+answer_date) if answer_date else '']))
  records.append(makeitem(key,title,date,current.get('url') or url,detail,author=author,response=response,summary=title))
 for row in rp.rows:
  if len(row)<2:continue
  field_label=clean(row[0]['text']);value=clean(row[1]['text'])
  if (key=='petycje' and field_label.lower()=='numer') or (key!='petycje' and field_label.upper() in ('CRI','CRZ')):
   finish();current={'ident':field_label+' '+value,'fields':{},'url':url}
  if current:
   if field_label:current['fields'][field_label]=value
   for link in row[1].get('links',[]):
    href=link.get('url','')
    if href.startswith('http'):current['url']=href;break
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
 unique={x['id']:x for x in allitems}
 payload={'lastUpdated':datetime.now(timezone.utc).isoformat(),'items':list(unique.values()),'sourceStatus':status}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Fetched records:',len(unique));print(json.dumps(status,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
