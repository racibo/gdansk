#!/usr/bin/env python3
"""Fetch public Gdansk BIP data into a normalized static JSON file."""
import json, re, urllib.request, html
from datetime import datetime, timezone
from pathlib import Path
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'public'/'data'/'latest.json'
HEADERS={'User-Agent':'GdanskRadar/0.1 (public-source monitor; contact: racibo.pl)'}
SOURCES=[
 ('interpelacje','Interpelacje','https://bip.gdansk.pl/rada-miasta/publikacja-interpelacji-radnych-miasta-gdanska','council'),
 ('zapytania','Zapytania radnych','https://bip.gdansk.pl/rada-miasta/publikacja-zapytan-radnych-miasta-gdanska','council'),
 ('petycje','Petycje','https://bip.gdansk.pl/urzad-miejski/publikacja-petycji-do-rady-miasta-gdanska','council'),
 ('decyzje','Decyzje WUIA','https://files.cloudgdansk.pl/d/otwarte-dane/bip-umg/publikacja-decyzji-wuia.json','json_decisions','https://bip.gdansk.pl/urzad-miejski/raporty-i-publikacje/publikacja-decyzji-wuia'),
 ('zgloszenia','Zgłoszenia budowlane','https://files.cloudgdansk.pl/d/otwarte-dane/bip-umg/publikacja-zgloszen-wuia.json','json_notices','https://bip.gdansk.pl/urzad-miejski/raporty-i-publikacje/publikacja-zgloszen-wuia'),
]
class PageParser(HTMLParser):
 def __init__(self):
  super().__init__();self.links=[];self.texts=[];self.rows=[];self.row=None;self.cell=None;self.in_table=False;self.anchor=None
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if tag=='table':self.in_table=True
  elif tag=='tr' and self.in_table:self.row=[]
  elif tag in ('td','th') and self.row is not None:self.cell={'text':'','links':[]}
  elif tag=='a':
   href=d.get('href','')
   if href.startswith('/'):href='https://bip.gdansk.pl'+href
   if href:
    self.anchor={'url':href,'text':''}
    if self.cell is not None:self.cell['links'].append(self.anchor)
    else:self.links.append((href,d.get('title','')))
 def handle_data(self,data):
  t=data.strip()
  if t:
   self.texts.append(t)
   if self.cell is not None:self.cell['text']+=' '+t
   if self.anchor is not None:self.anchor['text']+=' '+t
 def handle_endtag(self,tag):
  if tag=='a':self.anchor=None
  elif tag in ('td','th') and self.cell is not None:self.row.append(self.cell);self.cell=None
  elif tag=='tr' and self.row is not None:
   if self.row:self.rows.append(self.row)
   self.row=None
  elif tag=='table':self.in_table=False
def request(url):
 req=urllib.request.Request(url,headers=HEADERS)
 with urllib.request.urlopen(req,timeout=45) as resp:return resp.read().decode('utf-8','replace')
def normdate(value):
 if not value:return ''
 value=str(value).strip()
 for fmt in ('%Y-%m-%d','%d.%m.%Y','%Y/%m/%d'):
  try:return datetime.strptime(value,fmt).date().isoformat()
  except ValueError:pass
 return value
def makeitem(source,title,date='',url='',description='',author='',address='',parcel='',investor=''):
 return {'id':source+'-'+re.sub(r'[^a-zA-Z0-9]+','-',(title+date+address))[:90].strip('-'),'type':source,'category':dict((s[0],s[1]) for s in SOURCES).get(source,source),'title':title,'date':normdate(date),'url':url,'description':description,'author':author,'address':address,'parcel':parcel,'investor':investor}
def parse_json_source(key,label,feed_url,public_url):
 data=json.loads(request(feed_url));rows=data.get('results',[])
 items=[]
 for r in rows:
  if key=='decyzje':
   title=r.get('rodzaj_inwestycji') or 'Decyzja administracyjna'
   address=r.get('adres_inwestycji','');parcel=r.get('obreb_dzialka','')
   detail=' · '.join(filter(None,[r.get('typ_decyzji'),r.get('rodzaj_decyzji'),('nr '+str(r.get('nr_decyzji'))) if r.get('nr_decyzji') else '']))
   items.append(makeitem(key,title,r.get('data_decyzji'),public_url,detail,address=address,parcel=parcel))
  else:
   title=r.get('rodzaj_inwestycji') or 'Zgłoszenie budowlane'
   address=r.get('adres_inwestycji','')
   items.append(makeitem(key,title,r.get('data_wplywu'),public_url,'Numer zgłoszenia: '+str(r.get('numer_wniosku','')),address=address,parcel=address,investor=r.get('inwestor','')))
 return items,{'source':label,'ok':True,'count':len(items),'updated':data.get('description',{}).get('generationDate'),'url':public_url,'dataUrl':feed_url}
def parse_council(key,label,url):
 # BIP pages load their records from the Picklock API; the API returns HTML in JSON.results.
 page=request(url)
 class ScriptParser(HTMLParser):
  def __init__(self): super().__init__(); self.scripts=[]
  def handle_starttag(self,tag,attrs):
   if tag=='script': self.scripts.append(dict(attrs))
 sp=ScriptParser();sp.feed(page)
 endpoint=url.rstrip('/').split('/')[-1]
 script_url=''
 for attrs in sp.scripts:
  src=attrs.get('src','')
  if endpoint in src:
   if src.startswith('//'):src='https:'+src
   elif src.startswith('/'):src='https://bip.gdansk.pl'+src
   elif not src.startswith('http'):src=url.rsplit('/',1)[0]+'/'+src
   script_url=src;break
 if not script_url: raise RuntimeError('BIP API script not found')
 script=request(script_url)
 auth=re.search(r'Authorization\s*:\s*["\']([^"\']+)["\']',script)
 if not auth: raise RuntimeError('BIP API authorization header not found')
 import urllib.parse
 api='https://bip.gdansk.pl/picklock/'+endpoint+'?'+urllib.parse.urlencode({'rok':'2026','wyszukiwana_tresc':''})
 req=urllib.request.Request(api,headers={**HEADERS,'Authorization':auth.group(1),'Accept':'application/json, text/plain, */*','Referer':url,'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=60) as resp: payload=json.loads(resp.read().decode('utf-8','replace'))
 if payload.get('status') not in (200,'200'): raise RuntimeError('BIP API status: '+str(payload.get('status')))
 markup=payload.get('results','')
 if not isinstance(markup,str): raise RuntimeError('Unexpected BIP API results type')
 class RecordParser(HTMLParser):
  def __init__(self):
   super().__init__();self.rows=[];self.row=None;self.cell=None;self.anchor=None
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
 rp=RecordParser();rp.feed(markup)
 records=[];current=None
 def clean(v):return re.sub(r'\s+',' ',html.unescape(v or '')).strip(' :|')
 def finish():
  if not current:return
  fields=current['fields'];ident=current['ident']
  title=fields.get('Przedmiot interpelacji') or fields.get('Przedmiot wniosku') or fields.get('Przedmiot petycji') or fields.get('Przedmiot')
  if not title:return
  date=fields.get('Data wpływu do Rady Miasta') or fields.get('Data wpływu') or ''
  author=fields.get('Imię i nazwisko radnej/radnego') or fields.get('Osoba wytwarzająca informację') or ''
  ezd=fields.get('Numer EZD','')
  answer=fields.get('Data odpowiedzi','')
  detail=' · '.join(filter(None,[ident,('EZD '+ezd) if ezd else '',('Odpowiedź: '+answer) if answer else '']))
  records.append(makeitem(key,title,date,current.get('url') or url,detail,author=author))
 for row in rp.rows:
  if len(row)<2:continue
  field_label=clean(row[0]['text']);value=clean(row[1]['text'])
  if key=='petycje' and field_label.lower()=='numer' or key!='petycje' and field_label.upper() in ('CRI','CRZ'):
   finish();current={'ident':field_label+' '+value,'fields':{},'url':url}
  if current:
   if field_label:current['fields'][field_label]=value
   for link in row[1].get('links',[]):
    href=link.get('url','')
    if href.startswith('http'):
     current['url']=href;break
 finish()
 count_match=re.search(r'Ilość\s+(?:interpelacji|zapytań|petycji)\s*:\s*<[^>]*>\s*(\d+)',markup,re.I)
 reported=int(count_match.group(1)) if count_match else None
 return records,{'source':label,'ok':bool(records),'count':len(records),'reportedCount':reported,'note':'Records extracted from BIP Picklock API HTML.' if records else 'API returned HTML but no records were parsed.','url':url}

def main():
 allitems=[];status=[]
 for source in SOURCES:
  key,label,url,kind=source[:4]
  try:
   items,st=parse_json_source(key,label,url,source[4]) if kind.startswith('json') else parse_council(key,label,url)
   allitems.extend(items);status.append(st)
  except Exception as e:
   status.append({'source':label,'ok':False,'count':0,'error':str(e),'url':source[4] if len(source)>4 else url})
 unique={}
 for item in allitems:unique[item['id']]=item
 payload={'lastUpdated':datetime.now(timezone.utc).isoformat(),'items':list(unique.values()),'sourceStatus':status}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Fetched records:',len(unique));print(json.dumps(status,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
