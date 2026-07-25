# Politika privatnosti i Uslovi korišćenja — predlog izmena

Dokument za DOMOVIK, 25.07.2026.

Ovo je odgovor na pitanja iz mejla o politici privatnosti i uslovima korišćenja. Proverili
smo **svaku tvrdnju iz predloženog teksta u odnosu na to šta platforma zapravo radi.**

Dve stranice o kojima je reč:

- https://prijave.domovik.org/politika-privatnosti/
- https://prijave.domovik.org/uslovi-koristenja/

---

## Ukratko

Većina tvrdnji iz predloženog teksta je bila **tačna, ili je u međuvremenu postala tačna** —
tri stvari koje tekst obećava nisu radile, i one su ispravljene u platformi 25.07.2026:

| Tvrdnja | Pre 25.07. | Sada |
|---|---|---|
| Upload-ovani fajlovi nisu dostupni javnosti | ❌ bio je dostupan svakome sa linkom | ✅ samo prijavljeni administrator |
| Kolačići zaštićeni na HTTPS-u | ⚠️ bez `Secure` oznake | ✅ ispravljeno |
| Draft podaci se brišu posle 7 dana | ⚠️ tekst da, priloženi fajlovi ne | ✅ i fajlovi se brišu |
| Redovni dnevni backup, 30 dana | ❌ nije postojao | ✅ svake noći u 01:00 |
| Evidencija datih saglasnosti | ❌ nije se čuvala | ✅ čuva se uz vreme i verziju politike |
| Bez trećih strana | ⚠️ fontovi su se učitavali sa Google servera | ✅ sa našeg servera |

**Ostaju dve stvari koje ne možemo da rešimo bez vaše odluke** — one su ispod, označene kao
ODLUKA 1 i ODLUKA 2, plus spisak podataka koji nam trebaju.

---

# ODLUKA 1 — Tvrdnja o enkripciji baze podataka

**Gde se nalazi:** Politika privatnosti, sekcija **4.2 Zaštita na serveru**, druga stavka
(u vašem predlogu i u tekstu koji je sada na sajtu).

### Sada piše

> **Enkripcija baze podataka:** Podaci se čuvaju u MySQL bazi podataka uz naprednu AES-256
> enkripciju podataka u mirovanju.

### Problem

**Ovo trenutno nije tačno.** Proverili smo bazu na serveru: enkripcija podataka u mirovanju
nije uključena, niti je disk servera enkriptovan. Podaci su zaštićeni na druge načine
(opisane ispod), ali ne enkripcijom.

Ovakvu tvrdnju ne smemo objaviti dok ne bude istinita — ako neko ikada proveri, to je
netačna izjava u zvaničnom dokumentu.

### Mogućnost A — ispraviti tekst *(preporučujemo)*

Zamenili bismo tu jednu stavku ovim:

> **Zaštićen pristup bazi podataka:** Baza podataka nije izložena internetu — dostupna je
> isključivo lokalno, sa samog servera aplikacije, preko posebnog naloga sa ograničenim
> pravima. Podacima mogu pristupiti samo ovlašćeni administratori.

Ostale tri stavke u sekciji 4.2 ostaju kako su i **sve su tačne:** SSL/TLS enkripcija u
prenosu, redovni dnevni backup sa čuvanjem 30 dana, i pristup ograničen na ovlašćene
administratore.

**Zašto ovo preporučujemo:** prava enkripcija baze u ovom slučaju donosi malo stvarne
zaštite. Ključ za dešifrovanje mora da stoji na istom serveru kao i baza — ko dođe do
servera, došao je i do ključa. Enkripcija štiti prvenstveno od krađe samog diska ili backup
fajla, što nije glavni rizik ovde. Uloženo vreme se bolje isplati na drugim merama.

### Mogućnost B — uključiti enkripciju, pa tvrdnja ostaje

Tehnički je izvodljivo (procena: pola radnog dana, uključuje kratak prekid rada baze).
Nakon toga bi tekst glasio: *„Podaci se čuvaju u MySQL bazi uz enkripciju na nivou tabela
(AES-256)."*

**Šta nam treba od vas:** izbor — **A** ili **B**.

---

# ODLUKA 2 — Rokovi čuvanja podataka

**Gde se nalazi:** Politika privatnosti, sekcija **5. Period čuvanja podataka**, i sekcija
**4.3**, treća stavka.

Rok za draft podatke (7 dana) je u redu i radi tačno tako. Problem su druga dva roka.

### Sada piše

> - **Podnesene prijave:** 5 godina po završetku projekta (zakonska obaveza)
> - **Upload-ovani fajlovi:** Brišu se 30 dana po završetku projekta

### Problem

Oba roka su vezana za **„završetak projekta"**, a platforma taj pojam ne poznaje. Prijava
može biti *podneta*, *u razmatranju*, *odobrena* ili *odbijena* — nigde se ne evidentira da
je projekat završen. Zato ovi rokovi tehnički ne mogu da se sprovedu: sistem ne zna od kog
datuma da počne da meri.

Osim toga, „5 godina (zakonska obaveza)" — molimo potvrdite da ovaj rok zaista proizlazi iz
neke konkretne obaveze (ugovor sa donatorom, računovodstveni propisi). Ako ne, treba
napisati rok koji je vaša odluka, jer se pozivanje na zakon može proveriti.

### Šta predlažemo

Vezati rokove za datum koji sistem zna — **datum podnošenja prijave**. Primer:

> - **Odbijene prijave:** brišu se 12 meseci od podnošenja
> - **Odobrene prijave:** čuvaju se 5 godina od podnošenja (obaveza izveštavanja donatorima)
> - **Priložena dokumenta odbijenih prijava:** brišu se zajedno sa prijavom

**Šta nam treba od vas:** potvrda ovih brojeva ili vaši brojevi. Kada ih potvrdite, ugradimo
automatsko brisanje po tim rokovima — tako da tekst nije samo obećanje, nego stvarno pravilo.

*(Ako želite rok vezan za završetak projekta, to je takođe izvodljivo, ali onda u admin
panelu treba dodati polje „projekat završen" koje neko popunjava. Recite ako je to opcija.)*

---

# PODACI KOJI NAM TREBAJU

Na obe stranice trenutno stoje **primeri umesto pravih podataka.** To su ostaci iz izrade
platforme i moraju se zameniti pre objave:

| Gde | Sada piše | Treba |
|---|---|---|
| Politika, sekcija 6 i 9 | `privacy@domovik.rs` | pravi mejl za pitanja o podacima |
| Uslovi, sekcija 10 | `support@domovik.rs` | pravi mejl za tehničku podršku |
| Obe stranice | `+381 11 1234 567` | pravi telefon |
| Obe stranice | „Poslednja izmena: Decembar 2025" | datum objave nove verzije |

Napomena: domen u mejl adresama je `.rs`, a vaš je `.org`.

**Dodatno, po zakonu je obavezno navesti identitet rukovaoca podacima,** čega sada nema
nigde. Potrebno je:

1. **Pun pravni naziv udruženja** (kako je u APR-u)
2. **Adresa sedišta**
3. **Matični broj i PIB**
4. **Da li imate određeno lice za zaštitu podataka o ličnosti** — ako da, ime i kontakt

---

# ŠTA MENJAMO BEZ POTREBE ZA VAŠOM ODLUKOM

Ovo su ispravke činjeničnih netačnosti i zakonom obaveznih delova. Radimo ih same, samo da
znate da će tekst na tim mestima biti drugačiji.

### Politika privatnosti

- **Sekcija 1** — tvrdnja „u potpunosti usklađena sa GDPR" biće ublažena i pozvaćemo se
  prvenstveno na **Zakon o zaštiti podataka o ličnosti Republike Srbije** („Sl. glasnik RS"
  87/2018), koji je za vas primarno merodavan, a GDPR kao referenca.

- **Sekcija 3** — „Nikada ne delimo vaše podatke sa trećim licima" nije precizno.
  Podatke ne prodajete i ne koristite za marketing, ali dva pružaoca usluga tehnički
  dolaze u kontakt sa njima: **hosting** (server u Nemačkoj, u EU) i **email servis**
  (Microsoft 365, kojim idu potvrde o prijavi). Zakon zahteva da se to navede.

- **Sekcija 4.1** — piše „Server NIKADA ne dobija draft podatke". Skoro tačno, ali ne
  potpuno: tekst koji upisujete zaista ostaje samo na vašem uređaju, **ali dokumenti koji se
  priloži odlaze na server odmah pri upload-u**, pre klika na „PODNESI PRIJAVU". Takođe se
  čuva jedan tehnički zapis (slučajno generisan broj drafta i vreme, bez ličnih podataka).
  Ovo ćemo napisati precizno.

- **Sekcija 6** — dodajemo dva prava koja su obavezna, a nema ih: **pravo na povlačenje
  pristanka** u svakom trenutku, i **pravo na pritužbu Povereniku za informacije od javnog
  značaja i zaštitu podataka o ličnosti**.

- **Sekcija 7 (Kolačići)** — vaš predloženi tekst je tačan; dodajemo samo koliko traju, jer
  se i to navodi: `csrftoken` 12 meseci, `sessionid` 30 minuta neaktivnosti.

- **Nova sekcija** — tehnički logovi. Server beleži IP adrese posetilaca (uobičajeno, radi
  bezbednosti i otkrivanja grešaka). To se navodi u politici.

### Uslovi korišćenja

- **Sekcija 6.2** — vaša nova formulacija je **tačnija od one koja je sada na sajtu.** Sada
  piše: *„Osnovna funkcionalnost forme će raditi i bez JavaScript-a"* — to nije tačno, forma
  bez JavaScript-a ne radi. Vaša verzija („JavaScript: obavezan") ide na sajt.

  Jedna sitna korekcija: **`localStorage` nije striktno obavezan.** Bez njega prijava se može
  podneti, samo se ne čuva radna verzija. Predlog: *„localStorage: neophodan za čuvanje radne
  verzije. Bez njega prijavu možete podneti, ali se nacrt neće čuvati."*

- **Sekcija 3.2** — spisak obavezne dokumentacije za COB prijave je zastareo (piše
  „Biografija podnosioca", a sada se traži budžet inicijative uz opciono pismo podrške).
  Usklađujemo sa onim što forma zaista traži.

---

# ŠTA NAM KONKRETNO TREBA

1. **ODLUKA 1** — enkripcija baze: mogućnost **A** (ispraviti tekst, preporučujemo) ili **B**
   (uključiti enkripciju)
2. **ODLUKA 2** — rokovi čuvanja: potvrda predloženih rokova ili vaši rokovi
3. **PODACI** — pun pravni naziv, adresa, matični broj, PIB, lice za zaštitu podataka
   (ako postoji), pravi mejl(ovi) i telefon

Kada ovo dobijemo, finalne verzije obe stranice su gotove **u roku od jednog dana** i
objavljujemo ih na platformi.
