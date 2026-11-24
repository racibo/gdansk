# Gdański Radar

**gdansk.racibo.pl** — niezależny monitoring publicznych danych miejskich.

## MVP źródła
- Interpelacje radnych (BIP)
- Zapytania radnych (BIP)
- Decyzje administracyjne WUIA (JSON open data)
- Zgłoszenia budowlane WUIA (JSON open data)
- Wyszukiwanie, filtrowanie i podgląd odnośników do źródeł

## Status danych
Interpelacje i zapytania są stronami BIP, których listy mogą być generowane dynamicznie. Pierwsza wersja skanera próbuje wykrywać linki dokumentów, ale **nie gwarantuje kompletności** tych dwóch źródeł. Decyzje i zgłoszenia WUIA pobierane są bezpośrednio z JSON publikowanych przez miasto.

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
- [Zgłoszenia budowlane](https://bip.gdansk.pl/urzad-miejski/raporty-i-publikacje/publikacja-zgloszen-wuia)

## Zastrzeżenie
Radar nie jest oficjalną stroną miasta. Służy do odkrywania dokumentów; informacje weryfikuj w źródłach pierwotnych.