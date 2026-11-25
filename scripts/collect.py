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
 def _legacy_init_removed(self):
 def __init__(self): super().__init__();self.links=[];self.texts=[]
 def handle_starttag(self,tag,attrs):
  if tag=='a':
   d=dict(attrs);href=d.get('href','')
   if href:self.links.append((href,d.get('title','')))
 def handle_data(self,data):
  t=data.strip()
  if t:self.texts.append(t)
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
 page=request(url);parser=PageParser();parser.feed(page)
 items=[];header=[]
 def clean(c):return re.sub(r'\\s+',' ',c.get('text','')).strip()
 for row in parser.rows:
  vals=[clean(c) for c in row]
  if not vals:continue
  low=[v.lower() for v in vals]
  if any(x in low for x in ('crz','numer','data wpływu','przedmiot wniosku','przedmiot petycji')):
   header=vals;continue
  # Extract BIP records using known labels from field/value or headered table layout
  title='';date='';author='';num='';response_date=''
  if header and len(header)==len(vals):
   pairs={h.lower():v for h,v in zip(header,vals)}
   title=next((v for h,v in pairs.items() if 'przedmiot' in h or h in ('tytuł','tytul')), '')
   date=next((v for h,v in pairs.items() if 'data wpływu' in h), '')
   author=next((v for h,v in pairs.items() if 'radnej/radnego' in h or 'imię i nazwisko' in h or 'autor' in h), '')
   num=next((v for h,v in pairs.items() if h in ('crz','numer')), '')
   response_date=next((v for h,v in pairs.items() if 'data odpowiedzi' in h), '')
  # BIP can also render records as repeated label/value cells
  if not title:
   for labelname in ('przedmiot wniosku','przedmiot petycji','przedmiot interpelacji','temat'):
    if labelname in low:
     i=low.index(labelname)
     if i+1<len(vals):title=vals[i+1]
   for labelname in ('data wpływu','data wpływu do rady miasta'):
    if not date and labelname in low:
     i=low.index(labelname)
     if i+1<len(vals):date=vals[i+1]
   for labelname in ('imię i nazwisko radnej/radnego','radny','radna'):
    if not author and labelname in low:
     i=low.index(labelname)
     if i+1<len(vals):author=vals[i+1]
  if title:
   links=[l for c in row for l in c.get('links',[])]
   doc=next((l['url'] for l in links if any(w in l['text'].lower() for w in ('pobierz','treść','odpowiedź','pdf'))),url)
   desc=' · '.join(filter(None,[('Nr '+num) if num else '',('Odpowiedź: '+response_date) if response_date else '']))
   items.append(makeitem(key,title,date,doc,desc,author=author))
 if not items:
  # Keep a few official links as discoverable records if BIP HTML structure changes
  for href,title in parser.links:
   if title and any(t in title.lower() for t in ('interpel','zapyt','petyc')) and href.startswith('https://'):
    items.append(makeitem(key,title,url=href,description='Link do oficjalnego BIP'))
 return items,{'source':label,'ok':bool(items),'count':len(items),'note':'HTML table extraction; completeness requires validation against BIP page.','url':url}
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
