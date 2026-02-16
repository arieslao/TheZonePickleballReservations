# The Zone Pickleball Reservations
**An intelligent booking automation system that demonstrates enterprise 
RPA patterns, ChatOps integration, and containerized microservices.**

> Built with Python, Playwright, Flask, Slack API, and Docker

---

## The Problem
Court reservations at The Zone Sports Center open on a rolling 
4-day window and sell out within seconds. Manual booking is 
unreliable, frustrating, and time-consuming.

## The Solution
An automated reservation system that:
- Monitors court availability across a configurable booking window
- Executes precision-timed bookings at slot release (23:59:59)
- Sends real-time Slack notifications with interactive booking buttons
- Runs headlessly in a Docker container on Railway

## Architecture
<img width="1648" height="724" alt="image" src="https://github.com/user-attachments/assets/15fbcff8-39ba-45f3-b9e7-0c1c35765cc7" />


## Technology Choices & Why

| Technology | Purpose | Why This Over Alternatives |
|-----------|---------|---------------------------|
| Playwright | Browser automation | Handles JS-heavy SPAs that APIs can't reach; async-native |
| Flask | Webhook server | Lightweight; perfect for single-endpoint microservices |
| Slack Webhooks | User notifications | Where teams already communicate; interactive buttons enable action without context-switching |
| Docker | Containerization | Reproducible deploys; bundles Chromium dependencies cleanly |
| HMAC-SHA256 | Request verification | Prevents replay attacks on webhook endpoints |

## Corporate Translation
This same architecture pattern applies to enterprise scenarios:

- **HR/IT**: Automated resource booking (conference rooms, equipment, 
  licenses) with Slack/Teams approval workflows
- **Supply Chain**: Inventory slot reservation systems that act on 
  time-sensitive windows
- **Finance**: Automated compliance report filing before regulatory 
  deadlines
- **Sales**: CRM lead assignment automation with real-time 
  notification and one-click action

The pattern — **time-sensitive automation + ChatOps integration + 
containerized deployment** — is the foundation of enterprise RPA 
that [Gartner predicts will be in 40% of enterprise apps by 
end of 2026].

## Key Engineering Decisions
- **Session persistence over OAuth**: Skedda doesn't offer a public 
  API, so browser session storage was the pragmatic choice
- **Pixel-coordinate clicking over CSS selectors**: The booking grid 
  uses dynamic rendering that defeats traditional selectors
- **Threading for Slack responses**: Slack requires <3s webhook 
  response times; booking runs in background threads to avoid timeouts
- **Priority-ordered court list**: Mimics real user preference rather 
  than first-available, reducing follow-up rebooking

## How to Run
[clear setup instructions with .env.example reference]

## What I'd Do Differently / Next Steps
- Add an LLM-powered natural language booking interface via Slack
- Implement demand forecasting from historical availability data
- Add observability (structured logging, latency metrics)
- Migrate from session scraping to official API if one becomes available
