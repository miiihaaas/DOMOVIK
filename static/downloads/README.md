# Obrazac budžeta — DOMOVIK

**Fajl:** `budzet-obrazac.xlsx`
**Izvor:** klijentov dokument `docs/Budzet_obrazac.xlsx` (Z6, 2026-07-25)

Jedan obrazac se koristi za **oba** tipa prijave — Projekat (COA) i Inicijativa (COB).
Preuzima se sa početne strane (`templates/landing/home.html`) i iz Sekcije III obe forme.

> ⚠️ Ovaj fajl **nije generisan kodom**. To je dokument koji je dostavio klijent.
> Ranije skripte `scripts/create_budget_template.py` i `scripts/verify_excel_template.py`
> su obrisane upravo zato što bi pregazile ovaj fajl pri pokretanju.

## Struktura

Jedan sheet: **`Budžet šablon`**

| Red | Sadržaj |
|-----|---------|
| 7 | `Naziv tima:` (unos ide u `B7`) |
| 12 | Zaglavlje: Troškovi / Jedinica / Količina / Jedinična cena (EUR) / Ukupan budžet (EUR) / Opis troškova |
| 13–18 | 1. Putni troškovi (A) — stavke 14–17, međuzbir `E18 = SUM(E14:E17)` |
| 19–24 | 2. Materijali, oprema i promotivni proizvodi (B) — stavke 20–23, međuzbir `E24` |
| 25–31 | 3. Organizacija aktivnosti i događaja (C) — stavke 26–30, međuzbir `E31` |
| 32–38 | 4. Spoljne usluge i ostali troškovi (D) — stavke 33–37, međuzbir `E38` |
| 39 | Ukupni troškovi `E39 = E18+E24+E31+E38` |
| 41–42 | Napomene o okvirnim cenama |

Svaki red sa stavkom ima `E{red} = C{red}*D{red}`. Prva stavka u svakoj kategoriji je
popunjen primer (prevoz, majice, osveženje, honorar moderatora).

## Zaštita ćelija

Sheet je zaštićen (**bez lozinke**), tako da:

- **kolona E je zaključana** — korisnik ne može obrisati formule;
- **kolone A, B, C, D i F u redovima sa stavkama su otključane**, kao i `B7`;
- formatiranje ćelija/redova/kolona je dozvoljeno, izmena strukture nije.

Ako je potrebno **dodati redove**, sheet se skida sa zaštite kroz Excel:
*Review → Unprotect Sheet* (ne traži lozinku).

## Izmena obrasca

1. Zameni `docs/Budzet_obrazac.xlsx` novom verzijom od klijenta.
2. Ponovo primeni zaštitu ćelija:
   ```bash
   venv/bin/python scripts/protect_budget_template.py
   ```
   Skripta čita `docs/Budzet_obrazac.xlsx` i upisuje `static/downloads/budzet-obrazac.xlsx`.
   Radi direktno nad XML-om u .xlsx arhivi — **ne koristi openpyxl za ponovni upis**, jer
   briše ugrađeni logo (`xl/media/image1.jpeg`), print podešavanja i `customXml` delove.
   Ako klijent promeni raspored redova, ažuriraj konstante na vrhu skripte.
3. Pokreni testove:
   ```bash
   venv/bin/python manage.py test apps.landing.tests.ExcelTemplateDownloadTests --keepdb
   ```
   Oni proveravaju sheet, zaglavlje, sve formule, zaštitu i prisustvo logotipa.
4. `venv/bin/python manage.py collectstatic --noinput` i restart gunicorn-a.

## Napomena o sadržaju

Prazne stavke u obrascu su nazvane `1.2 ???????`, `2.3 ??????` itd. — tako ih je
dostavio klijent (nije greška enkodiranja). Ostavljeno namerno, po dogovoru.
