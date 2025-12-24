# Excel Šabloni - DOMOVIK

## Struktura Budžet Projekta Šablona

**Fajl:** `budzet-projekta-sablon.xlsx`

### Sheet 1: Budžet Projekta

**Struktura tabele:**

| Red | Kategorija Troškova | Opis | Jedinična Cena (RSD) | Količina | Ukupno (RSD) |
|-----|---------------------|------|----------------------|----------|--------------|
| 1   | **Header**          |      |                      |          |              |
| 2   | Plate i naknade     | (primer) | (korisnik unosi) | (korisnik unosi) | =C2*D2 |
| 3   | Materijalni troškovi | (primer) | (korisnik unosi) | (korisnik unosi) | =C3*D3 |
| 4   | Usluge              | (primer) | (korisnik unosi) | (korisnik unosi) | =C4*D4 |
| 5-8 | (prazno za unos)    |      |                      |          | =C*D formule |
| **9** | **UKUPNO**        |      |                      |          | **=SUM(E2:E8)** |

### Ključne Karakteristike

- **Data redovi:** 2-8 (7 redova za budget entries)
- **UKUPNO red:** 9
- **SUM formula:** `=SUM(E2:E8)` (sumira sve data redove)
- **Zaštićene ćelije:** Kolona E (redovi 2-9) - korisnik ne može da obriše formule
- **Format:** .xlsx (Excel 2007+)

### Sheet 2: Uputstvo

Sadrži instrukcije za korisnike kako da popune budžet šablon.

## Kreiranje/Modifikacija Šablona

### Opcija 1: Ručno (Preporučeno za brze izmene)

1. Otvori `budzet-projekta-sablon.xlsx` u Microsoft Excel ili LibreOffice Calc
2. Napravi izmene direktno u fajlu
3. Sačuvaj kao .xlsx format
4. Pokreni testove: `python manage.py test apps.landing.tests.ExcelTemplateDownloadTests`

### Opcija 2: Programatski (Za automatsku verifikaciju)

Koristi `scripts/verify_excel_template.py` skript:

```bash
python scripts/verify_excel_template.py
```

**Šta skript radi:**
- Učitava postojeći Excel fajl (NE kreira novi od nule)
- Verifikuje strukturu (kolone, kategorije, formule)
- Ispravlja greške ako ih pronađe
- Dodaje zaštitu formula
- Verifikuje Uputstvo sheet

**NAPOMENA:** Skript **NE kreira novi fajl** ako ga nema. Mora postojati bazni Excel fajl.

## Testiranje

Pokreni unit testove za Excel šablon:

```bash
# Svi Excel testovi
python manage.py test apps.landing.tests.ExcelTemplateDownloadTests

# Specifičan test (npr. SUM formula)
python manage.py test apps.landing.tests.ExcelTemplateDownloadTests.test_excel_template_has_sum_formula
```

## Verzija i Kreiranje

- **Kreiran:** Story 1.1 (2025-12-23)
- **Verifikovan/Unapređen:** Story 1.2 (2025-12-24)
- **Trenutna verzija:** 1.0
- **File size:** 7398 bytes
