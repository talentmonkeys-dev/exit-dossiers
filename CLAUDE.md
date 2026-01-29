# CLAUDE.md - Exit Intelligence & n8n Automation Skills

Dieses Dokument enthält alle Skills und Expertise für die Entwicklung von Exit Intelligence Workflows mit n8n, North Data API, und Anthropic Claude.

---

## Projekt-Kontext

Du arbeitest an einem **M&A Exit Intelligence System** für TalentMonkeys. Das System:
- Identifiziert Unternehmen mit hoher Exit-Wahrscheinlichkeit
- Nutzt North Data API für Firmendaten
- Erstellt Investment Dossiers mit Claude AI
- Automatisiert Workflows über n8n
- Hostet Dossiers auf GitHub Pages

**Wichtige URLs:**
- GitHub: https://github.com/talentmonkeys-dev/exit-dossiers
- GitHub Pages: https://talentmonkeys-dev.github.io/exit-dossiers/
- n8n Cloud: https://talentmonkeys.app.n8n.cloud

---

# SKILL 1: n8n Complete Expert Guide

Comprehensive guide for building flawless n8n workflows.

## 1.1 Expression Syntax

All dynamic content uses **double curly braces**: `{{expression}}`

```javascript
// Correct
{{$json.email}}
{{$json.body.name}}
{{$node["HTTP Request"].json.data}}

// Wrong
$json.email  // no braces - literal text
{$json.email}  // single braces - invalid
```

### Core Variables

| Variable | Use | Example |
|----------|-----|---------|
| `$json` | Current node output | `{{$json.fieldName}}` |
| `$node` | Reference other nodes | `{{$node["Node Name"].json.field}}` |
| `$now` | Current timestamp | `{{$now.toFormat('yyyy-MM-dd')}}` |
| `$env` | Environment variables | `{{$env.API_KEY}}` |

### CRITICAL: Webhook Data Structure

**Most Common Mistake**: Webhook data is **NOT** at root - it's under `.body`!

```javascript
// Webhook output structure
{
  "headers": {...},
  "params": {...},
  "query": {...},
  "body": {           // USER DATA IS HERE!
    "name": "John",
    "email": "john@example.com"
  }
}

// WRONG
{{$json.name}}

// CORRECT
{{$json.body.name}}
```

### When NOT to Use Expressions

| Context | Wrong | Correct |
|---------|-------|---------|
| Code nodes | `'={{$json.email}}'` | `$json.email` |
| Webhook paths | `{{$json.user_id}}/webhook` | `user-webhook` (static) |
| Credentials | `={{$env.API_KEY}}` | Use credential system |

## 1.2 MCP Tools Guide

### Quick Reference - Most Used Tools

| Tool | Use When | Speed |
|------|----------|-------|
| `search_nodes` | Finding nodes by keyword | <20ms |
| `get_node` | Understanding node operations | <10ms |
| `validate_node` | Checking configurations | <100ms |
| `n8n_create_workflow` | Creating workflows | 100-500ms |
| `n8n_update_partial_workflow` | Editing workflows (MOST USED!) | 50-200ms |
| `validate_workflow` | Checking complete workflow | 100-500ms |

### nodeType Formats

**Two different formats for different tools!**

```javascript
// Search/Validate Tools (short prefix)
"nodes-base.slack"
"nodes-base.httpRequest"
"nodes-langchain.agent"

// Workflow Tools (full prefix)
"n8n-nodes-base.slack"
"n8n-nodes-base.httpRequest"
"@n8n/n8n-nodes-langchain.agent"
```

## 1.3 JavaScript Code Node

### Quick Start Template

```javascript
const items = $input.all();

const processed = items.map(item => ({
  json: {
    ...item.json,
    processed: true,
    timestamp: new Date().toISOString()
  }
}));

return processed;
```

### Essential Rules

1. Choose **"Run Once for All Items"** mode (95% of use cases)
2. Access data: `$input.all()`, `$input.first()`, or `$input.item`
3. **MUST return** `[{json: {...}}]` format
4. **Webhook data under** `$json.body` (not `$json` directly)
5. **Built-ins available**: `$helpers.httpRequest()`, `DateTime`, `$jmespath()`

### Mode Selection

| Mode | Use When | Access |
|------|----------|--------|
| **Run Once for All Items** (Default) | 95% of use cases | `$input.all()` |
| Run Once for Each Item | Per-item operations | `$input.item` |

### Top 5 Errors & Fixes

| Error | Fix |
|-------|-----|
| Empty code / missing return | Add `return [...]` |
| Expression syntax in code | Use `$json.field` not `{{ $json.field }}` |
| Object instead of array | Return `[{json: ...}]` not `{json: ...}` |
| Null crashes | Use `item.json?.user?.email \|\| 'default'` |
| Wrong webhook access | Use `$json.body.email` not `$json.email` |

## 1.4 Workflow Patterns

### The 5 Core Patterns

| Pattern | Trigger | Structure |
|---------|---------|-----------|
| **Webhook Processing** | HTTP request | Webhook -> Validate -> Transform -> Respond |
| **HTTP API Integration** | Various | Trigger -> HTTP Request -> Transform -> Action |
| **Database Operations** | Schedule | Schedule -> Query -> Transform -> Write |
| **AI Agent Workflow** | Chat/Webhook | Trigger -> AI Agent (Model+Tools+Memory) -> Output |
| **Scheduled Tasks** | Cron | Schedule -> Fetch -> Process -> Deliver -> Log |

### Workflow Creation Checklist

**Planning:**
- [ ] Identify pattern (webhook, API, database, AI, scheduled)
- [ ] List required nodes (use search_nodes)
- [ ] Plan data flow and error handling

**Implementation:**
- [ ] Create workflow with appropriate trigger
- [ ] Configure authentication/credentials
- [ ] Add transformation and output nodes
- [ ] Add error handling

**Validation & Deployment:**
- [ ] Validate each node (validate_node)
- [ ] Validate complete workflow
- [ ] Test with sample data
- [ ] Activate workflow
- [ ] Monitor first executions

---

# SKILL 2: North Data API Complete Guide

Comprehensive guide for accessing North Data's company database via HTTPS API.

**References:**
- API Reference: https://northdata.github.io/doc/api/
- User Guide: https://github.com/northdata/api/blob/master/doc/data-api-userguide/data-api-userguide.md

## 2.1 Authentication

### API Key Format

```
XXXX-XXXX (with hyphen!)
```

### Method 1: X-Api-Key Header (RECOMMENDED)

```http
X-Api-Key: XXXX-XXXX
```

### n8n HTTP Request Node Setup

```
Authentication: None
Send Headers: true
Header Name: X-Api-Key
Header Value: YOUR-API-KEY
```

**Common Error:** Using `Bearer` token or wrong header name causes 403.

## 2.2 Endpoints Overview

### Base URL

```
https://www.northdata.com/_api/
```

### All Endpoints

| Category | Endpoint | URL |
|----------|----------|-----|
| **Company** | Get Company | `/company/v1/company` |
| | Company Publications | `/company/v1/publications` |
| **Person** | Get Person | `/person/v1/person` |
| **Search** | **Power Search** | `/search/v1/power` |
| | Universal Search | `/search/v1/universal` |
| | Suggest (Autocomplete) | `/search/v1/suggest` |
| **Publications** | Query Publications | `/pub/v1/publications` |

## 2.3 Power Search (Most Important!)

### Endpoint

```
GET https://www.northdata.com/_api/search/v1/power
```

### Key Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `countries` | string[] | ISO codes: `DE\|AT\|CH` |
| `status` | string[] | `active\|terminated\|liquidation` |
| `legalForm` | string[] | `gmbh\|ag\|llc` |
| `indicatorId` | string[] | `Revenue\|Employees\|CompanyAge` |
| `lowerBound` | number[] | Min values |
| `upperBound` | number[] | Max values |

### Key Financial Indicators

| ID | Description | Unit |
|----|-------------|------|
| `Revenue` | Annual revenue | EUR |
| `Earnings` | Annual earnings | EUR |
| `Employees` | Employee count | - |
| `Equity` | Equity capital | EUR |
| `CompanyAge` | Years since founding | Years |
| `RevenueGrowth1Y` | Revenue growth 1 year | % |

### Example: Exit Intelligence Search

```
GET /search/v1/power
  ?countries=DE
  &status=active
  &legalForm=gmbh
  &indicatorId=Revenue|Employees|CompanyAge
  &lowerBound=1000000|10|10
  &upperBound=50000000|500|
  &financials=true
  &relations=true
  &limit=100
```

## 2.4 Error Handling

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Process response |
| 400 | Bad Request | Check parameter format |
| 403 | Forbidden | Check API key format (XXXX-XXXX) |
| 404 | Not Found | Entity doesn't exist |
| 500 | Server Error | Contact support@northdata.com |

### Common Issues

**403 "invalid API key":**
1. Format must be `XXXX-XXXX` (with hyphen)
2. Use `X-Api-Key` header (not `Authorization: Bearer`)

**Empty Results:**
1. Country codes: **UPPERCASE** (`DE` not `de`)
2. Legal forms: **lowercase** (`gmbh` not `GmbH`)
3. Status: **lowercase** (`active` not `Active`)

---

# SKILL 3: Exit Intelligence Dossier Creation

## 3.1 Dossier Workflow Architecture

```
Google Sheets Trigger (polls for Create_Dossier = TRUE)
    ↓
Filter Node (only rows without Dossier_Link)
    ↓
Build Prompt (creates Claude instruction)
    ↓
Claude AI (generates HTML)
    ↓
Extract & Encode HTML (Base64 for GitHub)
    ↓
Upload to GitHub (via API)
    ↓
Create Pages URL
    ↓
Update Google Sheet (adds link, sets FALSE)
```

## 3.2 HTML Dossier Design Specification

### Color Scheme (Goldman Sachs Style)

```css
:root {
  --primary-navy: #002d62;
  --accent-gold: #b3a369;
  --text-slate: #2c3e50;
  --bg-light: #f8f9fa;
  --border-gray: #d1d1d1;
  --risk-red: #c0392b;
  --success-green: #27ae60;
}
```

### Typography

```css
/* Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Inter:wght@300;400;500;600&display=swap');

/* Headlines */
font-family: 'Playfair Display', Georgia, serif;

/* Body */
font-family: 'Inter', -apple-system, sans-serif;

/* Labels */
text-transform: uppercase;
letter-spacing: 2px;
font-weight: 600;
font-size: 11px;
```

### 7-Section Structure

1. **Cover Page** - Navy background, Project Name, CONFIDENTIAL
2. **Executive Summary** - Thesis, Key Metrics, Exit Probabilities
3. **Company Profile** - Business data, Industry, Location
4. **Financial Analysis** - Revenue, Growth, Margins
5. **Exit Intelligence** - Scores, Signals, Probabilities (PROMINENT!)
6. **Risk Assessment** - Risks, Deal Breakers, DD Points
7. **Approach Strategy** - Timing, Script, Next Steps

## 3.3 Key Data Fields

### Exit Intelligence Metrics (MOST IMPORTANT!)

```javascript
Exit_Intelligence     // 0-100 overall score
Exit_Druck           // 0-100 exit pressure
Brautschau_Score     // 0-100 "looking for buyer" signals
Exit_Prob_12M        // % probability in 12 months
Exit_Prob_24M        // % probability in 24 months
Exit_Readiness       // HOT LEAD | QUALIFIED | NURTURE
Priority             // GOLD DUST | HIGH | MEDIUM | LOW
Confidence           // very_high | high | medium | low
```

### Financial Data

```javascript
Revenue_M            // Annual revenue in Mio EUR
Earnings_M           // EBITDA in Mio EUR
Employees            // Employee count
Equity_M             // Equity in Mio EUR
Equity_Ratio         // EK-Quote in %
Revenue_Growth_1Y    // 1-year growth %
Revenue_Growth_3Y    // 3-year growth %
```

### Owner/Succession Data

```javascript
Owner                // Name
Age                  // Current age
Role                 // Managing Director, Shareholder, etc.
Ownership            // % ownership
Tenure               // Years in position
Succession           // Ja/Nein
Successor_Name       // If identified
```

---

# SKILL 4: GitHub Pages Integration

## 4.1 GitHub API for File Upload

### Endpoint

```
PUT https://api.github.com/repos/{owner}/{repo}/contents/{path}
```

### Headers

```http
Authorization: Bearer {token}
Accept: application/vnd.github.v3+json
X-GitHub-Api-Version: 2022-11-28
```

### Body

```json
{
  "message": "Add dossier for {Company}",
  "content": "{base64_encoded_html}"
}
```

### n8n Implementation

```javascript
// Encode HTML to Base64
const base64Content = Buffer.from(htmlContent, 'utf-8').toString('base64');

// GitHub API URL
const url = `https://api.github.com/repos/talentmonkeys-dev/exit-dossiers/contents/${filename}`;
```

## 4.2 GitHub Pages URL Structure

```
https://talentmonkeys-dev.github.io/exit-dossiers/{filename}.html
```

---

# Quick Reference Card

## n8n Expressions

```javascript
{{$json.field}}              // Current node data
{{$json.body.field}}         // Webhook data (CRITICAL!)
{{$node["Name"].json.field}} // Other node data
{{$now.toFormat('yyyy-MM-dd')}} // Date formatting
```

## Code Node Return Format

```javascript
// JavaScript
return [{json: {...}}];

// Filter (keep items)
return items.filter(item => item.json.condition === true);

// Transform
return items.map(item => ({json: {...item.json, newField: value}}));
```

## North Data API

```bash
# Power Search
curl -H "X-Api-Key: XXXX-XXXX" \
  "https://www.northdata.com/_api/search/v1/power?countries=DE&legalForm=gmbh"

# Company Lookup
curl -H "X-Api-Key: XXXX-XXXX" \
  "https://www.northdata.com/_api/company/v1/company?registerKey=12203550103038"
```

## GitHub API

```bash
# Upload file
curl -X PUT \
  -H "Authorization: Bearer {token}" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/owner/repo/contents/file.html" \
  -d '{"message": "Add file", "content": "base64..."}'
```

---

# Best Practices

## Do ✅

- Use `get_node` with standard detail (default)
- Validate after every significant change
- Access webhook data via `.body`
- Return `[{json: ...}]` from Code nodes
- Use GitHub Pages for HTML hosting
- Make Exit Probabilities the most prominent metrics

## Don't ❌

- Use expressions in Code nodes
- Skip validation before activation
- Store `companyId` (use `registerKey` instead)
- Forget the hyphen in North Data API key
- Use `Bearer` token for North Data (use `X-Api-Key`)

---

*Exit Intelligence System - TalentMonkeys*
*Skills compiled from n8n-skills by Romuald Czlonkowski and North Data API documentation*
