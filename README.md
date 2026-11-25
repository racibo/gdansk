# Gdański Radar

**gdansk.racibo.pl** — niezależny monitoring publicznych danych miejskich.

## MVP źródła
- Interpelacje radnych (BIP)
- Zapytania radnych (BIP)
- Petycje do Rady Miasta (BIP)
- Uchwały i zarządzenia (link do Bazy Aktów Własnych – bez pobierania danych na tym etapie)
- Decyzje administracyjne WUIA (JSON open data)
- Zgłoszenia budowlane WUIA (JSON open data)
- Wyszukiwanie, filtrowanie i podgląd odnośników do źródeł

## Status danych
Interpelacje, zapytania i petycje są parsowane z tabel HTML BIP. Skrypt pobiera przedmioty spraw, daty i autorów, jeśli są widoczne w strukturze HTML. **Kompletność wymaga walidacji skanem** — część BIP może renderować dane dynamicznie. Uchwały i zarządzenia są obecnie dodane jako oficjalny link do Bazy Aktów Własnych, bez automatycznego pobierania.

## Automatyzacja i ręczne skanowanie
Plik `public/data/latest.json` generuje `scripts/collect.py`. GitHub Actions obsługuje skanowanie na żądanie. Na stronie znajduje się bezpośredni link do [GitHub Actions](https://github.com/racibo/gdansk/actions/workflows/monitor.yml). Po jego otwarciu wybierz workflow „Monitor Gdansk public data”, kliknij **Run workflow**, pozostaw branch `main` i zatwierdź przyciskiem **Run workflow**. Po zakończeniu zadania dane zostaną zapisane w repozytorium, a Netlify wdroży aktualizację. Nie jest potrzebny żaden token ani konfiguracja sekretów w Netlify.

## Lokalnie
```bash
npm install
npm run dev
npm run build
```

## Netlify
- Build: `npm run build`
- Publish: `dist`
- Domena: `gdansk.racibo.pl`

## Źródła
- [Interpelacje radnych](https://bip.gdansk.pl/rada-miasta/publikacja-interpelacji-radnych-miasta-gdanska)
- [Zapytania radnych](https://bip.gdansk.pl/rada-miasta/publikacja-zapytan-radnych-miasta-gdanska)
- [Decyzje WUIA](https://bip.gdansk.pl/urzad-miejski/raporty-i-publikacje/publikacja-decyzji-wuia)
- [Petycje](https://bip.gdansk.pl/urzad-miejski/publikacja-petycji-do-rady-miasta-gdanska)
- [Uchwały i zarządzenia](https://bip.gdansk.pl/prawo-lokalne)
- [Zgłoszenia budowlane](https://bip.gdansk.pl/urzad-miejski/raporty-i-publikacje/publikacja-zgloszen-wuia)

## Zastrzeżenie
Radar nie jest oficjalną stroną miasta. Służy do odkrywania dokumentów; informacje weryfikuj w źródłach pierwotnych.