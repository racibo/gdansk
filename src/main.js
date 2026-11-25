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
 {key:'budzet-historyczny',label:'Budżet Gdańska – wybrane dane od 1990',group:'Finanse i dane',url:'https://ckan.multimediagdansk.pl/dataset/budzet-gdanska-wybrane-dane-od-1990',desc:'Zbiór otwartych danych o dochodach, wydatkach, wyniku finansowym, zadłużeniu i inwestycjach.'},
 {key:'rejestr-wydatkow',label:'Rejestr wydatków miasta',group:'Finanse i dane',url:'https://www.gdansk.pl/link/101647/rejestr-wydatkow',desc:'Miejski rejestr wydatków; źródło do weryfikacji wydatków i płatności.'},
 {key:'budzet',label:'Wieloletnia prognoza finansowa',group:'Finanse i dane',url:'https://www.gdansk.pl/urzad-miejski/2027-2051%2Ca%2C322561',desc:'WPF na lata 2027–2051: wieloletnie przedsięwzięcia, limity i planowanie finansowe.'},
 {key:'projekt-budzetu',label:'Projekt budżetu Gdańska 2027',group:'Finanse i dane',url:'https://media.gdansk.pl/komunikaty/879887/co-gdansk-zrobi-dla-ciebie-w-2027-roku',desc:'Projekt budżetu na 2027 rok i zapowiadane inwestycje; dane planowane, nie wykonanie budżetu.'},
 {key:'zmiany-budzetu',label:'Zmiany budżetu – zarządzenia Prezydenta',group:'Finanse i dane',url:'https://baw.bip.gdansk.pl/UrzadMiejskiwGdansku/document/568413/Zarz%C4%85dzenie',desc:'Oficjalne zarządzenie zmieniające plan budżetu 2026 wraz z tabelami zmian wydatków.'},
 {key:'umowy',label:'Centralny Rejestr Umów JSFP',group:'Finanse i dane',url:'https://rejestrumow.gov.pl/',desc:'Publiczny rejestr umów jednostek sektora finansów publicznych.'},
 {key:'eko',label:'Środowisko i decyzje środowiskowe',group:'Środowisko',url:'https://www.gdansk.pl/ekologia',desc:'Informacje i publikacje dotyczące środowiska; zakres automatycznego pobierania wymaga osobnej integracji.'},
 {key:'prawo',label:'Uchwały i zarządzenia',group:'Prawo lokalne',url:'https://bip.gdansk.pl/prawo-lokalne',desc:'Akty prawa lokalnego i zarządzenia miasta.'}
];
let allItems=[],lastRun=null,sourceStatus=[],activeView='mapa',typeFilter='all',statusFilter='all',sortMode='newest',map=null,mapMarkers=[],mapPoints=[],mapReady=false,locationQuery='';
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dateFmt=v=>{if(!v)return '—';const d=new Date(v);return isNaN(d)?esc(v):d.toLocaleDateString('pl-PL')};
const typeNames={interpelacje:'Interpelacja',zapytania:'Zapytanie',petycje:'Petycja',decyzje:'Decyzja administracyjna',zgloszenia:'Zgłoszenie budowlane',finanse:'Dokument finansowy'};
function statusInfo(item){
 const raw=[item.status,item.description,item.title].join(' ').toLowerCase();
 if(item.type==='decyzje'||item.type==='zgloszenia'){
  if(/sprzeciw|odmow|negatywn|nie wyraż/.test(raw))return {key:'negative',label:'Negatywna / sprzeciw'};
  if(/pozytywn|udzielono pozwolen|zatwierdzono|wydano pozwolen/.test(raw))return {key:'positive',label:'Pozytywna'};
  if(/umorz/.test(raw))return {key:'closed',label:'Umorzenie'};
  if(/warunkow/.test(raw))return {key:'conditional',label:'Warunkowa'};
  if(/w toku|oczekuj|rozpatrywan/.test(raw))return {key:'pending',label:'W toku'};
  return {key:'unknown',label:'Wynik do weryfikacji'};
 }
 if(item.type==='zapytania'||item.type==='interpelacje')return (item.response||item.responseDate||item.responseUrl)?{key:'answered',label:'Jest odpowiedź'}:{key:'pending',label:'Brak wykrytej odpowiedzi'};
 return {key:'unknown',label:'Nieustalony'};
}
function districtName(item){return item.district||''}
function hasLocation(x){return Boolean((x.lat!=null&&x.lon!=null&&x.lat!==''&&x.lon!==''&&Number.isFinite(Number(x.lat))&&Number.isFinite(Number(x.lon)))||(x.address&&x.address.trim())||(x.parcel&&x.parcel.trim()))}
function locationText(x){return [x.address,x.parcel,x.parcelId,x.title,x.description,x.summary,x.investor,x.author].filter(Boolean).join(' ').toLocaleLowerCase('pl')}
function locationSnippet(x){const q=locationQuery.trim().toLocaleLowerCase('pl');const source=String(x.description||x.summary||'');const lower=source.toLocaleLowerCase('pl');const at=q?lower.indexOf(q):-1;if(at<0)return source.slice(0,240);const from=Math.max(0,at-100),to=Math.min(source.length,at+q.length+140);return (from?'…':'')+source.slice(from,to)+(to<source.length?'…':'');}
function sourceLinkMarkup(x,compact=false){
 const direct=String(x.url||'').trim();
 if(direct&&direct!=='#')return '<a class="'+(compact?'':'source-link')+'" href="'+esc(direct)+'" target="_blank" rel="noopener">Otwórz konkretny dokument ↗</a>';
 const catalog=x.sourceCatalog|| (x.type==='decyzje'?'https://bip.gdansk.pl/urzad-miejski/raporty-i-publikacje/publikacja-decyzji-wuia':x.type==='zgloszenia'?'https://bip.gdansk.pl/urzad-miejski/raporty-i-publikacje/publikacja-zgloszen-wuia':'');
 return '<span class="no-direct-link">Źródło nie udostępnia osobnego pliku dla tej pozycji — publikuje ją w wykazie danych.'+(catalog?' <a href="'+esc(catalog)+'" target="_blank" rel="noopener">Otwórz wykaz źródłowy ↗</a>':'')+'</span>';
}
function locationMatches(){const q=locationQuery.trim().toLocaleLowerCase('pl');if(!q)return [];return allItems.filter(x=>locationText(x).includes(q)).sort((a,b)=>(b.date||'').localeCompare(a.date||''));}
function renderLocationResults(){const node=$('#location-results');if(!node)return;const q=locationQuery.trim();if(!q){node.innerHTML='<p class="location-hint">Wpisz ulicę i numer, nazwę miejsca albo numer działki (np. obręb 0024, działka 391/10). Radar przeszuka wszystkie pobrane oficjalne dokumenty.</p>';return;}const found=locationMatches();node.innerHTML=found.length?'<p class="location-result-count">Znaleziono '+found.length+' dokumentów powiązanych z wpisaną lokalizacją.</p>'+found.slice(0,60).map(x=>'<article class="location-result"><div class="record-meta"><span class="kind">'+esc(typeNames[x.type]||x.category||'Dokument')+'</span><span>'+dateFmt(x.date)+'</span></div><b>'+esc(x.title||'Dokument urzędowy')+'</b><p>'+esc(x.address||'Lokalizacja z danych działki')+(x.parcel?' · działka '+esc(x.parcel):'')+'</p><p class="location-snippet">'+esc(locationSnippet(x))+'</p>'+sourceLinkMarkup(x,true)+'</article>').join(''):'<p class="location-hint">Nie znaleziono jeszcze dokumentu z takim zapisem lokalizacji. Spróbuj krótszej nazwy ulicy, samego numeru działki lub numeru obrębu.</p>';}
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
 ${x.response?'<section class="answer"><b>Odpowiedź urzędu</b><p>'+esc(x.response)+'</p></section>':(x.responseDate||x.responseUrl?'<section class="answer"><b>Odpowiedź urzędu</b><p>'+(x.responseDate?'Data odpowiedzi: '+esc(dateFmt(x.responseDate)):'W źródle wykryto odnośnik do odpowiedzi.')+(x.responseUrl?' · <a href="'+esc(x.responseUrl)+'" target="_blank" rel="noopener">Otwórz odpowiedź ↗</a>':'')+'</p></section>':(x.type==='interpelacje'||x.type==='zapytania'?'<div class="small-line">Nie wykryto odpowiedzi w pobranych polach. Sprawdź dokument źródłowy.</div>':''))}
 ${x.type==='finanse'&&x.description&&x.description.includes('DANE Z ARKUSZA')?'<details><summary>Podgląd danych z arkusza</summary><pre class="source-data">'+esc(x.description.slice(x.description.indexOf('DANE Z ARKUSZA'),x.description.indexOf('DANE Z ARKUSZA')+18000))+'</pre></details>':''}
 <details><summary>Co oznaczają te informacje?</summary><p>${esc(x.explanation||technicalHelp(x))}</p>${x.decisionFinality?'<p><b>Ostateczność:</b> '+esc(x.decisionFinality)+'</p>':''}</details>
 ${sourceLinkMarkup(x)}</article>`;
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
 if(map){map.remove();map=null;mapMarkers=[];}
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
 <div class="map-layout"><div id="city-map" class="city-map"><div class="map-loading">Ładowanie mapy…</div></div><aside class="map-side"><h3>Warstwy i filtry</h3><label><input type="checkbox" id="map-invest" checked> Zgłoszenia budowlane</label><label><input type="checkbox" id="map-decisions" checked> Decyzje administracyjne</label><label><input type="checkbox" id="map-council" checked> Interpelacje, zapytania i petycje</label><label><input type="checkbox" id="map-finance" checked> Finanse i umowy</label><p class="map-note">Radar rozpoznaje adresy oraz identyfikatory działek. Działki są lokalizowane przez usługę ULDK GUGiK; adresy bez współrzędnych są geokodowane. Dokument bez pewnej lokalizacji pozostaje w wynikach wyszukiwania.</p><div id="map-summary" class="map-summary"></div></aside></div>
 </section>
 <section class="view ${activeView==='katalog'?'visible':''}" id="view-katalog">
 <div class="section-head"><div><h2>Katalog spraw</h2><p>Wyszukuj, sortuj i filtruj według rodzaju dokumentu oraz rozstrzygnięcia.</p></div></div>
 <div class="filters"><input id="search" placeholder="Szukaj tematu, ulicy, radnego, działki…"><select id="type-filter"><option value="all">Wszystkie rodzaje</option>${Object.entries(typeNames).map(([k,v])=>'<option value="'+k+'">'+v+'</option>').join('')}</select><select id="status-filter"><option value="all">Każdy status</option><option value="positive">Pozytywna</option><option value="negative">Negatywna / sprzeciw</option><option value="conditional">Warunkowa</option><option value="closed">Umorzenie</option><option value="pending">W toku / brak odpowiedzi</option><option value="answered">Jest odpowiedź</option><option value="unknown">Nieustalony</option></select><select id="sort-filter"><option value="newest">Od najnowszych</option><option value="oldest">Od najstarszych</option></select></div>
 <div class="catalog-layout"><div id="record-list" class="record-list">${items.length?items.slice(0,200).map(itemCard).join(''):'<div class="empty">Brak wpisów pasujących do filtrów.</div>'}</div><aside class="panel catalog-side"><h3>Źródła i kompletność</h3>${sourceStatus.map(s=>'<div class="source-health"><b>'+(s.ok?'● ':'⚠ ')+esc(s.source)+'</b><small>'+esc(s.ok?'Pobrano: '+(s.count??0):s.error||s.note||'Źródło niedostępne')+'</small></div>').join('')||'<p>Brak raportu skanowania.</p>'}</aside></div>
 </section>
 <section class="view ${activeView==='dzielnice'?'visible':''}" id="view-dzielnice"><h2>Rady dzielnic i sprawy lokalne</h2><p>Rady dzielnic są ważnym źródłem informacji o potrzebach mieszkańców. Ich stanowiska i wnioski nie mają jednak automatycznie mocy wiążącej dla miasta.</p><div class="source-grid">${sourceLinks.filter(s=>s.group==='Dzielnice').map(sourceCard).join('')}<article class="info-card"><b>Jak interpretować stanowisko rady dzielnicy?</b><p>To głos lokalnej wspólnoty i formalny postulat lub opinia. Nie należy go oznaczać jako decyzji administracyjnej ani obietnicy realizacji.</p></article></div><p class="notice">Na tym etapie sekcja zawiera oficjalne źródło. Automatyczne pobieranie protokołów, uchwał i wniosków rad dzielnic jest kolejną integracją — nie udajemy, że te dokumenty są już zebrane.</p></section>
 <section class="view ${activeView==='finanse'?'visible':''}" id="view-finanse"><h2>Finanse, budżet i dofinansowania</h2><p>Finansowe dane miasta trzeba łączyć z konkretnymi projektami ostrożnie: plan budżetowy nie jest wydatkiem, a przyznane dofinansowanie nie zawsze oznacza wypłacone środki.</p><div class="source-grid">${sourceLinks.filter(s=>s.group==='Finanse i dane').map(sourceCard).join('')}</div><h3>Dokumenty finansowe wykryte w oficjalnych źródłach (${allItems.filter(x=>x.type==='finanse').length})</h3><div class="record-list finance-records">${allItems.filter(x=>x.type==='finanse').sort((a,b)=>(b.date||'').localeCompare(a.date||'')).map(itemCard).join('')||'<p class="notice">Dokumenty pojawią się po zakończeniu skanowania źródeł finansowych.</p>'}</div><div class="glossary-grid"><article class="info-card"><b>Budżet</b><p>Plan dochodów i wydatków na dany rok. Nie jest równoznaczny z wykonaniem.</p></article><article class="info-card"><b>WPF</b><p>Wieloletnia prognoza finansowa. Pokazuje m.in. planowane przedsięwzięcia, okresy i limity wydatków.</p></article><article class="info-card"><b>Wykonanie</b><p>Informacja o rzeczywistych dochodach i wydatkach, zwykle publikowana w sprawozdaniach.</p></article><article class="info-card"><b>Dofinansowanie</b><p>Środki zewnętrzne przyznane na projekt. Warto rozróżnić kwotę przyznaną, zakontraktowaną i faktycznie otrzymaną.</p></article></div><p class="notice">Radar pobiera metadane oficjalnych publikacji budżetowych i WPF oraz linki do wykrytych załączników. Kolejnym krokiem jest pełne parsowanie tabel z plików PDF/XLSX, aby można było łączyć konkretne wydatki z lokalizacjami. Kwoty z projektu budżetu są planem, a nie wykonaniem.</p></section>
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
 document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{activeView=b.dataset.view;render();}));
 $('#search')?.addEventListener('input',()=>{const node=$('#record-list');if(node)node.innerHTML=filteredItems().slice(0,200).map(itemCard).join('')||'<div class="empty">Brak wyników.</div>';});
 $('#type-filter')?.addEventListener('change',e=>{typeFilter=e.target.value;$('#record-list').innerHTML=filteredItems().slice(0,200).map(itemCard).join('')||'<div class="empty">Brak wyników.</div>';});
 $('#status-filter')?.addEventListener('change',e=>{statusFilter=e.target.value;$('#record-list').innerHTML=filteredItems().slice(0,200).map(itemCard).join('')||'<div class="empty">Brak wyników.</div>';});
 $('#sort-filter')?.addEventListener('change',e=>{sortMode=e.target.value;$('#record-list').innerHTML=filteredItems().slice(0,200).map(itemCard).join('')||'<div class="empty">Brak wyników.</div>';});
 if(activeView==='mapa'){renderLocationResults();$('#location-search')?.addEventListener('input',e=>{locationQuery=e.target.value;renderLocationResults();});initMap();}
}
function sourceCard(s){return '<article class="source-card"><span>'+esc(s.group)+'</span><b>'+esc(s.label)+'</b><p>'+esc(s.desc)+'</p><a href="'+esc(s.url)+'" target="_blank" rel="noopener">Otwórz źródło urzędowe ↗</a></article>'}
function loadLeaflet(){
 return new Promise((resolve,reject)=>{
  if(window.L){resolve();return;}
  if(!document.querySelector('#leaflet-css')){const l=document.createElement('link');l.id='leaflet-css';l.rel='stylesheet';l.href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';document.head.append(l);}
  const s=document.createElement('script');s.src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';s.onload=resolve;s.onerror=reject;document.head.append(s);
 });
}
async function geocode(address){
 const key='gdansk-radar-geocode-v1';let cache={};try{cache=JSON.parse(localStorage.getItem(key)||'{}')}catch{}
 if(cache[address])return cache[address];
 try{const url='https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&country=Polska&q='+encodeURIComponent(address+', Gdańsk, Polska');
 const res=await fetch(url,{headers:{'Accept-Language':'pl'}});if(!res.ok)return null;const rows=await res.json();if(!rows[0])return null;
 const point=[Number(rows[0].lat),Number(rows[0].lon)];cache[address]=point;try{localStorage.setItem(key,JSON.stringify(cache))}catch{}return point;
 }catch{return null;}
}
function mapItemEnabled(item){
 const type=item.type;
 if(type==='zgloszenia')return $('#map-invest')?.checked!==false;
 if(type==='decyzje')return $('#map-decisions')?.checked!==false;
 if(['interpelacje','zapytania','petycje'].includes(type))return $('#map-council')?.checked!==false;
 if(type==='finanse'||type==='umowy')return $('#map-finance')?.checked!==false;
 return true;
}
function renderMapLayers(){
 if(!map)return;
 mapMarkers.forEach(m=>map.removeLayer(m));mapMarkers=[];
 const bounds=map.getBounds(),zoom=map.getZoom();
 const visible=mapPoints.filter(p=>mapItemEnabled(p.item)&&bounds.contains(p.point));
 const cell=zoom<=11?0.012:zoom<=13?0.004:zoom<=14?0.0015:0;
 const groups=new Map();
 for(const p of visible){
  const key=cell?Math.floor(p.point[0]/cell)+':'+Math.floor(p.point[1]/cell):p.item.id;
  if(!groups.has(key))groups.set(key,[]);
  groups.get(key).push(p);
 }
 for(const group of groups.values()){
  const lat=group.reduce((s,p)=>s+p.point[0],0)/group.length;
  const lon=group.reduce((s,p)=>s+p.point[1],0)/group.length;
  const count=group.length,first=group[0].item;
  const color=first.type==='decyzje'?'#2868b2':first.type==='zgloszenia'?'#8b5bb5':first.type==='finanse'?'#167b70':'#d18a22';
  const radius=count>1?Math.min(22,9+Math.log2(count)*3):7;
  const body=count>1?'<b>'+count+' spraw w tym obszarze</b><p>Przybliż mapę, aby zobaczyć poszczególne lokalizacje.</p>'+group.slice(0,8).map(p=>'<div class="map-popup-item"><b>'+esc(p.item.title||'Dokument')+'</b><br><small>'+esc(p.item.address||p.item.parcel||'')+'</small></div>').join(''):'<b>'+esc(first.title||'Dokument')+'</b><br>'+esc(typeNames[first.type]||first.category||'Dokument')+' · '+esc(statusInfo(first).label)+'<br>'+esc(first.address||first.parcel||'')+'<br>'+sourceLinkMarkup(first,true);
  const marker=window.L.circleMarker([lat,lon],{radius,color,fillColor:color,fillOpacity:.78,weight:2}).bindPopup(body);
  if(count>1)marker.on('click',()=>{map.setView([lat,lon],Math.min(18,zoom+2));});
  marker.addTo(map);mapMarkers.push(marker);
 }
 const summary=$('#map-summary');
 if(summary){
  const total=allItems.filter(x=>mapItemEnabled(x)&&hasLocation(x)).length;
  const unlocated=allItems.filter(x=>mapItemEnabled(x)&&!hasLocation(x)).length;
  summary.textContent='Widoczne na mapie: '+visible.length+' lokalizacji w '+groups.size+' obszarach. W całym zbiorze: '+mapPoints.length+' punktów z pozycją; '+Math.max(0,total-mapPoints.length)+' rekordów czeka na ustalenie współrzędnych; '+unlocated+' rekordów bez danych lokalizacyjnych.';
 }
}
async function initMap(){
 if(!$('#city-map'))return;
 try{await loadLeaflet();}catch{$('#city-map').innerHTML='<div class="map-loading">Nie udało się załadować biblioteki mapy. Sprawdź połączenie internetowe.</div>';return;}
 map=window.L.map('city-map').setView([54.352,18.646],11);
 window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'}).addTo(map);
 setTimeout(()=>map.invalidateSize(),100);
 // Filtry działają od razu — nie czekają na wolne geokodowanie adresów.
 // Delegated filter handler: remains attached even when view markup is rebuilt.
 if($('#app')&&!$('#app').dataset.mapFilterHandler){$('#app').dataset.mapFilterHandler='1';$('#app').addEventListener('change',e=>{if(['map-invest','map-decisions','map-council','map-finance'].includes(e.target?.id))renderMapLayers();});}
 map.on('zoomend moveend',renderMapLayers);
 mapPoints=allItems.filter(x=>x.lat!=null&&x.lon!=null&&x.lat!==''&&x.lon!==''&&Number.isFinite(Number(x.lat))&&Number.isFinite(Number(x.lon))).map(item=>({item,point:[Number(item.lat),Number(item.lon)]}));
 renderMapLayers();
 // Dodatkowe adresy są rozpoznawane w tle, z limitem i cache. Mapa oraz filtry pozostają responsywne.
 const candidates=allItems.filter(x=>!(x.lat!=null&&x.lon!=null&&x.lat!==''&&x.lon!=='')&&x.address&&/\d/.test(x.address)).slice(0,80);
 for(let i=0;i<candidates.length;i++){
  const item=candidates[i];
  const point=await geocode(item.address);
  if(point){mapPoints.push({item,point});if(i%3===0)renderMapLayers();}
  if(i<candidates.length-1)await new Promise(r=>setTimeout(r,1050));
 }
 renderMapLayers();
}
function applyMapFilters(){renderMapLayers();}
async function load(){try{const r=await fetch(DATA_URL+'?v='+Date.now());if(r.ok){const d=await r.json();allItems=d.items||[];lastRun=d.lastUpdated||null;sourceStatus=d.sourceStatus||[];}}catch(e){console.warn('Nie udało się pobrać danych',e);}render();}
load();
