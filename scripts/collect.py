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
 page=request(url);parser=PageParser();parser.feed(page)
 # BIP renders each entry as a label/value block (not an HTML table).
 # Normalize all visible page text, then split entries by CRZ number.
 raw=' '.join(parser.texts)
 raw=re.sub(r'\s+',' ',html.unescape(raw)).strip()
 matches=list(re.finditer((r'Numer\s+(\d{1,3}/\d{4})' if key=='petycje' else r'CRZ\s*[:|]?\s*(\d{1,3}/\d{2,4})'),raw,re.I))
 items=[]
 def field(segment,patterns):
  for pattern in patterns:
   m=re.search(pattern,segment,re.I)
   if m:return m.group(1).strip()
  return ''
 for i,m in enumerate(matches):
  segment=raw[m.start():matches[i+1].start() if i+1<len(matches) else len(raw)]
  crz=m.group(1)
  ezd=field(segment,[r'Numer EZD\s*[:|]?\s*([0-9]+)'])
  date=field(segment,[r'Data wpływu do Rady Miasta\s*[:|]?\s*(\d{4}-\d{2}-\d{2})',r'Data wpływu\s*[:|]?\s*(\d{4}-\d{2}-\d{2})'])
  author=field(segment,[r'Imię i nazwisko radnej/radnego\s*[:|]?\s*([^|]+?)(?=\s+Przedmiot wniosku|\s+Treść|\s+Data odpowiedzi|$)'])
  title=field(segment,[r'Przedmiot (?:wniosku|petycji)\s*[:|]?\s*(.+?)(?=\s+Treść\s*[:|]?|\s+Petycja\s*[:|]?|\s+Data odpowiedzi|\s+Termin odpowiedzi|\s+Komórka prowadząca|\s+Treść odpowiedzi|\s+Uwagi|$)'])
  answer=field(segment,[r'Data odpowiedzi\s*[:|]?\s*(\d{4}-\d{2}-\d{2})'])
  if not title:
   # Fallback captures short subject before document controls when label whitespace varies.
   title=field(segment,[r'Przedmiot wniosku\s+(.+?)\s+(?:Treść|Data odpowiedzi|Uwagi)'])
  if not title:continue
  title=re.sub(r'\s+',' ',title).strip(' |')
  desc=' · '.join(filter(None,[('CRZ '+crz),('EZD '+ezd) if ezd else '',('Odpowiedź: '+answer) if answer else '']))
  items.append(makeitem(key,title,date,url,desc,author=author))
 # Only if the BIP page actually contains the records, avoid a fake success/empty feed.
 count_match=re.search(r'Ilość (?:interpelacji|zapytań|petycji)\s*[:|]?\s*(\d+)',raw,re.I)
 reported=int(count_match.group(1)) if count_match else None
 return items,{'source':label,'ok':bool(items),'count':len(items),'reportedCount':reported,'note':'Extracted records from BIP label/value content.' if items else 'No CRZ records parsed from page text; BIP layout may have changed or data may be client-loaded.','url':url}

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
