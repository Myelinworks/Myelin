# Technical Architecture, Cost & Timeline

> Source: `Myelin_Technical_Architecture_md.pdf` · Version v1.0 (Pilot Phase) · Timeline 45 days

## Overview

Myelin is a **deterministic** CEO decision-simulation platform. Every student decision
(Finance, Marketing, Product, Sales, Operations, Customer Experience) maps to a fixed formula
with base-impact values and contextual modifiers (Brand Strength, Market Saturation,
Inventory, Competitor Activity).

The backend's job:

1. Evaluate these formulas
2. Mutate company state each quarter
3. Generate **two parallel outputs per decision**

| Pipeline | Produces |
|---|---|
| **Business Impact** | Cash, revenue, KPIs, valuation |
| **Evidence** | Behavioural signals feeding the Cognitive Scoring Engine (Strategic Thinking, Adaptability, Leadership, …) |

This is a **data-and-rules-heavy system, not a compute-heavy one**. Architecture is optimised for:

- Clean state management
- Auditability (decision logs)
- Fast dashboard rendering across many chart-heavy workspaces

## Finalised tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js (App Router) if a public landing page/docs/marketing site sits alongside the app. React + Vite if this build is only the internal simulation platform. |
| Backend | FastAPI (Python) |
| Database | Supabase PostgreSQL |
| File/Object Storage | Supabase Storage (buckets — reports, exports, documents/media) |
| Cache | Redis (Upstash) |
| Deployment — Backend | Railway |
| Deployment — Frontend | Vercel |
| API Style | REST |

## Expected cost — pilot phase

| Service | Plan | Cost |
|---|---|---|
| Supabase | Free (500 MB DB, 1 GB storage, 50K MAU, 5 GB egress) → Pro at $25/mo once auto-pausing must be removed | $0 – $25/mo |
| Railway (backend) | Hobby, $5/mo base incl. $5 usage; scales per-second beyond | $5 – $20/mo |
| Vercel (frontend) | Hobby is free but **non-commercial only**; a real pilot needs Pro at $20/mo/seat (1 TB bandwidth, commercial rights) | $0 (Hobby, strictly non-commercial) or $20/mo (Pro, recommended) |
| Upstash Redis | Free tier (500K commands/mo, 256 MB) covers pilot scale; PAYG beyond at $0.20/100K commands | $0 – $10/mo |
| Domain | Annual, amortised | ~$1/mo |

**Estimated pilot total: ≈ $30 – $75/month**, realistically at the low end for the first several
weeks since Supabase Free and Upstash Free alone cover early-stage usage. Vercel Pro ($20) is the
main fixed cost worth budgeting for, since Hobby's non-commercial restriction doesn't fit a
pitch-stage product being shown to a stakeholder.

All are usage-based platforms — actual cost depends on pilot traffic/compute.

## Timeline

**45 days total**, covering:

- Architecture setup
- Core simulation engine (Finance, Marketing, Product, Sales, Operations workspaces)
- Dashboard UI
- Decision-log / evidence pipeline
- Pilot deployment

## Commercials

- Total project cost: **₹50,000**
- Payment terms:
  - ₹20,000 — advance (before development begins)
  - ₹15,000 — after MVP completion and demo
  - ₹15,000 — after final delivery, deployment, and handover
