# DOMOVIK – Plan izmena na osnovu testiranja platforme

**Datum:** 2026-07-24
**Autor analize:** Claude (code review celog codebase-a + provera produkcione baze)
**Status:** ČEKA ODOBRENJE (nije implementirano)

---

## 0. Kako je rađena analiza

Pregledani su: `apps/submissions` (models, forms, views, services, tasks, admin, validators,
constants), `apps/landing`, svi templejti, svi JS fajlovi, `config/settings.py`, `.env`,
`django-cpanel-deploy-uputstvo.md`, `upustvo.md`, `media/`, kao i **stvarno stanje baze**
(30 prijava, FileMetadata i ClanTima zapisi).

Svaki nalaz ispod ima dokaz iz koda ili baze — nema pretpostavki.

---

## 1. NALAZI (root cause analiza)

### N1 – Broj lične karte / ID broj se traži na 2 mesta
Polje se u bazi zove `Applicant.jmbg` (naziv zadržan zbog kompatibilnosti), a u UI je
"Broj lične karte / ID broj". Obavezno je i za COA i za COB, za fizička lica.

Tačke u kodu: `forms.py` (COAFormSectionI.jmbg + clean_jmbg + clean; COBApplicantForm.id_broj
+ clean_id_broj + clean), `validators.validate_id_broj`, `services.process_submission`,
`views.submit_cob`, `coa_form.html:80-90`, `cob_form.html:76-81`,
`submission-handler.js`, `draft-manager.js`, `real-time-validator.js`,
`section-navigation.js:309`, `services.PDFGenerationService` (JMBG red u PDF-u),
`politika-privatnosti.html:39`, `uslovi-koristenja.html:47`, ~30 test asertacija.

### N2 – Email potvrda se ne šalje (2 nezavisna uzroka)

**Uzrok A – lokalno/dev:** u `.env` stoji
`EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` → mejl se samo ispisuje u konzoli.

**Uzrok B – produkcija:** mejlovi se šalju isključivo preko Celery-ja
(`send_confirmation_email.delay(...)`). Na cPanel-u nema Redis-a, broker je MySQL
(`django-cpanel-deploy-uputstvo.md`, sekcija 10). Ako Celery worker nije živ, task se
upiše u red i **nikad se ne izvrši** — korisnik dobije "poslato", a mejl ne postoji.
Dodatni čest uzrok: Office365 (`smtp.office365.com`) po defaultu ima **isključen SMTP AUTH**
za nalog, pa `email.send()` puca i posle 4 pokušaja odustaje (vidljivo samo u
`logs/email_tasks.log` i `logs/celery.log`).

Ekran uspeha (`success.html:46-76`) bezuslovno tvrdi da je mejl poslat i nudi dugme
"Pošalji email ponovo" — što u ovom stanju samo ponavlja neuspeh.

### N3 – Članovi tima se UOPŠTE ne čuvaju (kritično)

**Dokaz iz baze:** `ClanTima.objects.count() == 0` uz 30 prijava.

Uzrok: `static/js/submission-handler.js` → `collectFormData()` **nikad ne dodaje**
`team_members` u payload, iako:
- `team-members.js` ima `TeamMembersManager.getTeamMembersData()`,
- `draft-manager.js:256` ih uredno čuva u draft,
- backend (`views.submit_application:434` i `views.submit_cob:786`) ih uredno čita i snima.

Drugi problem: i da stignu, **admin panel ih nigde ne prikazuje** — `ClanTima` nije
registrovan u `admin.py` niti postoji inline na `ApplicationAdmin`.

Treći problem: sekcija "Ostali članovi tima" je u templejtu unutar `#fizicko-fields`,
pa je pravna lica uopšte ne vide.

### N4 – Fajlovi COB prijava se ne mogu otvoriti iz admina (kritično)

**Dokaz iz baze:**

| Prijava | Kategorija | `original_filename` | `stored_filename` |
|---|---|---|---|
| COB-2026-009 | BUDZET_INICIJATIVE | `prekoracena_zaduzenja (2).xlsx` | `prekoracena_zaduzenja (2).xlsx` ❌ |
| COA-2026-006 | BUDGET | `prekoracena_zaduzenja.xlsx` | `20260124_160401_1e539040_prekoracena_zaduzenja.xlsx` ✅ |

Uzrok: `file-upload-handler.js:565` → `stored_filename: file.filename` (šalje se **originalno**
ime, jer `/upload/` endpoint u odgovoru uopšte ne vraća pravo ime na disku).
- **COA** je slučajno ispravan: `views.submit_application:410-420` ignoriše ono što šalje
  frontend i gradi metapodatke iz `UploadedFile` tabele.
- **COB** nije: `views.submit_cob:776` veruje frontendu → `stored_filename` je pogrešan →
  `views.download_file` traži fajl na disku po tom imenu i vraća 404
  ("Fajl nije pronađen na serveru").

Dakle: **nije problem u formatu fajla, nego u imenu pod kojim se traži.** Zato "neki fajlovi"
rade (COA), a "neki ne" (COB).

Prateći problemi:
- Fajlovi se nikad fizički ne premeštaju iz `media/uploads/drafts/` u
  `media/submissions/<kategorija>/` — radi samo zahvaljujući fallback-u u `views.py:1442`.
- Stare prijave imaju ukinute kategorije (`OPIS_INICIJATIVE`, `PISMO_NAMERE`) kojih nema u
  `FILE_CATEGORY_FOLDERS`.
- Admin ne signalizira da fajl fali — vidi se tek posle klika na Download.

### N5 – Admin panel ne prikazuje deo podataka iz prijave

Nedostaje u `get_fieldsets()` (`admin.py:402-496`), iako postoji u bazi:

| Podatak | Model | COA | COB |
|---|---|---|---|
| Datum startovanja / završetka | ProjectData / InitiativeData | ❌ | ❌ |
| Naziv tima | InitiativeData.naziv_tima | – | ❌ |
| Totalni budžet (EUR) | InitiativeData.totalni_budzet | – | ❌ |
| Članovi tima | ClanTima | ❌ | ❌ |
| Datum kreiranja | Application.created_at | ❌ | ❌ |

Dodatno:
- `get_project_totalni_budzet` prikazuje **"RSD"**, a platforma svuda koristi **EUR**
  (`forms.py:272` "Totalni budžet (EUR)", PDF potvrda kaže EUR). Nekonzistentno.
- `FileMetadataInline.get_category_serbian` (`admin.py:99-106`) koristi ključeve
  `BUDZET`/`BIOGRAFIJA` kojih nema u `constants.FileType` (tamo je `BUDGET`/`BIOGRAPHY`) →
  COA fajlovi se prikazuju kao sirovi kod. Isti dict ima i duplirani ključ `PISMO_PODRSKE`.
- `get_applicant_jmbg.short_description = 'JMBG'` i `get_applicant_maticni_broj = 'Matični broj'`
  — stari nazivi.
- `InitiativeDataAdmin.readonly_fields` ne pokriva nova polja (naziv_tima, datumi, budžet) →
  ta polja su u adminu editabilna, iako sve ostalo nije.

### N6 – Obrazac budžeta

**Trenutno na platformi:** `static/downloads/budzet-projekta-sablon.xlsx` (7,5 KB), generisan
skriptom `scripts/create_budget_template.py`. Sadržaj: 2 sheeta, kolone u **RSD**, generičke
kategorije (Plate/Materijalni/Usluge), UKUPNO `=SUM(E2:E8)`.

**Klijentov obrazac:** `docs/Budzet_obrazac.xlsx` (38,7 KB). Provereno `openpyxl`-om:
- 1 sheet: `Budžet šablon`, validan .xlsx (Excel 2007+), 4 merge-ovane ćelije
- red 7: `Naziv tima:`; zaglavlje u redu 12 (Troškovi / Jedinica / Količina / Jedinična cena (EUR) / Ukupan budžet (EUR) / Opis troškova)
- 4 sekcije (A–D) sa primerima i međuzbirovima: `=SUM(E14:E17)`, `=SUM(E20:E23)`, `=SUM(E26:E30)`, `=SUM(E33:E37)`
- ukupno: red 39 `=E18+E24+E31+E38`
- napomene u redovima 41–42
- sheet nije zaključan (formule se mogu obrisati)

**Zaključak o formatu:** ✅ format je adekvatan. `.xlsx` je na whitelist-i
(`settings.ALLOWED_FILE_EXTENSIONS`), MIME `...spreadsheetml.sheet` je dozvoljen, 38 KB je
daleko ispod limita od 10 MB. Valuta EUR se poklapa sa ostatkom platforme (za razliku od
postojećeg RSD šablona).

**Ali:** u adminu se Excel **ne prikazuje** — postoji samo Download dugme. I to trenutno ne
radi za COB prijave (vidi N4). Znači: obrazac je OK, ali bez ispravke N4 klijent ni ovaj fajl
neće moći da otvori iz admina.

**Odgovor na pitanje "generisati ili držati fajl u repou":** držati klijentov fajl u repou.
Generisanje skriptom je bilo opravdano dok obrasca nije bilo; sada je to samo dodatni kod koji
može da razbije klijentov layout. Skripte se penzionišu, fajl se menja prostom zamenom.

---

## 2. ZADACI (prioritizovano)

| # | Zadatak | Prioritet | Procena |
|---|---|---|---|
| Z1 | Ispraviti download COB fajlova (N4) + popraviti postojeće zapise | 🔴 P0 | 4h |
| Z2 | Članovi tima: poslati ih sa fronta i prikazati u adminu (N3) | 🔴 P0 | 3h |
| Z3 | Izbaciti Broj LK / ID broj za fizička lica (N1) | 🟠 P1 | 4h |
| Z4 | ~~Isključiti slanje mejla + ukloniti poruku sa ekrana uspeha (N2)~~ | ⏸️ ODLOŽENO | 2h |
| Z5 | Dopuniti admin detaljni prikaz (N5) | 🟠 P1 | 3h |
| Z6 | Zameniti obrazac budžeta klijentovim (N6) | 🟡 P2 | 2h |
| Z7 | Dijagnostika mejla na produkciji (Celery + Office365) | 🟡 P2 | 1–3h |
| Z8 | Zajednički prolaz kroz admin panel | 🟡 P2 | 1h |

---

## 3. PLAN IZMENA

### Z1 – Download fajlova (COB)

**Princip:** backend nikad ne veruje imenu fajla koje pošalje browser.

1. `views.submit_cob` – umesto `data.get('files')`, graditi metapodatke iz `UploadedFile`
   tabele za tekuću sesiju (identično kao COA na `views.py:402-420`). Klijentska lista se
   koristi samo za validaciju broja/kategorija.
2. `views.upload_file` – u JSON odgovor dodati `stored_filename` (koristan i za draft).
   `file-upload-handler.js` – čuvati ga u registry i slati.
3. `services.py` – nova funkcija `resolve_stored_file_path(file_metadata)`, redosled
   pretrage: (a) povezani `UploadedFile.file_path`, (b) `media/submissions/<folder>/`,
   (c) `media/uploads/drafts/`. Koriste je `download_file` i `download_all_files`
   (uklanja se dupliran kod).
4. `constants.FILE_CATEGORY_FOLDERS` – dodati legacy ključeve `OPIS_INICIJATIVE`,
   `PISMO_NAMERE`.
5. **Popravka postojećih podataka:** management komanda
   `python manage.py fix_file_metadata` koja za svaki `FileMetadata` sa nevalidnim
   `stored_filename` nađe odgovarajući `UploadedFile` (ista prijava + kategorija +
   `original_filename`) i upiše ispravno ime. Pokreće se sa `--dry-run` prvo.
6. `FileMetadataInline` – nova readonly kolona "Status fajla": ✅ dostupan / ⚠️ nedostaje.
7. Za PDF fajlove dodati i link "Otvori u pregledaču" (`as_attachment=False`), da admin ne
   mora da skida svaki dokument.

**Fajlovi:** `apps/submissions/views.py`, `services.py`, `constants.py`, `admin.py`,
`static/js/file-upload-handler.js`, nova `apps/submissions/management/commands/fix_file_metadata.py`

### Z2 – Članovi tima

1. `static/js/submission-handler.js` → `collectFormData()`: dodati
   `submissionData.team_members = TeamMembersManager.getTeamMembersData()` (uz guard ako
   manager nije učitan). Važi za COA i COB.
2. `templates/submissions/coa_form.html` i `cob_form.html`: sekciju "Ostali članovi tima"
   izmestiti iz `#fizicko-fields` u zajednički deo forme *(pod uslovom da se odobri —
   vidi Otvoreno pitanje P1)*.
3. `admin.py`: novi `ClanTimaInline(admin.TabularInline)` — readonly, bez add/delete,
   dodat u `ApplicationAdmin.inlines`.
4. `ApplicationAdmin.get_queryset()`: `prefetch_related('clanovi_tima')`.
5. `list_display`: kolona "Članovi tima" (broj).
6. Backend već validira; dodati `validate_phone_optional` na serverskoj strani pri snimanju
   (sada se veruje frontendu).

### Z3 – Uklanjanje Broja LK / ID broja (fizička lica)

Polje se **ne briše iz baze** (`Applicant.jmbg` ostaje, nullable) da bi se sačuvale postojeće
prijave; samo se prestaje sa prikupljanjem i prikazom. Bez migracije.

| Sloj | Izmena |
|---|---|
| `forms.py` | ukloniti `jmbg` iz `COAFormSectionI.Meta.fields`/labels/help_texts, `clean_jmbg()`, i proveru u `clean()`; ukloniti `id_broj` + `clean_id_broj()` + proveru iz `COBApplicantForm` |
| `views.py` | `submit_cob`: skloniti `jmbg=applicant_data.get('id_broj')` |
| `services.py` | `process_submission`: skloniti `validate_id_broj(...)` i `jmbg=...`; iz PDF potvrde skloniti red "JMBG" |
| `coa_form.html` | obrisati blok linija 80–90 |
| `cob_form.html` | obrisati blok linija 76–81 |
| `submission-handler.js` | skloniti `applicant.jmbg` |
| `draft-manager.js` | skloniti `jmbg`/`id_broj` iz draft objekta, restore-a i liste validacije |
| `real-time-validator.js` | skloniti `validateJMBG`, `handleJMBGValidation`, poruku i registraciju polja |
| `section-navigation.js` | skloniti `{ id: 'id_jmbg', label: 'JMBG' }` iz obaveznih polja |
| `admin.py` | skloniti `get_applicant_jmbg` iz fieldsets-a i readonly liste |
| `politika-privatnosti.html` / `uslovi-koristenja.html` | uskladiti tekst (bez JMBG-a) — GDPR obaveza |
| testovi | ažurirati ~30 asertacija (`test_forms.py`, `tests.py`, `test_api.py`, `test_cob_submission.py`, `test_services.py`, admin testovi) |

`validate_id_broj` ostaje u `validators.py` (neškodljivo) ili se briše zajedno sa testovima —
predlog: ostaviti, radi lakšeg vraćanja ako se predomislite.

**Registracioni broj za pravna lica se NE dira** (nije bio deo zahteva).

### Z4′ – Sinhroni mejl + cron ✅ IMPLEMENTIRANO (2026-07-24)

**Dijagnoza (Z7, obavljeno):** produkcija je VPS `91.107.234.61` (nginx+gunicorn,
`/var/www/domovik`), NE cPanel. Celery worker mrtav od 2026-06-03; broker je `sqla+mysql`
pa `.delay()` tiho upisuje zadatke u red koji niko ne prazni. **SMTP je ispravan** —
direktan `send_mail` prolazi i mejl stiže. Isti uzrok oborio i GDPR brisanje draftova.

**Urađeno:**
1. `tasks.py` refaktorisan: logika izdvojena u obične funkcije
   `_deliver_confirmation_email` / `_deliver_admin_notification`; Celery task-ovi zadržani kao
   tanki wrapper-i (async put i dalje radi ako se worker ikad vrati); dodati sinhroni
   `send_confirmation_email_now` / `send_admin_notification_now` koji **nikad ne bacaju
   izuzetak** (neuspeh mejla ne obara prijavu).
2. `views.py`: sva 3 mesta (`submit_application`, `submit_cob`, `resend_email`) prešla sa
   `.delay()` na sinhrone pozive. COB i dalje kroz `transaction.on_commit` (mejl samo ako je
   prijava commit-ovana). `resend_email` sada vraća stvarni ishod (502 ako slanje padne).
3. Periodični zadaci → management komande + cron:
   `apps/submissions/management/commands/delete_old_drafts.py` (podržava `--dry-run`),
   `cleanup_old_admin_logs.py`. `tasks.py` ih zove kroz `purge_expired_drafts` /
   `purge_old_admin_logs`.
4. Test `test_email_confirmation_triggered` usklađen (patch → `send_confirmation_email_now`,
   `captureOnCommitCallbacks`).

**Provereno lokalno:** `manage.py check` čist; sinhrono slanje COA+COB radi (console backend);
`delete_old_drafts --dry-run` → 11 draftova čeka brisanje (potvrda da GDPR cleanup nije radio);
task-level testovi notifikacija (12) prolaze. Preostali test error-i su postojeći (ratelimit IP
u test klijentu, zastareli Story 5.4 file-count testovi) — nevezani za ovu izmenu, potvrđeno
`git stash` baseline poređenjem.

**Preostalo na serveru (ručno, uz deploy):**
- `.env`: `SITE_URL=https://prijave.domovik.org` (sada goli IP → admin linkovi pogrešni).
- `crontab -e`:
  ```
  0 2 * * * cd /var/www/domovik && venv/bin/python manage.py delete_old_drafts >> logs/maintenance.log 2>&1
  0 3 1 * * cd /var/www/domovik && venv/bin/python manage.py cleanup_old_admin_logs >> logs/maintenance.log 2>&1
  ```
- Ukloniti stare cPanel cron linije za `start_celery.sh` (gađaju nepostojeći fajl).

<details>
<summary>Prethodni plan Z4 (gašenje mejla) — NAPUŠTEN jer je SMTP ispravan</summary>

Umesto brisanja koda, uvode se prekidači u `settings.py` (paljenje = jedna linija u `.env`):

```python
SEND_APPLICANT_CONFIRMATION_EMAIL = config('SEND_APPLICANT_CONFIRMATION_EMAIL', default=False, cast=bool)
SEND_ADMIN_NOTIFICATION_EMAIL     = config('SEND_ADMIN_NOTIFICATION_EMAIL',     default=True,  cast=bool)
```

1. `views.submit_application` i `views.submit_cob` – pozivi `.delay()` iza `if settings...`.
2. `views.resend_email` – ako je flag isključen, vraća 503 sa jasnom porukom.
3. `templates/submissions/success.html` – ukloniti blok `.email-info` (linije 46–55) i dugme
   "Pošalji email ponovo" (69–75). Umesto toga: naglasak na referentnom broju + PDF potvrdi
   i rečenica "Sačuvajte referentni broj i preuzmite PDF potvrdu."
4. `static/js/success-handler.js` – ukloniti resend logiku.
5. `views.success_screen` – `applicant_email` više nije potreban u kontekstu.

</details>

### Z5 – Dopuna admin prikaza

1. `get_fieldsets()`:
   - COA sekcija: + `datum_startovanja`, `datum_zavrsetka`
   - COB sekcija: + `naziv_tima` (prvo polje), `datum_startovanja`, `datum_zavrsetka`,
     `totalni_budzet`
   - Opšti podaci: + `created_at`
2. `get_project_totalni_budzet` – **RSD → EUR**; isto uskladiti `ProjectData.total_budget.help_text`
   i `forms.py:287`.
3. `FileMetadataInline.get_category_serbian` – ispraviti ključeve na `BUDGET`, `BIOGRAPHY`,
   `SUPPORT_LETTER`, `BUDZET_INICIJATIVE`, `PISMO_PODRSKE` (+ legacy) i ukloniti duplikat.
4. `get_applicant_jmbg` / `get_applicant_maticni_broj` – ispraviti nazive kolona
   (prvo se briše u Z3, drugo → "Registracioni broj").
5. `InitiativeDataAdmin.readonly_fields` – dodati nova polja.
6. `admin.py` – `list_display` proširiti kolonom sa brojem članova tima i brojem dokumenata.

### Z6 – Obrazac budžeta

1. `docs/Budzet_obrazac.xlsx` → `static/downloads/budzet-projekta-sablon.xlsx`
   (ime fajla ostaje isto → URL, landing templejt i deo testova se ne diraju).
2. Obrisati `scripts/create_budget_template.py`; `scripts/verify_excel_template.py` prilagoditi
   novoj strukturi ili obrisati.
3. `static/downloads/README.md` – prepisati: opis nove strukture (sekcije A–D, međuzbirovi,
   ukupno u redu 39, EUR) + uputstvo "novi obrazac = prosto zameniti fajl i pokrenuti testove".
4. `apps/landing/tests.py` – prilagoditi `ExcelTemplateDownloadTests`
   (`test_excel_template_structure`, `test_excel_template_has_sum_formula`) novoj strukturi:
   sheet `Budžet šablon`, zaglavlje u redu 12, ukupno u redu 39. Testovi postojanja fajla,
   `.xlsx` validnosti i download linka ostaju.
5. `python manage.py collectstatic` posle deploy-a.
6. Preporuka (opciono): zaključati kolonu E (formule) da korisnici ne obrišu proračun —
   isto što je radio stari šablon.

### Z7 – Dijagnostika mejla na produkciji (posle Z4, zasebno)

Redosled provere preko SSH-a:
```bash
ps aux | grep celery                      # da li worker uopšte radi
tail -50 ~/prijave.domovik.org/logs/celery.log
tail -50 ~/prijave.domovik.org/logs/email_tasks.log
python manage.py shell -c "from django.core.mail import send_mail; send_mail('Test','Test','noreply@domovik.org',['miiihaaas@gmail.com'])"
```
Ako direktan `send_mail` puca → problem je SMTP (Office365 SMTP AUTH / lozinka / SPF-DKIM).
Ako `send_mail` prolazi a mejl iz forme ne stiže → problem je Celery worker/broker.
Kao trajno rešenje predlažem **sinhrono slanje sa timeout-om** za potvrdu prijave
(mejl je kratak, jedan SMTP poziv), a Celery zadržati samo za periodične zadatke — time
nestaje cela klasa "task u redu koji niko ne izvršava".

### Z8 – Zajednički prolaz kroz admin panel

Posle Z1–Z5, prolazak kroz listu prijava, detaljni prikaz, filtere, download dokumenata i
promenu statusa; beležimo dodatne zahteve kao novu iteraciju.

---

## 4. REDOSLED IMPLEMENTACIJE

```
Faza 0 (odmah, bez koda): Z7 dijagnostika  (klijent proverava Celery/SMTP na serveru)
Faza 1 (P0):              Z1 → Z2          (podaci se gube / nisu dostupni)
Faza 2 (P1):              Z3 → Z5
Faza 3 (P2):              Z6 → Z8
Z4 samo ako Z7 pokaže da mejl nije rešiv.
```

Posle svake faze: `python manage.py test`, ručni smoke test (COA i COB, fizičko i pravno lice),
zatim commit.

---

## 5. RIZICI

| Rizik | Ublažavanje |
|---|---|
| Popravka `stored_filename` na postojećim zapisima | `--dry-run` režim + backup baze pre pokretanja |
| Draftovi u localStorage sadrže polje ID broj | `draft-manager.js` ignoriše nepoznata polja; stari draftovi ostaju validni |
| Testovi masovno padaju posle Z3 | Z3 se radi u jednom commit-u zajedno sa ažuriranjem testova |
| Klijentov Excel bez zaštite formula | Opciono zaključavanje kolone E (Z6, tačka 6) |
| Izmena Excel testova prikriva regresiju | Zadržati provere: fajl postoji, validan .xlsx, ima SUM formulu, link ima `download` |

---

## 6. ODLUKE KLIJENTA (2026-07-24)

- **P1 – Članovi tima:** ✅ vidljivi i **fizičkim i pravnim licima**. Sekcija se izmešta iz
  `#fizicko-fields` u zajednički deo forme (COA i COB).
- **P2 – Mejlovi:** ⏸️ **ništa se ne menja** dok se ne proveri da li Celery worker radi
  (Z7). Z4 ostaje kao rezervni plan.
- **P3 – Obrazac budžeta:** ✅ **jedan obrazac** za projekte i inicijative, kao i sada.
- **P4 – Registracioni broj:** ✅ **ostaje obavezan** za pravna lica. Uklanja se samo Broj
  lične karte / ID broj za fizička lica.
