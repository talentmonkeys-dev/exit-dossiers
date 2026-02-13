# TalentMonkeys Lead Generation System

Automatisiertes Lead Generation System fuer talentmonkeys GmbH.

## Features

- **Apollo-basierte Firmensuche** (besser als Job-Portal Scraping!)
- **Automatische HR-Kontakt Anreicherung**
- **Google Sheets Integration** fuer Lead-Tracking
- **Human-in-the-Loop Approval** via Email
- **Personalisierte Outreach-Emails**
- **Spam-Schutz** (Business Hours, Delays, Cooldown)
- **Taegliche Kategorie-Rotation** (IT, Sales, Marketing, etc.)

## Installation

```bash
cd leadgen
pip install -r requirements.txt
```

## Google Cloud Setup

1. Gehe zu [Google Cloud Console](https://console.cloud.google.com/)
2. Erstelle ein neues Projekt
3. Aktiviere Gmail API und Google Sheets API
4. Erstelle OAuth 2.0 Credentials (Desktop App)
5. Lade `credentials.json` herunter
6. Kopiere es in den `leadgen/` Ordner

## Verwendung

### Test aller Komponenten

```bash
python main.py --test
```

### Nur Suche und Anreicherung (ohne Emails)

```bash
python main.py --search-only --limit 10
```

### Vollstaendige Pipeline mit Approval

```bash
python main.py --spreadsheet-id YOUR_SHEET_ID
```

### Auto-Approve Mode (zum Testen)

```bash
python main.py --auto-approve --limit 5
```

## Konfiguration

Alle Einstellungen in `config.py`:

- **API Keys**: Serper, Apollo
- **Email Settings**: Flavio@talentmonkeys.com
- **Job Categories**: 7 Kategorien mit taeglicher Rotation
- **Blacklist**: Firmen die ausgeschlossen werden
- **Limits**: Max 50 Leads/Tag, Min 50 Mitarbeiter

## Architektur

```
leadgen/
├── config.py           # Konfiguration und Konstanten
├── apollo_client.py    # Apollo.io API Client
├── job_search.py       # Firmen-/Jobsuche
├── sheets_client.py    # Google Sheets Integration
├── email_client.py     # Gmail Integration
├── main.py             # Hauptprogramm/Orchestrator
├── credentials.json    # Google OAuth (nicht committen!)
└── requirements.txt    # Python Dependencies
```

## Workflow

1. **Suche**: Apollo durchsucht oesterreichische Firmen nach Kategorie
2. **Filter**: Blacklist, Recruiting-Agenturen, Mitarbeiterzahl
3. **Anreicherung**: HR-Kontakt + verifizierte Email + Telefon
4. **Speicherung**: Lead in Google Sheets
5. **Approval**: Email an Flavio mit Lead-Liste
6. **Outreach**: Personalisierte Emails an genehmigte Leads

## Scheduling (Cron)

Fuer taegliche Ausfuehrung um 8:00:

```bash
crontab -e
```

Eintrag hinzufuegen:

```
0 8 * * 1-5 cd /pfad/zu/leadgen && python main.py --spreadsheet-id SHEET_ID >> leadgen.log 2>&1
```

## Vorteile gegenueber n8n

- **Mehr Kontrolle**: Bessere Fehlerbehandlung, Debugging
- **Bessere Datenquelle**: Apollo Company Search statt Job-Portal Scraping
- **Einfacher zu warten**: Standard Python Code
- **Kostenlos**: Keine n8n Cloud Kosten
- **Flexibel**: Leicht erweiterbar

## API Limits

- **Apollo**: Abhaengig vom Plan (Free: ~100 Credits/Monat)
- **Serper**: 2500 Suchen/Monat (Free Plan)
- **Gmail**: 500 Emails/Tag
- **Google Sheets**: 60 Requests/Minute

## Support

Bei Fragen: Flavio@talentmonkeys.com
