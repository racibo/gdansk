# Gdański Radar

**gdansk.racibo.pl** — niezależny monitoring publicznych danych miejskich.

## Widoki aplikacji

- **Lokalizacja jako główny punkt wejścia** — wyszukiwarka przyjmuje adres, ulicę, obręb i numer działki; przeszukuje tytuły, opisy i pola lokalizacyjne wszystkich zebranych dokumentów. Mapa wykorzystuje współrzędne działek pozyskane z usługi ULDK GUGiK oraz geokodowanie adresów Nominatim / OpenStreetMap. Dla części rekordów lokalizacja może pozostać nierozpoznana; wyszukiwarka tekstowa nadal pokaże dokument.
- **Katalog spraw** — wyszukiwanie, filtrowanie po typie i statusie, sortowanie chronologiczne.
- **Dzielnice** — katalog oficjalnych źródeł rad dzielnic. Dokumenty nie są jeszcze automatycznie pobierane.
- **Finanse** — automatycznie indeksowane publikacje WPF, projekt budżetu i wybrane zarządzenia zmieniające budżet. Sekcja zawiera też umowy z Gdańska pobierane z publicznego, nieoficjalnego endpointu tylko do odczytu CRU JSFP. Pełne wydobywanie wszystkich tabel PDF/XLSX i łączenie ich z konkretnymi lokalizacjami jest dalszym etapem.
- **Wyjaśnienia** — słownik podstawowych pojęć i objaśnienie statusów.

## Automatycznie pobierane źródła

- Interpelacje radnych (BIP; Picklock API)
- Zapytania radnych (BIP; Picklock API)
- Petycje (BIP; Picklock API)
- Decyzje WUIA (otwarty JSON)
- Zgłoszenia budowlane WUIA (otwarty JSON)
- Centralny Rejestr Umów JSFP – publiczny endpoint wyszukiwania, JSFP z nazwą GDAŃSK (od 1.07.2026; interfejs nieoficjalny, może się zmienić)

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

Workflow uruchamia się codziennie o 03:20 UTC, po zmianach w `src/**`, `scripts/**` lub samym workflow oraz ręcznie na żądanie. Lokalizowanie działek korzysta z ULDK GUGiK; wyniki są zapisywane w `public/data/parcel_cache.json`. Adresy dokumentów geokoduje kolektor przez Nominatim, z trwałym cache `public/data/geocode_cache.json` i limitem 120 nowych zapytań na skan. Adresy z treści interpelacji/zapytań/petycji są wyszukiwane w tytułach i odpowiedziach, a testy regresji sprawdzają ekstrakcję ulic. Przed pobraniem danych sprawdza build Vite, składnię Pythona i testy kolektora.

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
