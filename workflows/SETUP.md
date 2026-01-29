# TalentMonkeys Lead Generation Workflow - Setup Guide

## Overview

Diese Dokumentation beschreibt die Einrichtung der n8n Lead Generation Workflows fuer talentmonkeys GmbH.

**Workflows:**
1. **TalentMonkeys Lead Gen** - Hauptworkflow fuer Job-Scraping, Enrichment und Outreach
2. **TalentMonkeys Reply Handler** - Automatische Verarbeitung von Antworten

---

## 1. Voraussetzungen

### n8n Instanz
- URL: https://talentmonkeys.app.n8n.cloud
- Timezone: Europe/Vienna

### Erforderliche Credentials

| Credential | Typ | API Key/Details |
|------------|-----|-----------------|
| Serper API | Header Auth | `YOUR_SERPER_API_KEY` |
| Apollo.io | Header Auth | `YOUR_APOLLO_API_KEY` |
| Gmail | OAuth2 | Client ID aus Google Cloud Console |
| Google Sheets | OAuth2 | Client Secret aus Google Cloud Console |

> **Hinweis:** Die API Keys und OAuth Credentials wurden separat bereitgestellt. Diese nicht im Repository speichern!

---

## 2. Credentials einrichten

### 2.1 Serper API

1. Gehe zu **Settings > Credentials > Add Credential**
2. Waehle **Header Auth**
3. Konfiguration:
   - Name: `Serper API`
   - Header Name: `X-API-KEY`
   - Header Value: `YOUR_SERPER_API_KEY` (separat bereitgestellt)

### 2.2 Apollo.io API

1. Gehe zu **Settings > Credentials > Add Credential**
2. Waehle **Header Auth**
3. Konfiguration:
   - Name: `Apollo API`
   - Header Name: `x-api-key`
   - Header Value: `YOUR_APOLLO_API_KEY` (separat bereitgestellt)

### 2.3 Gmail OAuth2

1. Gehe zu **Settings > Credentials > Add Credential**
2. Waehle **Gmail OAuth2 API**
3. Konfiguration:
   - Client ID: `YOUR_GOOGLE_CLIENT_ID` (aus Google Cloud Console)
   - Client Secret: `YOUR_GOOGLE_CLIENT_SECRET` (aus Google Cloud Console)
   - Scope: `https://www.googleapis.com/auth/gmail.modify`
4. **OAuth Flow ausfuehren** mit dem konfigurierten Google Account

### 2.4 Google Sheets OAuth2

1. Gehe zu **Settings > Credentials > Add Credential**
2. Waehle **Google Sheets OAuth2 API**
3. Konfiguration:
   - Client ID: `YOUR_GOOGLE_CLIENT_ID` (gleiche wie Gmail)
   - Client Secret: `YOUR_GOOGLE_CLIENT_SECRET` (gleiche wie Gmail)
4. **OAuth Flow ausfuehren** mit dem gleichen Google Account

---

## 3. Google Sheet erstellen

### 3.1 Neues Sheet anlegen

1. Oeffne Google Sheets
2. Erstelle ein neues Spreadsheet: **"TalentMonkeys Leads"**
3. Benenne das erste Tabellenblatt: **"TalentMonkeys Leads"**

### 3.2 Header-Zeile (Zeile 1)

Fuege folgende Spalten in Zeile 1 ein:

| A | B | C | D | E | F | G | H | I | J | K | L | M | N | O |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Datum | Kategorie | Firma | Mitarbeiter | Job Titel | Job URL | Gehalt | HR Kontakt | Email | Telefon | LinkedIn | Weitere Jobs | Status | Letzter Kontakt | Notizen |

### 3.3 Bedingte Formatierung (Optional)

**Status-Spalte (M) faerben:**
- "Neu" = Blau
- "Gesendet" = Gelb
- "Interessiert" = Gruen
- "Abgelehnt" = Rot

---

## 4. Workflows importieren

### 4.1 Hauptworkflow importieren

1. Gehe zu **Workflows > Import from File**
2. Waehle `talentmonkeys-lead-gen-workflow.json`
3. Oeffne den importierten Workflow

### 4.2 Credentials zuweisen

Weise folgende Credentials den Nodes zu:

| Node | Credential |
|------|------------|
| Serper Job Search | Serper API (Header Auth) |
| Apollo Org Enrichment | Apollo API (Header Auth) |
| Apollo People Search | Apollo API (Header Auth) |
| Apollo Contact Match | Apollo API (Header Auth) |
| Google Sheets Lookup | Google Sheets OAuth2 |
| Google Sheets Append | Google Sheets OAuth2 |
| Google Sheets Update Sent | Google Sheets OAuth2 |
| Gmail Approval Request | Gmail OAuth2 |
| Gmail Trigger Reply | Gmail OAuth2 |
| Gmail Send Outreach | Gmail OAuth2 |

### 4.3 Google Sheet Document ID eintragen

1. Oeffne dein Google Sheet
2. Kopiere die Document ID aus der URL: `https://docs.google.com/spreadsheets/d/DOCUMENT_ID/edit`
3. Trage die ID in allen Google Sheets Nodes ein

### 4.4 Reply Handler importieren

1. Importiere `talentmonkeys-reply-handler-workflow.json`
2. Weise Gmail und Google Sheets Credentials zu
3. Trage die Google Sheet Document ID ein

---

## 5. Workflow-Logik

### 5.1 Kategorie-Rotation

Der Workflow rotiert taeglich durch 7 Job-Kategorien:

| Tag | Kategorie |
|-----|-----------|
| Mo/Tag 1 | IT |
| Di/Tag 2 | Sales |
| Mi/Tag 3 | Marketing |
| Do/Tag 4 | Finance |
| Fr/Tag 5 | HR |
| Sa/Tag 6 | Engineering |
| So/Tag 7 | Operations |

Nach 7 Tagen beginnt die Rotation von vorne.

### 5.2 Filterkriterien

Ein Lead wird nur verarbeitet wenn:
- Job maximal 2 Wochen alt
- Unternehmen >= 50 Mitarbeiter
- NICHT auf der Blacklist
- KEINE Recruiting-Agentur
- Verifizierte Email vorhanden
- Nicht in den letzten 30 Tagen kontaktiert

### 5.3 Spam-Schutz

- Emails nur Mo-Fr
- Emails nur 08:00-18:00 (Vienna)
- Max 50 Emails/Tag
- 5-15 Minuten Pause zwischen Emails
- Max 1x pro 30 Tage pro Lead

---

## 6. Testing

### 6.1 Manueller Test

1. Oeffne den Hauptworkflow
2. Klicke auf **Execute Workflow** (manuell)
3. Pruefe jeden Schritt im Execution Log

### 6.2 Test-Checklist

- [ ] Serper API gibt Job-Ergebnisse zurueck
- [ ] Apollo Enrichment funktioniert
- [ ] Google Sheet wird beschrieben
- [ ] Approval-Email kommt an
- [ ] Reply-Parsing funktioniert
- [ ] Outreach-Email wird gesendet

### 6.3 Test mit eigenem Email

Aendere temporaer `Flavio@talentmonkeys.com` zu deiner Test-Email, um den Flow zu testen.

---

## 7. Aktivierung

### 7.1 Hauptworkflow aktivieren

1. Oeffne den Workflow
2. Stelle sicher, dass alle Credentials verbunden sind
3. Klicke auf **Activate** (oben rechts)

### 7.2 Reply Handler aktivieren

1. Oeffne den Reply Handler Workflow
2. Stelle sicher, dass Credentials verbunden sind
3. Klicke auf **Activate**

### 7.3 Ueberwachung

Nach Aktivierung:
- Pruefe taeglich die Executions
- Ueberwache die Google Sheets auf neue Leads
- Reagiere zeitnah auf "Interessiert" Status

---

## 8. Blacklist

Folgende Unternehmen werden automatisch ausgeschlossen:

```
PSA, Drees & Sommer, LKW Walter, Cyan Security, Schmachtl,
Netconomy, Lisec, Babak Bacon, Binderholz, Post, Lat Nitrogen,
Still, ATSP, KUKA, Kotanyi, Eam, Rohndo Ganahl, Informatics,
Rail Power Systems, Doka, Hobex, Budimex, ComeOn Group, Toolsense,
Mubea, XXXL, Ortner, Axians, ARAG, Planradar, Haberkorn,
Xit Cross, Wuerth Elektronik, Filzwieser, Tractive, Buehler,
Salesianer, Lasselsberger, TaxPro, Automation X, Light for the world,
Ebcont, Waterdrop, Hoerbiger, Verbund, Plasmics, Patchbox, Feri,
Navax, Uniqa, Workist, RBI, Hahn Software, Bawag, Finmatics,
Meister, KIK, With Solid, Tink, UCS, Mister Specks, Bitpanda,
Speedinvest, CTRL.QS, Joris Ide, Gebr. Heinemann, Ubimet, Gekko,
Steffl, Waldquelle, enspired, Swat.io, Consileon, Glacier,
Treetop Medical, Sclable, Journi, Jentis, Generali, Otago,
Anyline, Celum, Frequentis, Herold, IBM iX CH DE, Imi,
Voestalpine, Tourradar, Mysugr, Evolve Consulting, Bet@Home,
Alpenland, Nexxar, NextMunich, BWT, ZKW, Deepopinion, Oatly,
Eversports, HalloSonne, Dynatrace, Ikarus, Storyblok, IKEA, Mjam
```

### Blacklist erweitern

Um weitere Unternehmen hinzuzufuegen, bearbeite den Code im Node "Parse & Filter Jobs":

```javascript
const blacklist = [
  // ... bestehende Eintraege
  "Neues Unternehmen",  // Neuer Eintrag
];
```

---

## 9. Troubleshooting

### API Fehler

| Fehler | Loesung |
|--------|---------|
| 403 Serper | API Key pruefen (Header: X-API-KEY) |
| 403 Apollo | API Key pruefen (Header: x-api-key) |
| 401 Gmail | OAuth neu autorisieren |
| 404 Sheet | Document ID und Sheet-Name pruefen |

### Keine Leads gefunden

1. Pruefe ob Serper Ergebnisse liefert
2. Pruefe Apollo Enrichment (>= 50 MA)
3. Pruefe ob alle Leads auf Blacklist sind
4. Pruefe ob alle in letzten 30 Tagen kontaktiert wurden

### Email wird nicht gesendet

1. Pruefe Business Hours (Mo-Fr, 08-18h Vienna)
2. Pruefe ob 50 Emails/Tag Limit erreicht
3. Pruefe Gmail Quota

---

## 10. Kontakt

**Erstellt fuer:** talentmonkeys GmbH
**Email:** Flavio@talentmonkeys.com
**Website:** talentmonkeys.com
**n8n Cloud:** talentmonkeys.app.n8n.cloud

---

*Letzte Aktualisierung: 2025-01-29*
