# BudgetFlow

A full-stack envelope budgeting app — Django REST API + React SPA with JWT auth, per-category balances, and a polished dashboard.

> Status: in active development.

## Highlights

- JWT auth with email verification and password reset
- Envelope-style categories with a primary **Wallet** and per-user balances
- Income, expense, and allocate transactions with overdraft protection
- Dashboard totals, recent activity, and chart-ready data
- Light / dark themes with a first-run welcome tour

## Tech Stack

**Backend** Django · Django REST Framework
**Frontend** React · Vite
**Data** SQLite (dev) · Postgres (prod)

## Quick Start

Run the backend and frontend in two terminals. Both folders ship a `.env.example` — copy it to `.env` and fill in the values before starting.

## Reviewer Demo

- [ ] Register a new account
- [ ] Review the seeded **Wallet** and starter categories
- [ ] Allocate funds from Wallet to a category
- [ ] Log an expense from that category
- [ ] Check dashboard totals and recent activity
- [ ] Toggle dark mode

## Deployment

Deploys cleanly to **Render** (backend + Postgres) and **Vercel** (frontend) using the included `render.yaml` and `vercel.json`. In production, generate a fresh `SECRET_KEY`, set `DEBUG=False`, and restrict CORS / CSRF origins to your frontend domain.

## Security

- Short-lived JWT access tokens with refresh rotation
- Single-use, time-bound password reset and email verification tokens
- Django password validators with a frontend strength meter
- CORS allowlist, CSRF trusted origins, HSTS, secure cookies, and `SECURE_PROXY_SSL_HEADER` enabled in production
- `.env` files are gitignored — never commit secrets

Please report security issues privately via [`SECURITY.md`](SECURITY.md) rather than opening a public issue.

## Testing

```powershell
cd backend
py manage.py test
```

CI runs the same suite on every push to `main`.
