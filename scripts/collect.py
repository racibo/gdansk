#!/usr/bin/env python3
"""Fetch public Gdansk BIP data into a normalized static JSON file.
Initial scope: interpellations, councillor queries, WUIA decisions, building notifications.
"""
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
 ('decyzje','Decyzje WUIA','https://files.cloudgdansk.pl/d/otwarte-dane/bip-umg/publikacja-decyzji-wuia.json','json_decisions'),
 ('zgloszenia','Zgłoszenia budowlane','https://files.cloudgdansk.pl/d/otwarte-dane/bip-umg/publikacja-zgloszen-wuia.json','json_notices'),
]
class PageParser(HTMLParser):
 def __init__(self): super().__init__();self.links=[];self.texts=[];self._text=''
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
def parse_json_source(key,label,url):
 data=json.loads(request(url));rows=data.get('results',[])
 items=[]
 for r in rows:
  if key=='decyzje':
   title=r.get('rodzaj_inwestycji') or 'Decyzja administracyjna'
   address=r.get('adres_inwestycji','');parcel=r.get('obreb_dzialka','')
   detail=' · '.join(filter(None,[r.get('typ_decyzji'),r.get('rodzaj_decyzji'),('nr '+str(r.get('nr_decyzji'))) if r.get('nr_decyzji') else '']))
   items.append(makeitem(key,title,r.get('data_decyzji'),url,detail,address=address,parcel=parcel))
  else:
   title=r.get('rodzaj_inwestycji') or 'Zgłoszenie budowlane'
   address=r.get('adres_inwestycji','')
   items.append(makeitem(key,title,r.get('data_wplywu'),url,'Numer zgłoszenia: '+str(r.get('numer_wniosku','')),address=address,parcel=address,investor=r.get('inwestor','')))
 return items,{'source':label,'ok':True,'count':len(items),'updated':data.get('description',{}).get('generationDate'),'url':url}
def parse_council(key,label,url):
 page=request(url);parser=PageParser();parser.feed(page)
 # BIP pages can render their list in scripts; record only recognizable document/article links rather than inventing items.
 candidates=[]
 for href,linktitle in parser.links:
  href=html.unescape(href)
  if href.startswith('/'):href='https://bip.gdansk.pl'+href
  title=linktitle.strip()
  if not title:continue
  if any(term in title.lower() for term in ('interpel','zapyt','odpowied','radny','radnej','pdf')) and href.startswith('https://'):
   candidates.append(makeitem(key,title,'',href,'Dokument lub link z oficjalnej strony BIP'))
 return candidates,{'source':label,'ok':True,'count':len(candidates),'note':'Scraped document links; verify completeness as BIP list may be dynamically rendered.','url':url}
def main():
 allitems=[];status=[]
 for key,label,url,kind in SOURCES:
  try:
   items,st=parse_json_source(key,label,url) if kind.startswith('json') else parse_council(key,label,url)
   allitems.extend(items);status.append(st)
  except Exception as e:
   status.append({'source':label,'ok':False,'count':0,'error':str(e),'url':url})
 # stable de-duplication
 unique={}
 for i in allitems:
  unique[i['id']]=i
 payload={'lastUpdated':datetime.now(timezone.utc).isoformat(),'items':list(unique.values()),'sourceStatus':status}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Fetched records:',len(unique));print(json.dumps(status,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
