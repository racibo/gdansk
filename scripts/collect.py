#!/usr/bin/env python3
"""Fetch public Gdansk BIP data into a normalized static JSON file."""
import json, re, urllib.request, html, urllib.parse, time, csv, io
from datetime import datetime, timezone
from pathlib import Path
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'public'/'data'/'latest.json'
PARCEL_CACHE=ROOT/'public'/'data'/'parcel_cache.json'
GEOCODE_CACHE=ROOT/'public'/'data'/'geocode_cache.json'
CRU_SEARCH='https://rejestrumow.gov.pl/api-dp/v1/agreements/search'
CRU_DETAIL='https://rejestrumow.gov.pl/api-dp/v1/agreement/'
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
LABELS['umowy']='Umowy z Centralnego Rejestru Umów JSFP'
def request(url,headers=None):
 req=urllib.request.Request(url,headers={**HEADERS,**(headers or {})})
 with urllib.request.urlopen(req,timeout=60) as resp:return resp.read().decode('utf-8','replace')

def request_bytes(url,headers=None):
 req=urllib.request.Request(url,headers={**HEADERS,**(headers or {})})
 with urllib.request.urlopen(req,timeout=90) as resp:return resp.read()
def extract_spreadsheet(url,fmt=''):
 """Read a bounded, searchable preview of official CSV/XLSX/XLS resources."""
 fmt=(fmt or '').upper()
 try:
  raw=request_bytes(url)
  if fmt=='CSV' or url.lower().split('?')[0].endswith('.csv'):
   decoded=raw.decode('utf-8-sig','replace')
   rows=list(csv.reader(io.StringIO(decoded)))[:600]
   return '\n'.join(' | '.join(str(v or '') for v in row) for row in rows)[:18000]
  if fmt in ('XLSX','XLSM') or url.lower().split('?')[0].endswith(('.xlsx','.xlsm')):
   import openpyxl
   wb=openpyxl.load_workbook(io.BytesIO(raw),read_only=True,data_only=True)
   sections=[]
   for ws in wb.worksheets[:12]:
    lines=[]
    for idx,row in enumerate(ws.iter_rows(values_only=True)):
     if idx>=600:break
     values=[str(v).strip() if v is not None else '' for v in row]
     if any(values):lines.append(' | '.join(values))
    if lines:sections.append('ARKUSZ: '+ws.title+'\n'+'\n'.join(lines))
   return '\n\n'.join(sections)[:18000]
  if fmt=='XLS' or url.lower().split('?')[0].endswith('.xls'):
   import xlrd
   book=xlrd.open_workbook(file_contents=raw,on_demand=True)
   sections=[]
   for sheet in book.sheets()[:12]:
    lines=[]
    for r in range(min(sheet.nrows,600)):
     values=[str(sheet.cell_value(r,col)).strip() for col in range(sheet.ncols)]
     if any(values):lines.append(' | '.join(values))
    if lines:sections.append('ARKUSZ: '+sheet.name+'\n'+'\n'.join(lines))
   return '\n\n'.join(sections)[:18000]
 except Exception as exc:
  return 'Nie udało się odczytać arkusza automatycznie: '+str(exc)[:220]
 return ''
def normdate(value):
 if not value:return ''
 value=str(value).strip()
 for fmt in ('%Y-%m-%d','%d.%m.%Y','%Y/%m/%d'):
  try:return datetime.strptime(value,fmt).date().isoformat()
  except ValueError:pass
 return value
def makeitem(source,title,date='',url='',description='',author='',address='',parcel='',investor='',status='',response='',summary='',response_date='',response_url='',lat='',lon='',parcel_id='',source_catalog=''):
 ident='-'.join(filter(None,[source,re.sub(r'[^a-zA-Z0-9]+','-',str(title)+str(date)+str(address))[:90].strip('-')]))
 return {'id':ident,'type':source,'category':LABELS.get(source,source),'title':title,'date':normdate(date),'url':url,'description':description,'summary':summary,'author':author,'address':address,'parcel':parcel,'investor':investor,'status':status,'response':response,'responseDate':normdate(response_date),'responseUrl':response_url,'lat':lat,'lon':lon,'parcelId':parcel_id,'sourceCatalog':source_catalog}
def matching_value(row,*tokens):
 for key,value in row.items():
  normalized=re.sub(r'[^a-z0-9]','',str(key).lower())
  if any(token in normalized for token in tokens) and value is not None and str(value).strip():
   return str(value).strip()
 return ''
def first_value(row,*keys):
 for key in keys:
  value=row.get(key)
  if value is not None and str(value).strip():return str(value).strip()
 normalized={re.sub(r'[^a-z0-9]','',str(k).lower()):v for k,v in row.items()}
 for key in keys:
  value=normalized.get(re.sub(r'[^a-z0-9]','',str(key).lower()))
  if value is not None and str(value).strip():return str(value).strip()
 return ''
def find_record_url(row,excluded=()):
 excluded=set(excluded)
 candidates=[]
 def walk(value,key=''):
  if isinstance(value,dict):
   for k,v in value.items():walk(v,str(k).lower())
  elif isinstance(value,list):
   for v in value:walk(v,key)
  elif isinstance(value,str) and value.strip().startswith(('https://','http://')):
   candidates.append((key,value.strip()))
 walk(row)
 preferred=('url','link','href','dokument','zalacznik','załącznik','attachment','detail')
 for key,url in candidates:
  if url in excluded:continue
  if any(token in key for token in preferred):return url
 for key,url in candidates:
  if url not in excluded and not any(part in url.lower() for part in ('publikacja-decyzji-wuia','publikacja-zgloszen-wuia','publikacja-interpelacji','publikacja-zapytan','publikacja-petycji')):return url
 return ''
def parse_json_source(key,label,feed_url,public_url):
 data=json.loads(request(feed_url))
 rows=data if isinstance(data,list) else data.get('results',data.get('data',[]))
 if isinstance(rows,dict):rows=rows.get('results',rows.get('items',[]))
 if not isinstance(rows,list):raise RuntimeError('Unexpected JSON records structure')
 items=[]
 for r in rows:
  if not isinstance(r,dict):continue
  address=first_value(r,'adres_inwestycji','adres inwestycji','adres','ulica','lokalizacja','miejsce_inwestycji') or matching_value(r,'adresinwestycji','lokalizacj','ulica')
  parcel=first_value(r,'obreb_dzialka','obręb_działka','obreb i dzialka','nr_obrebu_i_dzialki','numer_obrebu_i_dzialki','obreb_dzialka_nr','dzialka','działka','nr_dzialki','numer_dzialki') or matching_value(r,'obreb','dzialka')
  if key=='decyzje':
   title=first_value(r,'rodzaj_inwestycji','nazwa_inwestycji','przedmiot','rodzaj decyzji') or 'Decyzja administracyjna'
   raw_status=' · '.join(filter(None,[first_value(r,k) for k in ('typ_decyzji','rodzaj_decyzji','wynik','status','rozstrzygniecie','rozstrzygnięcie')]))
   number=first_value(r,'nr_decyzji','numer_decyzji','numer','sygnatura','znak_sprawy','id')
   detail=' · '.join(filter(None,[raw_status,('nr '+number) if number else '']))
   date=first_value(r,'data_decyzji','data')
   direct_url=find_record_url(r,{public_url,feed_url})
   items.append(makeitem(key,title,date,direct_url,detail,address=address,parcel=parcel,status=raw_status,summary=title,source_catalog=public_url))
  else:
   title=first_value(r,'rodzaj_inwestycji','nazwa_inwestycji','przedmiot') or 'Zgłoszenie budowlane'
   raw_status=' · '.join(filter(None,[first_value(r,k) for k in ('status','sprzeciw','wynik')]))
   detail=' · '.join(filter(None,['Numer zgłoszenia: '+first_value(r,'numer_wniosku','nr_wniosku'),raw_status]))
   date=first_value(r,'data_wplywu','data_zgloszenia','data')
   direct_url=find_record_url(r,{public_url,feed_url})
   items.append(makeitem(key,title,date,direct_url,detail,address=address,parcel=parcel,investor=first_value(r,'inwestor'),status=raw_status,summary=title,source_catalog=public_url))
 return items,{'source':label,'ok':bool(items),'count':len(items),'updated':data.get('description',{}).get('generationDate') if isinstance(data,dict) else None,'url':public_url,'dataUrl':feed_url}
def load_parcel_cache():
 try:return json.loads(PARCEL_CACHE.read_text(encoding='utf-8'))
 except Exception:return {}
def parcel_identifier(value):
 text=str(value or '')
 patterns=(
  r'(?<!\d)(\d{4})\s*\.\s*(\d+(?:/\d+)?)(?!\d)',
  r'(?<!\d)(\d{4})\s*(?:obr[eę]b(?:u)?\s*)?[,;:/ -]+\s*(?:dzia[lł]k[aęi]\s*)?(\d+(?:/\d+)?)(?!\d)',
 )
 for pattern in patterns:
  match=re.search(pattern,text,re.I)
  if match:return match.group(1),match.group(2)
 return None
def resolve_parcel(value):
 parsed=parcel_identifier(value)
 if not parsed:return None
 region,number=parsed
 identifier=GDANSK_TERYT+'.'+region+'.'+number
 # The identifier is fully qualified, so use GetParcelById. GetParcelByIdOrNr
 # returns a match count in its first line and is not compatible with the 0-status check below.
 params=urllib.parse.urlencode({'request':'GetParcelById','id':identifier,'result':'geom_wkt,teryt,parcel,region,commune','srid':'4326'})
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
  if cache_key not in cache and new<500:
   try:
    resolved=resolve_parcel(item.get('parcel',''))
    if resolved:cache[cache_key]=resolved
   except Exception as exc:print('ULDK lookup failed:',cache_key,str(exc)[:120])
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
def parse_ckan_finance():
 base='https://ckan.multimediagdansk.pl'
 packages={}
 for term in ('finanse','budżet'):
  api=base+'/api/3/action/package_search?'+urllib.parse.urlencode({'q':term,'rows':100})
  payload=json.loads(request(api))
  if not payload.get('success'):raise RuntimeError('CKAN package_search failed for '+term)
  for pkg in payload.get('result',{}).get('results',[]):packages[pkg.get('id') or pkg.get('name')]=pkg
 items=[]
 for pkg in packages.values():
  org=pkg.get('organization') or {}
  tags=[str(t.get('name','')).lower() for t in pkg.get('tags',[])]
  if org.get('name') not in ('um-gdansk','urzad-miejski') and not any('finans' in t or 'budzet' in t or 'budżet' in t for t in tags):continue
  dataset_url=base+'/dataset/'+str(pkg.get('name',''))
  notes=html.unescape(re.sub(r'<[^>]+>',' ',pkg.get('notes') or ''))
  items.append(makeitem('finanse',pkg.get('title') or pkg.get('name'),(pkg.get('metadata_modified') or '')[:10],'',notes,summary=(notes[:420] or 'Zbiór danych z oficjalnego portalu Otwarty Gdańsk.'),source_catalog=dataset_url))
  for resource in pkg.get('resources',[]):
   resource_url=resource.get('url') or ''
   if not resource_url.startswith('http'):continue
   name=resource.get('name') or resource.get('description') or pkg.get('title') or 'Zasób finansowy'
   fmt=(resource.get('format') or '').upper()
   text_content=resource.get('description') or notes
   if fmt in ('CSV','XLSX','XLS','XLSM') or resource_url.lower().split('?',1)[0].endswith(('.csv','.xlsx','.xls','.xlsm')):
    extracted=extract_spreadsheet(resource_url,fmt)
    if extracted:text_content+='\n\nDANE Z ARKUSZA (podgląd do 600 wierszy na arkusz):\n'+extracted
   items.append(makeitem('finanse',name,(resource.get('last_modified') or resource.get('created') or pkg.get('metadata_modified') or '')[:10],resource_url,'Zbiór: '+str(pkg.get('title') or '')+'\n'+text_content,summary='Zasób '+fmt+' ze zbioru: '+str(pkg.get('title') or '')+'.'))
 return items,{'source':'Otwarty Gdańsk – CKAN (zbiory finansowe)','ok':True,'count':len(items),'url':base+'/dataset/?organization=um-gdansk&tags=finanse'}
def parse_finance_sources():
 pages=[
  ('Wieloletnia Prognoza Finansowa Gdańska 2027–2051','https://www.gdansk.pl/urzad-miejski/2027-2051%2Ca%2C322561','WPF i przedsięwzięcia wieloletnie'),
  ('Projekt budżetu Gdańska na 2027 rok','https://media.gdansk.pl/komunikaty/879887/co-gdansk-zrobi-dla-ciebie-w-2027-roku','Projekt budżetu; wartości są planem, nie wykonaniem.'),
  ('Zmiany budżetu Gdańska – zarządzenie 1654/26','https://baw.bip.gdansk.pl/UrzadMiejskiwGdansku/document/568413/Zarz%C4%85dzenie','Zarządzenie zmieniające plan budżetu 2026; zawiera załączniki z tabelami zmian wydatków.')
 ]
 items=[];status=[]
 for fallback,url,summary in pages:
  try:
   parser=PageParser();parser.base=url;parser.feed(request(url))
   body=' '.join(parser.text);title=parser.meta.get('og:title') or fallback
   stamp=parser.meta.get('article:published_time','')
   date=stamp[:10] if stamp else ('2026-11-13' if '2027-2051' in url else '')
   amounts=re.findall(r'\d[\d\s.,]*\s*(?:mln\s*zł|mld\s*zł|zł)',body,re.I)
   short_summary=summary+(' W publikacji wykryto wartości: '+', '.join(amounts[:8])+'.' if amounts else '')
   items.append(makeitem('finanse',title,date,url,body[:24000],summary=short_summary))
   attachment_count=0
   for link in parser.links:
    href=link['href'];label=re.sub(r'\s+',' ',link['text']).strip()
    if (re.search(r'\\.(pdf|xlsx?|csv|docx?|zip)(?:$|\\?)',href,re.I) or 'GetZipxAttachment' in href) and attachment_count<30:
     ext=(href.split('?',1)[0].rsplit('.',1)[-1] if '.' in href.split('?',1)[0] else '').upper()
     extracted=extract_spreadsheet(href,ext) if ext in ('XLSX','XLS','XLSM','CSV') else ''
     description='Załącznik do oficjalnej publikacji: '+title
     if extracted:description+='\n\nDANE Z ARKUSZA (podgląd do 600 wierszy na arkusz):\n'+extracted
     items.append(makeitem('finanse',label or 'Załącznik finansowy',date,href,description,summary=('Odczytano zawartość arkusza '+ext+'.' if extracted else 'Załącznik źródłowy — otwórz plik, aby sprawdzić tabele i kwoty.')))
     attachment_count+=1
   status.append({'source':fallback,'ok':True,'count':1+attachment_count,'url':url})
  except Exception as exc:status.append({'source':fallback,'ok':False,'count':0,'error':str(exc)[:220],'url':url})
 return items,status

def extract_explicit_address(text):
 """Extract explicit Polish street-address mentions from document text."""
 if not text:return ''
 patterns=[
  r'\b(?:ul(?:ica|icy|icę)?\.?|aleja|alei|al\.?|plac|pl\.?|rondo|skwer|bulwar)\s+([A-ZĄĆĘŁŃÓŚŹŻ][\wĄĆĘŁŃÓŚŹŻąćęłńóśźż.-]*(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][\wĄĆĘŁŃÓŚŹŻąćęłńóśźż.-]*){0,4})\s+(\d+[A-Za-z]?(?:\s*/\s*\d+)?)',
  r'\b(?:ul(?:ica|icy|icę)?\.?|aleja|alei|al\.?|plac|pl\.?|rondo|skwer|bulwar)\s+([A-ZĄĆĘŁŃÓŚŹŻ][\wĄĆĘŁŃÓŚŹŻąćęłńóśźż.-]*(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][\wĄĆĘŁŃÓŚŹŻąćęłńóśźż.-]*){0,4})'
 ]
 for pattern in patterns:
  match=re.search(pattern,text,re.I)
  if match:
   name=match.group(1).strip(' ,.;:')
   number=match.group(2).strip() if match.lastindex and match.lastindex>=2 else ''
   matched_prefix=text[match.start():match.start(1)].lower()
   prefix='ul. '
   if 'alej' in matched_prefix or re.search(r'\bal\.?\s',matched_prefix):prefix='al. '
   elif 'plac' in matched_prefix or re.search(r'\bpl\.?\s',matched_prefix):prefix='pl. '
   elif 'rondo' in matched_prefix:prefix='rondo '
   elif 'skwer' in matched_prefix:prefix='skwer '
   elif 'bulwar' in matched_prefix:prefix='bulwar '
   return prefix+name+(' '+number if number else '')
 return ''
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
  address=next((v for k,v in fields.items() if re.search(r'(adres inwestycji|lokalizacja|ulica|miejsce inwestycji|adres)',k,re.I) and v), '')
  if not address:
   address=extract_explicit_address(' '.join([title, *fields.values(), response]))
  parcel=next((v for k,v in fields.items() if re.search(r'(obręb|działka|nr działki)',k,re.I) and v), '')
  records.append(makeitem(key,title,date,current.get('url') or '',detail,author=author,response=response,summary=title,address=address,parcel=parcel,response_date=answer_date,response_url=current.get('responseUrl',''),source_catalog=url))
 for row in rp.rows:
  if len(row)<2:continue
  field_label=clean(row[0]['text']);value=clean(row[1]['text'])
  if (key=='petycje' and field_label.lower()=='numer') or (key!='petycje' and field_label.upper() in ('CRI','CRZ')):
   finish();current={'ident':field_label+' '+value,'fields':{},'url':'','responseUrl':''}
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

def post_json(url,payload):
 req=urllib.request.Request(url,data=json.dumps(payload,ensure_ascii=False).encode('utf-8'),headers={**HEADERS,'Content-Type':'application/json','Accept':'application/json'},method='POST')
 with urllib.request.urlopen(req,timeout=60) as resp:return json.loads(resp.read().decode('utf-8','replace'))
def cru_find(obj,aliases):
 wanted={re.sub(r'[^a-z0-9]','',k.lower()) for k in aliases}
 def walk(v):
  if isinstance(v,dict):
   for k,val in v.items():
    key=re.sub(r'[^a-z0-9]','',str(k).lower())
    if key in wanted and val is not None and str(val).strip():return val
   for val in v.values():
    found=walk(val)
    if found is not None:return found
  elif isinstance(v,list):
   for val in v:
    found=walk(val)
    if found is not None:return found
  return None
 return walk(obj)
def parse_cru():
 """Fetch public CRU records for JSFP entities whose name contains Gdańsk."""
 items=[];status={'source':'Centralny Rejestr Umów JSFP – Gdańsk','ok':False,'count':0,'url':'https://rejestrumow.gov.pl/','apiUrl':CRU_SEARCH,'note':'Publiczny, nieoficjalny endpoint tylko do odczytu; może zmienić format.'}
 try:
  offset=0;limit=50;max_pages=60;seen=set()
  query={'jsfp':{'nazwa':'GDAŃSK'}}
  for page in range(max_pages):
   url=CRU_SEARCH+'?'+urllib.parse.urlencode({'offset':offset,'limit':limit})
   payload=post_json(url,query)
   rows=payload.get('content',payload.get('results',payload.get('items',payload.get('agreements',[])))) if isinstance(payload,dict) else []
   if isinstance(rows,dict):rows=rows.get('content',rows.get('items',[]))
   if not isinstance(rows,list):raise RuntimeError('CRU response list shape not recognized')
   if not rows:break
   for row in rows:
    if not isinstance(row,dict):continue
    uid=cru_find(row,['idUmowy','agreementId','id'])
    if not uid or str(uid) in seen:continue
    seen.add(str(uid))
    subject=cru_find(row,['przedmiotUmowy','przedmiot','opisPrzedmiotuUmowy','nazwaUmowy']) or 'Umowa publiczna'
    number=cru_find(row,['numerUmowy','numer'])
    date=cru_find(row,['dataZawarciaUmowy','dataZawarcia','dataUmowy'])
    value=cru_find(row,['wartoscUmowy','wartoscPrzedmiotuUmowy','wartoscPrzedmiotu','kwota'])
    state=cru_find(row,['statusUmowy','status'])
    pub=cru_find(row,['dataPublikacji','dataOpublikowania'])
    details=' · '.join(filter(None,[('Nr '+str(number)) if number else '',('Wartość: '+str(value)) if value is not None else '',('Status: '+str(state)) if state else '',('Publikacja: '+str(pub)) if pub else '']))
    url_detail=CRU_DETAIL+urllib.parse.quote(str(uid))
    items.append(makeitem('umowy',str(subject),date,url_detail,details,summary=str(subject),source_catalog='https://rejestrumow.gov.pl/'))
   offset+=len(rows)
   if len(rows)<limit:break
  status.update({'ok':bool(items),'count':len(items),'note':status['note']+(' · Osiągnięto limit 3000 wyników, możliwa niepełność.' if len(items)>=limit*max_pages else '')})
 except Exception as exc:
  status.update({'ok':False,'count':len(items),'error':str(exc)[:220]})
 return items,status
def load_geocode_cache():
 try:return json.loads(GEOCODE_CACHE.read_text(encoding='utf-8'))
 except:return {}
def geocode_address(address):
 q=re.sub(r'\s+',' ',str(address or '')).strip()
 if not q or len(q)>100:return None
 url='https://nominatim.openstreetmap.org/search?'+urllib.parse.urlencode({'format':'jsonv2','limit':1,'country':'Polska','q':q+', Gdańsk, Polska'})
 try:
  data=json.loads(request(url,{'Accept-Language':'pl'}))
  if data and isinstance(data,list):
   return {'lat':round(float(data[0]['lat']),7),'lon':round(float(data[0]['lon']),7)}
 except Exception as exc:print('Address geocode failed:',q,str(exc)[:120])
 return None
def enrich_addresses(items):
 cache=load_geocode_cache();new=0;resolved=0
 candidates=sorted(items,key=lambda x:x.get('date',''),reverse=True)
 for item in candidates:
  if item.get('lat') not in (None,'') and item.get('lon') not in (None,''):continue
  address=str(item.get('address') or '').strip()
  if not address or len(address)>100 or not re.search(r'\d',address):continue
  key=re.sub(r'\s+',' ',address).casefold()
  if key not in cache and new<120:
   result=geocode_address(address)
   cache[key]=result or {'notFound':True}
   new+=1
   time.sleep(1.1)
  result=cache.get(key) or {}
  if result.get('lat') is not None:
   item.update(result);resolved+=1
 GEOCODE_CACHE.parent.mkdir(parents=True,exist_ok=True)
 GEOCODE_CACHE.write_text(json.dumps(cache,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Address locations:',resolved,'| cached addresses:',len(cache),'| new geocode requests:',new)
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
 cru_items,cru_status=parse_cru();allitems.extend(cru_items);status.append(cru_status)
 try:
  ckan_items,ckan_status=parse_ckan_finance();allitems.extend(ckan_items);status.append(ckan_status)
 except Exception as exc:status.append({'source':'Otwarty Gdańsk – CKAN (zbiory finansowe)','ok':False,'count':0,'error':str(exc)[:220],'url':'https://ckan.multimediagdansk.pl/dataset/?organization=um-gdansk&tags=finanse'})
 enrich_parcels(allitems)
 enrich_addresses(allitems)
 unique={x['id']:x for x in allitems}
 payload={'lastUpdated':datetime.now(timezone.utc).isoformat(),'items':list(unique.values()),'sourceStatus':status}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Fetched records:',len(unique));print(json.dumps(status,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
