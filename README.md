# Gdański Radar

**gdansk.racibo.pl** — niezależny monitoring publicznych danych miejskich.

## Widoki aplikacji

- **Mapa spraw** — adresy z rekordów WUIA i innych źródeł są lokalizowane jako punkty. Dla adresów bez współrzędnych przeglądarka może skorzystać z geokodowania Nominatim / OpenStreetMap; wyniki są zapamiętywane lokalnie. Mapa nie przypisuje punktu sprawom bez wiarygodnego adresu. Obecna wersja nie zawiera jeszcze granic dzielnic ani geometrii działek.
- **Katalog spraw** — wyszukiwanie, filtrowanie po typie i statusie, sortowanie chronologiczne.
- **Dzielnice** — katalog oficjalnych źródeł rad dzielnic. Dokumenty nie są jeszcze automatycznie pobierane.
- **Finanse** — oficjalne wejścia do danych otwartych, WPF, projektu budżetu i rejestru umów. To katalog źródeł, nie zintegrowany rejestr wydatków.
- **Wyjaśnienia** — słownik podstawowych pojęć i objaśnienie statusów.

## Automatycznie pobierane źródła

- Interpelacje radnych (BIP; Picklock API)
- Zapytania radnych (BIP; Picklock API)
- Petycje (BIP; Picklock API)
- Decyzje WUIA (otwarty JSON)
- Zgłoszenia budowlane WUIA (otwarty JSON)

Kolektor normalizuje rekordy do `public/data/latest.json`. Pola `status` i `response` są uzupełniane tylko wtedy, gdy odpowiednie informacje są obecne w pobranych danych. Automatyczna klasyfikacja statusu jest orientacyjna; w razie braku danych interfejs pokazuje „nieustalony”. Ostateczność decyzji administracyjnej nie jest obecnie ustalana automatycznie.

## Źródła katalogowe (jeszcze bez automatycznego importu)

- Rady dzielnic: https://bip.gdansk.pl/jednostki-pomocnicze
- Protokoły Rady Miasta: https://bip.gdansk.pl/rada-miasta-gdanska/Protokoly-z-sesji-Rady-Miasta-Gdanska%2Ca%2C771
- Otwarte dane Gdańska: https://www.gdansk.pl/otwarte-dane-w-gdansku
- WPF 2027–2051: https://www.gdansk.pl/urzad-miejski/2027-2051%2Ca%2C322561
- Projekt budżetu 2027: https://media.gdansk.pl/komunikaty/879887/co-gdansk-zrobi-dla-ciebie-w-2027-roku
- Centralny Rejestr Umów JSFP: https://rejestrumow.gov.pl/
- Środowisko: https://www.gdansk.pl/ekologia

## Automatyzacja i ręczne skanowanie

Workflow uruchamia się po zmianach w `src/**`, `scripts/**` lub samym workflow oraz ręcznie na żądanie. Przed pobraniem danych sprawdza build Vite i składnię kolektora Pythona.

Ręczny skan: https://github.com/racibo/gdansk/actions/workflows/monitor.yml

## Lokalnie

```bash
npm install
npm run dev
npm run build
python -m py_compile scripts/collect.py
```

## Netlify

- Build: `npm run build`
- Publish: `dist`
- Domena: `gdansk.racibo.pl`

## Zastrzeżenie

Radar nie jest oficjalną stroną miasta. Streszczenia i klasyfikacje pomagają przeglądać dokumenty, ale nie zastępują oryginalnego dokumentu ani oceny prawnej. Dane mogą być niepełne, opóźnione lub zmienione przez publikujący urząd.
