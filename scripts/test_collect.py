#!/usr/bin/env python3
"""Regression tests for Gdansk Radar collector helpers."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import collect

cases=[
 ("Interpelacja: na ulicy Kartuskiej 12 planowany remont chodnika","ul. Kartuskiej 12"),
 ("Przy ul. Długi Targ 2 zostanie wymieniona nawierzchnia","ul. Długi Targ 2"),
 ("Budowa przy al. Grunwaldzkiej 100","al. Grunwaldzkiej 100"),
 ("Zieleń przy Placu Solidarności","pl. Solidarności"),
 ("Brak wskazanego adresu w tym dokumencie",""),
]
for source,expected in cases:
 got=collect.extract_explicit_address(source)
 if got!=expected:raise AssertionError(f"{source!r}: expected {expected!r}, got {got!r}")
assert collect.cru_find({"wartośćUmowy":"123,45"},["wartoscUmowy"])=="123,45"
assert collect.cru_find({"idUmowy":"uuid"},["idUmowy"])=="uuid"
print("Address and CRU field tests passed.")
