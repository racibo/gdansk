import './style.css';

const DATA_URL='/data/latest.json';
const sourceLinks=[
 {key:'interpelacje',label:'Interpelacje radnych',group:'Rada miasta',url:'https://bip.gdansk.pl/rada-miasta/publikacja-interpelacji-radnych-miasta-gdanska',desc:'Pytania i postulaty radnych kierowane do prezydenta miasta.'},
 {key:'zapytania',label:'Zapytania radnych',group:'Rada miasta',url:'https://bip.gdansk.pl/rada-miasta/publikacja-zapytan-radnych-miasta-gdanska',desc:'Krótsze, konkretne pytania radnych oraz odpowiedzi urzędu.'},
 {key:'petycje',label:'Petycje',group:'Mieszkańcy',url:'https://bip.gdansk.pl/urzad-miejski/publikacja-petycji-do-rady-miasta-gdanska',desc:'Wnioski mieszkańców i sposób ich rozpatrzenia.'},
 {key:'decyzje',label:'Decyzje WUIA',group:'Inwestycje',url:'https://bip.gdansk.pl/urzad-miejski/raporty-i-publikacje/publikacja-decyzji-wuia',desc:'Decyzje urbanistyczne i architektoniczno-budowlane; źródłowe rekordy zawierają m.in. adresy i działki.'},
 {key:'zgloszenia',label:'Zgłoszenia budowlane',group:'Inwestycje',url:'https://bip.gdansk.pl/urzad-miejski/raporty-i-publikacje/publikacja-zgloszen-wuia',desc:'Zgłoszenia robót budowlanych, lokalizacje i inwestorzy.'},
 {key:'dzielnice',label:'Rady dzielnic',group:'Dzielnice',url:'https://bip.gdansk.pl/jednostki-pomocnicze',desc:'Wykaz rad dzielnic i ich dokumenty. Na razie katalog źródeł, bez automatycznego pobierania dokumentów.'},
 {key:'protokoly',label:'Protokoły sesji Rady Miasta',group:'Rada miasta',url:'https://bip.gdansk.pl/rada-miasta-gdanska/Protokoly-z-sesji-Rady-Miasta-Gdanska%2Ca%2C771',desc:'Protokoły sesji Rady Miasta, przydatne do sprawdzania przebiegu dyskusji i głosowań.'},
 {key:'otwarte',label:'Otwarte dane Gdańska',group:'Finanse i dane',url:'https://www.gdansk.pl/otwarte-dane-w-gdansku?show=byCategory',desc:'Punkt startowy do wyszukiwania zbiorów danych miejskich. Nie wszystkie zbiory są jeszcze zasilane do radaru.'},
 {key:'budzet',label:'Wieloletnia prognoza finansowa',group:'Finanse i dane',url:'https://www.gdansk.pl/urzad-miejski/2027-2051%2Ca%2C322561',desc:'WPF na lata 2027–2051: wieloletnie przedsięwzięcia, limity i planowanie finansowe.'},
 {key:'projekt-budzetu',label:'Projekt budżetu Gdańska 2027',group:'Finanse i dane',url:'https://media.gdansk.pl/komunikaty/879887/co-gdansk-zrobi-dla-ciebie-w-2027-roku',desc:'Projekt budżetu na 2027 rok i zapowiadane inwestycje; dane planowane, nie wykonanie budżetu.'},
 {key:'umowy',label:'Centralny Rejestr Umów JSFP',group:'Finanse i dane',url:'https://rejestrumow.gov.pl/',desc:'Publiczny rejestr umów jednostek sektora finansów publicznych.'},
 {key:'eko',label:'Środowisko i decyzje środowiskowe',group:'Środowisko',url:'https://www.gdansk.pl/ekologia',desc:'Informacje i publikacje dotyczące środowiska; zakres automatycznego pobierania wymaga osobnej integracji.'},
 {key:'prawo',label:'Uchwały i zarządzenia',group:'Prawo lokalne',url:'https://bip.gdansk.pl/prawo-lokalne',desc:'Akty prawa lokalnego i zarządzenia miasta.'}
];
let allItems=[],lastRun=null,sourceStatus=[],activeView='mapa',typeFilter='all',statusFilter='all',sortMode='newest',map=null,mapMarkers=[],mapReady=false;
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dateFmt=v=>{if(!v)return '—';const d=new Date(v);return isNaN(d)?esc(v):d.toLocaleDateString('pl-PL')};
const typeNames={interpelacje:'Interpelacja',zapytania:'Zapytanie',petycje:'Petycja',decyzje:'Decyzja administracyjna',zgloszenia:'Zgłoszenie budowlane'};
function statusInfo(item){
 const raw=[item.status,item.decisionStatus,item.description,item.title].join(' ').toLowerCase();
 if(/sprzeciw|odmow|negatywn|nie wyraż|nie udziel/.test(raw))return {key:'negative',label:'Negatywna / sprzeciw'};
 if(/pozytywn|udzielono pozwolen|zatwierdzono|wydano pozwolen/.test(raw))return {key:'positive',label:'Pozytywna'};
 if(/umorz/.test(raw))return {key:'closed',label:'Umorzenie'};
 if(/warunkow/.test(raw))return {key:'conditional',label:'Warunkowa'};
 if(/w toku|oczekuj|rozpatrywan/.test(raw))return {key:'pending',label:'W toku'};
 if(item.type==='decyzje')return {key:'unknown',label:'Wynik do weryfikacji'};
 if(item.type==='zapytania'||item.type==='interpelacje')return item.response?{key:'answered',label:'Jest odpowiedź'}:{key:'pending',label:'Brak wykrytej odpowiedzi'};
 return {key:'unknown',label:'Nieustalony'};
}
function districtName(item){return item.district||''}
function hasLocation(x){return Boolean(x.lat&&x.lon)||Boolean(x.address&&x.address.trim())}
function filteredItems(){
 const q=($('#search')?.value||'').toLocaleLowerCase('pl');
 let items=allItems.filter(x=>(typeFilter==='all'||x.type===typeFilter)&&(statusFilter==='all'||statusInfo(x).key===statusFilter)&&(!q||[x.title,x.description,x.author,x.address,x.parcel,x.investor,x.response,x.district].join(' ').toLocaleLowerCase('pl').includes(q)));
 return items.sort((a,b)=>sortMode==='oldest'?(a.date||'').localeCompare(b.date||''):(b.date||'').localeCompare(a.date||''));
}
function itemCard(x){
 const st=statusInfo(x),kind=typeNames[x.type]||x.category||'Dokument';
 return `<article class="record-card">
 <div class="record-meta"><span class="kind">${esc(kind)}</span><span class="status ${st.key}">${esc(st.label)}</span><span>${dateFmt(x.date)}</span></div>
 <h3>${esc(x.title||kind)}</h3><p class="record-description">${esc(x.summary||x.description||'W źródle nie ma krótkiego opisu. Otwórz dokument, aby sprawdzić szczegóły.')}</p>
 ${x.address?'<div class="location-line">⌖ '+esc(x.address)+(x.parcel?' · działka '+esc(x.parcel):'')+'</div>':''}
 ${x.author?'<div class="small-line">Autor / zgłaszający: '+esc(x.author)+'</div>':''}
 ${x.response?'<section class="answer"><b>Odpowiedź urzędu</b><p>'+esc(x.response)+'</p></section>':(x.type==='interpelacje'||x.type==='zapytania'?'<div class="small-line">Nie wykryto treści odpowiedzi w pobranych danych. Sprawdź dokument źródłowy.</div>':'')}
 <details><summary>Co oznaczają te informacje?</summary><p>${esc(x.explanation||technicalHelp(x))}</p>${x.decisionFinality?'<p><b>Ostateczność:</b> '+esc(x.decisionFinality)+'</p>':''}</details>
 <a class="source-link" href="${esc(x.url||'#')}" target="_blank" rel="noopener">Otwórz dokument / źródło urzędowe ↗</a></article>`;
}
function technicalHelp(x){
 if(x.type==='interpelacje')return 'Interpelacja to formalne wystąpienie radnego w sprawie o istotnym znaczeniu dla miasta. Sama interpelacja nie jest decyzją administracyjną ani poleceniem wykonania inwestycji.';
 if(x.type==='zapytania')return 'Zapytanie radnego służy uzyskaniu informacji w konkretnej sprawie. Odpowiedź urzędu wyjaśnia stanowisko lub przedstawia dane, ale sama w sobie nie musi oznaczać podjęcia działania.';
 if(x.type==='petycje')return 'Petycja to formalny wniosek w interesie publicznym, własnym lub innej osoby za jej zgodą. Jej złożenie nie oznacza, że urząd musi spełnić żądanie; powinien ją rozpatrzyć zgodnie z przepisami.';
 if(x.type==='decyzje')return 'Decyzja administracyjna rozstrzyga indywidualną sprawę. Trzeba odróżnić treść rozstrzygnięcia (np. pozwolenie lub odmowę) od tego, czy decyzja jest ostateczna i wykonalna.';
 if(x.type==='zgloszenia')return 'Zgłoszenie budowlane nie jest tym samym co pozwolenie na budowę. W określonych przypadkach roboty można rozpocząć, jeśli organ nie wniesie sprzeciwu w ustawowym terminie.';
 return 'To informacja z publicznego źródła. Jej skutki prawne zależą od rodzaju dokumentu i właściwych przepisów.';
}
function render(){
 const items=filteredItems(),counts={};
 allItems.forEach(x=>counts[x.type]=(counts[x.type]||0)+1);
 const answered=allItems.filter(x=>x.response).length;
 $('#app').innerHTML=`<header class="hero"><div class="wrap">
 <div class="brand"><div class="logo">⌁</div><div><h1>GDAŃSKI RADAR</h1><small>gdansk.racibo.pl · publiczne sprawy miasta w jednym miejscu</small></div></div>
 <p>Dokumenty, decyzje, inwestycje i pieniądze publiczne. Zobacz, czego dotyczą, gdzie mają miejsce i jakie mogą mieć znaczenie.</p>
 <div class="statusline"><span class="pill">Aktualizacja: ${lastRun?dateFmt(lastRun):'brak danych'}</span><a class="scan-button" href="https://github.com/racibo/gdansk/actions/workflows/monitor.yml" target="_blank" rel="noopener">↻ Uruchom skanowanie ↗</a></div></div></header>
 <main class="wrap main">
 <div class="stats"><div class="stat"><strong>${allItems.length}</strong><span>zebranych wpisów</span></div><div class="stat"><strong>${counts.decyzje||0}</strong><span>decyzji WUIA</span></div><div class="stat"><strong>${counts.zgloszenia||0}</strong><span>zgłoszeń budowlanych</span></div><div class="stat"><strong>${answered}</strong><span>odpowiedzi wykrytych w danych</span></div></div>
 <nav class="main-nav">${[['mapa','⌖ Mapa'],['katalog','☷ Katalog spraw'],['dzielnice','⌂ Dzielnice'],['finanse','▤ Finanse'],['wyjasnienia','? Jak to czytać']].map(([k,v])=>'<button data-view="'+k+'" class="'+(activeView===k?'active':'')+'">'+v+'</button>').join('')}</nav>
 <section class="view ${activeView==='mapa'?'visible':''}" id="view-mapa">
 <div class="section-head"><div><h2>Mapa spraw Gdańska</h2><p>Mapa pokazuje wyłącznie lokalizacje wynikające z danych lub potwierdzone geokodowaniem adresu.</p></div><span class="map-count">${allItems.filter(hasLocation).length} rekordów z informacją lokalizacyjną</span></div>
 <div class="map-layout"><div id="city-map" class="city-map"><div class="map-loading">Ładowanie mapy…</div></div><aside class="map-side"><h3>Warstwy i filtry</h3><label><input type="checkbox" id="map-invest" checked> Inwestycje i zgłoszenia</label><label><input type="checkbox" id="map-decisions" checked> Decyzje administracyjne</label><label><input type="checkbox" id="map-council" checked> Interpelacje, zapytania i petycje</label><p class="map-note">Nie każdy dokument ma adres. Wpis bez lokalizacji pozostaje w katalogu i nie otrzymuje sztucznego punktu na mapie.</p><div id="map-summary" class="map-summary"></div></aside></div>
 </section>
 <section class="view ${activeView==='katalog'?'visible':''}" id="view-katalog">
 <div class="section-head"><div><h2>Katalog spraw</h2><p>Wyszukuj, sortuj i filtruj według rodzaju dokumentu oraz rozstrzygnięcia.</p></div></div>
 <div class="filters"><input id="search" placeholder="Szukaj tematu, ulicy, radnego, działki…"><select id="type-filter"><option value="all">Wszystkie rodzaje</option>${Object.entries(typeNames).map(([k,v])=>'<option value="'+k+'">'+v+'</option>').join('')}</select><select id="status-filter"><option value="all">Każdy status</option><option value="positive">Pozytywna</option><option value="negative">Negatywna / sprzeciw</option><option value="conditional">Warunkowa</option><option value="closed">Umorzenie</option><option value="pending">W toku / brak odpowiedzi</option><option value="answered">Jest odpowiedź</option><option value="unknown">Nieustalony</option></select><select id="sort-filter"><option value="newest">Od najnowszych</option><option value="oldest">Od najstarszych</option></select></div>
 <div class="catalog-layout"><div id="record-list" class="record-list">${items.length?items.slice(0,200).map(itemCard).join(''):'<div class="empty">Brak wpisów pasujących do filtrów.</div>'}</div><aside class="panel catalog-side"><h3>Źródła i kompletność</h3>${sourceStatus.map(s=>'<div class="source-health"><b>'+(s.ok?'● ':'⚠ ')+esc(s.source)+'</b><small>'+esc(s.ok?'Pobrano: '+(s.count??0):s.error||s.note||'Źródło niedostępne')+'</small></div>').join('')||'<p>Brak raportu skanowania.</p>'}</aside></div>
 </section>
 <section class="view ${activeView==='dzielnice'?'visible':''}" id="view-dzielnice"><h2>Rady dzielnic i sprawy lokalne</h2><p>Rady dzielnic są ważnym źródłem informacji o potrzebach mieszkańców. Ich stanowiska i wnioski nie mają jednak automatycznie mocy wiążącej dla miasta.</p><div class="source-grid">${sourceLinks.filter(s=>s.group==='Dzielnice').map(sourceCard).join('')}<article class="info-card"><b>Jak interpretować stanowisko rady dzielnicy?</b><p>To głos lokalnej wspólnoty i formalny postulat lub opinia. Nie należy go oznaczać jako decyzji administracyjnej ani obietnicy realizacji.</p></article></div><p class="notice">Na tym etapie sekcja zawiera oficjalne źródło. Automatyczne pobieranie protokołów, uchwał i wniosków rad dzielnic jest kolejną integracją — nie udajemy, że te dokumenty są już zebrane.</p></section>
 <section class="view ${activeView==='finanse'?'visible':''}" id="view-finanse"><h2>Finanse, budżet i dofinansowania</h2><p>Finansowe dane miasta trzeba łączyć z konkretnymi projektami ostrożnie: plan budżetowy nie jest wydatkiem, a przyznane dofinansowanie nie zawsze oznacza wypłacone środki.</p><div class="source-grid">${sourceLinks.filter(s=>s.group==='Finanse i dane').map(sourceCard).join('')}</div><div class="glossary-grid"><article class="info-card"><b>Budżet</b><p>Plan dochodów i wydatków na dany rok. Nie jest równoznaczny z wykonaniem.</p></article><article class="info-card"><b>WPF</b><p>Wieloletnia prognoza finansowa. Pokazuje m.in. planowane przedsięwzięcia, okresy i limity wydatków.</p></article><article class="info-card"><b>Wykonanie</b><p>Informacja o rzeczywistych dochodach i wydatkach, zwykle publikowana w sprawozdaniach.</p></article><article class="info-card"><b>Dofinansowanie</b><p>Środki zewnętrzne przyznane na projekt. Warto rozróżnić kwotę przyznaną, zakontraktowaną i faktycznie otrzymaną.</p></article></div><p class="notice">Te źródła są obecnie katalogiem wejściowym, nie automatycznym monitoringiem. Integrację danych budżetowych, umów i dotacji trzeba dodać i zweryfikować osobno.</p></section>
 <section class="view ${activeView==='wyjasnienia'?'visible':''}"><h2>Jak czytać dokumenty urzędowe?</h2><p>Radar ma pomagać zrozumieć dokument, ale nie zastępuje jego treści ani porady prawnej.</p><div class="glossary-grid">
 <article class="info-card"><b>Interpelacja</b><p>Formalne wystąpienie radnego w sprawie o istotnym znaczeniu dla miasta. Nie jest decyzją ani nakazem wykonania prac.</p></article>
 <article class="info-card"><b>Zapytanie</b><p>Pytanie radnego w konkretnej sprawie. Odpowiedź może zawierać dane, stanowisko lub zapowiedź działania.</p></article>
 <article class="info-card"><b>Petycja</b><p>Wniosek w interesie publicznym lub własnym. Urząd ma obowiązek ją rozpatrzyć, ale nie musi spełnić żądania.</p></article>
 <article class="info-card"><b>Decyzja administracyjna</b><p>Formalne rozstrzygnięcie indywidualnej sprawy. Wynik i ostateczność decyzji to dwa różne zagadnienia.</p></article>
 <article class="info-card"><b>Sprzeciw do zgłoszenia</b><p>Organ może wnieść sprzeciw wobec zgłoszonych robót. Samo zgłoszenie nie jest pozwoleniem na budowę.</p></article>
 <article class="info-card"><b>Ostateczność</b><p>Co do zasady decyzja jest ostateczna, gdy nie przysługuje od niej odwołanie w administracyjnym toku instancji. To nie to samo co prawomocność.</p></article>
 <article class="info-card"><b>Wniosek / postulat</b><p>Prośba o podjęcie działania. Nie przesądza, że organ jest prawnie zobowiązany do jego wykonania.</p></article>
 <article class="info-card"><b>Odpowiedź urzędu</b><p>Ważne jest, czy zawiera konkretne zobowiązanie, termin, kwotę, odmowę, czy jedynie informację o stanie sprawy.</p></article>
 </div><h3>Jak oznaczamy statusy?</h3><div class="status-legend"><span class="status positive">Pozytywna</span><span class="status negative">Negatywna / sprzeciw</span><span class="status conditional">Warunkowa</span><span class="status closed">Umorzenie</span><span class="status pending">W toku</span><span class="status unknown">Nieustalony</span></div><p class="notice">Status jest automatycznie rozpoznawany tylko wtedy, gdy wynika z pobranych pól. W pozostałych przypadkach pokazujemy „nieustalony”, zamiast zgadywać. Ostateczność decyzji nie jest obecnie ustalana automatycznie.</p></section>
 <footer class="page-footer">Gdański Radar jest niezależnym projektem informacyjnym. Nie jest serwisem Urzędu Miejskiego. Dane mogą być niepełne lub zmienione przez publikujący urząd. Weryfikuj kluczowe informacje w oryginalnym dokumencie.</footer></main>`;
 document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{activeView=b.dataset.view;render();if(activeView==='mapa')initMap();}));
 $('#search')?.addEventListener('input',()=>{const node=$('#record-list');if(node)node.innerHTML=filteredItems().slice(0,200).map(itemCard).join('')||'<div class="empty">Brak wyników.</div>';});
 $('#type-filter')?.addEventListener('change',e=>{typeFilter=e.target.value;$('#record-list').innerHTML=filteredItems().slice(0,200).map(itemCard).join('')||'<div class="empty">Brak wyników.</div>';});
 $('#status-filter')?.addEventListener('change',e=>{statusFilter=e.target.value;$('#record-list').innerHTML=filteredItems().slice(0,200).map(itemCard).join('')||'<div class="empty">Brak wyników.</div>';});
 $('#sort-filter')?.addEventListener('change',e=>{sortMode=e.target.value;$('#record-list').innerHTML=filteredItems().slice(0,200).map(itemCard).join('')||'<div class="empty">Brak wyników.</div>';});
 if(activeView==='mapa')initMap();
}
function sourceCard(s){return '<article class="source-card"><span>'+esc(s.group)+'</span><b>'+esc(s.label)+'</b><p>'+esc(s.desc)+'</p><a href="'+esc(s.url)+'" target="_blank" rel="noopener">Otwórz źródło urzędowe ↗</a></article>'}
function loadLeaflet(){
 return new Promise((resolve,reject)=>{
  if(window.L){resolve();return;}
  if(!document.querySelector('#leaflet-css')){const l=document.createElement('link');l.id='leaflet-css';l.rel='stylesheet';l.href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';document.head.append(l);}
  const s=document.createElement('script');s.src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';s.onload=resolve;s.onerror=reject;document.head.append(s);
 });
}
async async function geocode(address){
 const key='gdansk-radar-geocode-v1';let cache={};try{cache=JSON.parse(localStorage.getItem(key)||'{}')}catch{}
 if(cache[address])return cache[address];
 try{const url='https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&country=Polska&city=Gdańsk&q='+encodeURIComponent(address+', Gdańsk');
 const res=await fetch(url,{headers:{'Accept-Language':'pl'}});if(!res.ok)return null;const rows=await res.json();if(!rows[0])return null;
 const point=[Number(rows[0].lat),Number(rows[0].lon)];cache[address]=point;try{localStorage.setItem(key,JSON.stringify(cache))}catch{}return point;
 }catch{return null;}
}
async function initMap(){
 if(!$('#city-map'))return;
 try{await loadLeaflet();}catch{$('#city-map').innerHTML='<div class="map-loading">Nie udało się załadować biblioteki mapy. Sprawdź połączenie internetowe.</div>';return;}
 if(!map){map=window.L.map('city-map').setView([54.352,18.646],12);window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'}).addTo(map);}
 setTimeout(()=>map.invalidateSize(),100);
 const visible=allItems.filter(hasLocation).slice(0,30),summary=$('#map-summary');if(summary)summary.textContent='Przygotowuję lokalizacje ('+visible.length+' rekordów maksymalnie na mapie)…';
 mapMarkers.forEach(m=>map.removeLayer(m));mapMarkers=[];
 for(let i=0;i<visible.length;i++){
  const item=visible[i];let point=(item.lat&&item.lon)?[Number(item.lat),Number(item.lon)]:await geocode(item.address);
  if(!point){if(summary)summary.textContent='Znaleziono lokalizacje dla '+mapMarkers.length+' z '+visible.length+' rekordów.';continue;}
  const st=statusInfo(item),color=st.key==='positive'?'#16834b':st.key==='negative'?'#c0392b':item.type==='decyzje'?'#2868b2':item.type==='zgloszenia'?'#8b5bb5':'#d18a22';
  const marker=window.L.circleMarker(point,{radius:8,color,fillColor:color,fillOpacity:.82,weight:2}).bindPopup('<b>'+esc(item.title)+'</b><br>'+esc(typeNames[item.type]||item.category)+' · '+esc(st.label)+'<br>'+esc(item.address||'')+'<br><a href="'+esc(item.url||'#')+'" target="_blank">Dokument źródłowy ↗</a>');
  marker.addTo(map);marker._radarType=item.type;mapMarkers.push(marker);
  if(i<visible.length-1)await new Promise(r=>setTimeout(r,1050));
 }
 const bounds=mapMarkers.map(m=>m.getLatLng());if(bounds.length>1)map.fitBounds(window.L.latLngBounds(bounds).pad(.12));
 if(summary)summary.textContent='Na mapie: '+mapMarkers.length+' lokalizacji. Punkty bez jednoznacznego adresu lub współrzędnych pozostają tylko w katalogu.';
 ['map-invest','map-decisions','map-council'].forEach(id=>{const el=$('#'+id);if(el)el.onchange=applyMapFilters;});
}
function applyMapFilters(){
 const groups={invest:['zgloszenia'],decisions:['decyzje'],council:['interpelacje','zapytania','petycje']};
 mapMarkers.forEach(m=>{const t=m._radarType,group=groups.invest.includes(t)?'invest':groups.decisions.includes(t)?'decisions':'council';const el=$('#map-'+group);if(el?.checked) m.addTo(map);else map.removeLayer(m);});
}
async function load(){try{const r=await fetch(DATA_URL+'?v='+Date.now());if(r.ok){const d=await r.json();allItems=d.items||[];lastRun=d.lastUpdated||null;sourceStatus=d.sourceStatus||[];}}catch(e){console.warn('Nie udało się pobrać danych',e);}render();}
load();
