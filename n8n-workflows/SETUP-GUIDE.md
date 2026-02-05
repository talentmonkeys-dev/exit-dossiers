# TalentMonkeys Lead Generation - n8n Workflow Setup Guide

## Workflow Import

1. In n8n, go to **Workflows** > **Import from File**
2. Select `talentmonkeys-lead-generation-complete.json`
3. The workflow will be imported with all nodes

## Required Credentials

You need to create the following credentials in n8n:

### 1. Serper API (HTTP Header Auth)
- **Name**: `Serper API` (must match exactly)
- **Type**: HTTP Header Auth
- **Header Name**: `X-API-KEY`
- **Header Value**: `YOUR_SERPER_API_KEY`

### 2. Apollo API (HTTP Header Auth)
- **Name**: `Apollo API` (must match exactly)
- **Type**: HTTP Header Auth
- **Header Name**: `x-api-key`
- **Header Value**: `YOUR_APOLLO_API_KEY`

### 3. Apify API (HTTP Header Auth)
- **Name**: `Apify API` (must match exactly)
- **Type**: HTTP Header Auth
- **Header Name**: `Authorization`
- **Header Value**: `Bearer YOUR_APIFY_API_TOKEN`

### 4. Claude API (HTTP Header Auth)
- **Name**: `Claude API` (must match exactly)
- **Type**: HTTP Header Auth
- **Header Name**: `x-api-key`
- **Header Value**: `YOUR_ANTHROPIC_API_KEY`

### 5. Instantly API (HTTP Header Auth)
- **Name**: `Instantly API` (must match exactly)
- **Type**: HTTP Header Auth
- **Header Name**: `Authorization`
- **Header Value**: `Bearer YOUR_INSTANTLY_API_KEY`

### 6. Google Sheets OAuth
- **Name**: `Google Sheets OAuth`
- **Type**: Google Sheets OAuth2 API
- Create OAuth credentials in Google Cloud Console
- Add scopes: `https://www.googleapis.com/auth/spreadsheets`

### 7. Gmail OAuth
- **Name**: `Gmail OAuth`
- **Type**: Gmail OAuth2 API
- Use same Google Cloud project
- Add scopes: `https://www.googleapis.com/auth/gmail.send`, `https://www.googleapis.com/auth/gmail.readonly`

## Google Sheets Setup

The workflow uses Google Sheet ID: `1Tei2P38DZpzEO1eKSnSlHoNDm3Gv3GslVsnYxmig07Q`

Create these tabs with the following columns:

### Tab: Jobs
| Column | Description |
|--------|-------------|
| Date | Date found |
| Job_Title | Position title |
| Company | Company name |
| Domain | Company domain |
| Location | Austria |
| Salary | Salary text |
| Job_URL | Link to job |
| Source | Google/LinkedIn |
| Status | pending_approval/approved/skipped |
| Approved | Boolean |
| Responsible | Flavio |

### Tab: Leads
| Column | Description |
|--------|-------------|
| Date | Date enriched |
| Company | Company name |
| Domain | Domain |
| Employees | Employee count |
| HR_Name | Contact name |
| HR_Title | Contact title |
| HR_Email | Email address |
| HR_LinkedIn | LinkedIn URL |
| Job_Title | Original job |
| Clean_Job_Title | Cleaned title |
| Email_Subject | Generated subject |
| Email_Body | Generated body |
| Status | ready_for_outreach/sent_to_instantly/meeting_scheduled/closed_lost |
| Instantly_Status | added/replied |
| Last_Response | POSITIV/NEGATIV/etc |

### Tab: Conversations
| Column | Description |
|--------|-------------|
| Date | Timestamp |
| Email | Lead email |
| Company | Company name |
| Classification | POSITIV/NEGATIV/FRAGE/SPATER/ABWESEND |
| Their_Reply | Original reply text |
| Our_Response | Claude's response |
| Response_Sent | Boolean |

## Instantly Campaign Setup

Create a 2-step campaign in Instantly with these placeholders:

### Step 1 - Initial Outreach
**Subject**: `{{email_subject}}`

**Body**:
```
{{email_body}}

Mit freundlichen Gruessen,
Flavio Arteaga
TalentMonkeys GmbH
```

### Step 2 - Follow-up (3 days later)
**Subject**: `Re: {{email_subject}}`

**Body**:
```
Hallo {{first_name}},

ich wollte mich noch einmal kurz melden bezueglich Ihrer offenen {{job_title}} Position.

Haetten Sie diese Woche kurz Zeit fuer ein 15-minuetiges Telefonat? Ich bin flexibel und passe mich gerne Ihrem Zeitplan an.

Beste Gruesse,
Flavio
```

### After Campaign Creation

1. Get the Campaign ID from Instantly
2. Update the "Add Lead to Instantly" node in n8n
3. Replace `{{INSTANTLY_CAMPAIGN_ID}}` with the actual ID

## Instantly Webhook Setup

1. In Instantly, go to Settings > Webhooks
2. Add a webhook for "Reply Received"
3. Set URL to your n8n webhook URL:
   `https://talentmonkeys.app.n8n.cloud/webhook/instantly-webhook`

## Workflow Activation

1. After setting up all credentials, test each node individually
2. Use "Execute Node" on the Daily trigger to run a test
3. Once everything works, activate the workflow

## Workflow Structure

```
Phase 1: Job Discovery (Daily 07:00)
  - Category Rotation (7 categories, rotates daily)
  - Serper x3 searches (parallel)
  - Apify LinkedIn scrape (async, 2min wait)
  - Combine & Filter (dedupe, blacklist, salary filter)

Phase 2: Approval Flow
  - Save to Google Sheets (Jobs tab)
  - Send approval email to Flavio
  - Gmail trigger waits for reply
  - Parse approval (JA/NEIN/numbers)

Phase 3: Enrichment & Outreach
  - Apollo organization enrich
  - Check min 50 employees
  - Apollo HR contact search
  - Apollo reveal email
  - Claude generate personalized message
  - Save to Leads sheet
  - Add to Instantly campaign

Phase 4: Reply Handling
  - Instantly webhook trigger
  - Get lead context from Sheets
  - Claude analyze reply (classify)
  - Send appropriate response
  - Log conversation
  - Update lead status
```

## Troubleshooting

### No jobs found
- Check Serper API key
- Try manual search on Google to verify jobs exist
- Check category rotation date

### Apollo no results
- Company domain may be wrong
- Company may be too small (<50 employees)
- Try searching for company manually on Apollo

### Instantly not receiving leads
- Check Campaign ID is correct
- Verify Instantly API key
- Check lead has valid email

### Gmail not triggering
- Check OAuth scopes
- Verify filter matches your approval email subject
- Gmail trigger polls every minute

## Support

- n8n Cloud: https://talentmonkeys.app.n8n.cloud
- GitHub: https://github.com/talentmonkeys-dev/exit-dossiers
