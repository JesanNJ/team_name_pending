# Canteen Management System

> **Know your wait before you queue.**
> Order ahead from your campus canteen, see an honest waiting time, and track your order live.

A full-stack canteen ordering platform built for the **Genesis Hackathon**. Students order from one of several canteens, each with its own menu, cart and kitchen queue. Orders start cooking automatically (up to 15 at a time per canteen), staff get an express lane, and every order shows its own estimated ready time.

---

## Features

| Area | What it does |
|---|---|
| **Separate canteens** | Each canteen has its own menu, stock, carts, orders and queue |
| **Ordering** | Browse the menu, cart per canteen, stock validated at checkout, cancel with stock restored |
| **Smart queue** | At most 15 orders cook at once per canteen; pending orders start automatically, first come first served |
| **Waiting time** | Per-order estimate from queue position and kitchen stations (live counters, bulk pots, quick items) |
| **Staff express lane** | Staff orders skip the gate and are made first, with a guardrail on how many can use it at once |
| **Live updates** | Supabase Realtime pushes changes to the orders page, with a 30-second polling fallback |
| **Notifications** | "Ready for pickup" email through Brevo |
| **Admin portal** | Manage menu (add, edit, hide, delete, stock), move orders through statuses, per-canteen analytics |
| **Auth and roles** | JWT login with refresh-token blacklist on logout; roles: `user` (student), `staff`, `admin` |

---

## Architecture

```
┌────────────────────┐   REST + JWT    ┌──────────────────────────┐   Django ORM   ┌───────────────────┐
│  React + Vite app  │ ──────────────► │   Django REST API        │ ─────────────► │ PostgreSQL        │
│  (canteen-frontend)│                 │  • order-flow engine     │                │ (Supabase)        │
└─────────▲──────────┘                 │  • wait-time engine      │                └─────────┬─────────┘
          │                            └────────────┬─────────────┘                          │
          │          Supabase Realtime              │ Brevo email                             │
          └─────────────────────────────────────────┴─────────────────────────────────────────┘
```

- **Order-flow engine** (`order_flow.py`): promotes pending orders to preparing under the cap, with a row lock so the cap holds under simultaneous orders.
- **Wait-time engine** (`wait_time.py`, `wait_config.py`): computes queue position, start time and ready time for every open order on read. Nothing extra is stored.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 7, React Router 7, Axios, dayjs, jwt-decode, `@supabase/supabase-js` |
| Backend | Django 5.2, Django REST Framework 3.16, SimpleJWT (with token blacklist), django-cors-headers |
| Database | PostgreSQL (hosted on Supabase) via psycopg2 |
| Serving | gunicorn and WhiteNoise (backend), Vercel-style SPA rewrite (frontend) |
| Email | Brevo (API key or SMTP relay) |
| Tests | Django `TestCase` suite for the order-flow and wait-time engines |

---

## Project structure

```
.
├── canteen-frontend/              React + Vite single-page app
│   ├── src/pages/                 Auth, Home, Menu, Cart, Orders, Admin (+ analytics)
│   ├── src/config/api.js          API base URL (VITE_API_BASE_URL)
│   ├── src/supabaseClient.js      Supabase Realtime client
│   └── .env.example
├── myproject/                     Django project
│   ├── manage.py
│   ├── myproject/                 settings, root urls, wsgi/asgi
│   ├── Canteen_backend/           the app
│   │   ├── models.py              data model
│   │   ├── views.py, urls.py      REST endpoints
│   │   ├── serializers.py         incl. OrderSerializer (wait, position, priority)
│   │   ├── order_flow.py          cap, promotion, staff priority
│   │   ├── wait_time.py           estimates
│   │   ├── wait_config.py         stations, timings, caps (per canteen)
│   │   ├── notifications.py       Brevo email
│   │   ├── management/commands/   sweep_pending, sync_staff_group
│   │   └── tests_waiting_time.py  engine tests
│   ├── seed_data.py               imports backup.sql data into the database
│   ├── populate_roles.py          sets roles/groups for existing users
│   └── requirements.txt
├── backup.sql                     data snapshot
└── requirements.txt               same backend dependencies
```

---

## Getting started

### Prerequisites

- Python 3.10+ (3.12 recommended)
- Node.js 18+ and npm
- A PostgreSQL database (a local one for development, or a Supabase project)

### 1. Backend

```bash
cd myproject

# create and activate a virtual environment
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate

pip install -r requirements.txt

# create your environment file, then fill in the values (see "Environment variables")
cp .env.example .env

python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

The API is now at `http://127.0.0.1:8000/api/`.

**Optional data setup**

| Command | Purpose |
|---|---|
| `python seed_data.py` | Imports the data from `backup.sql` (canteens, products, menus, users) into the configured database |
| `python populate_roles.py` | Creates the `Staff` and `Admin` groups and assigns roles to existing users (review the usernames inside it first) |

> Both scripts write to whichever database your `.env` points at. Check it before running them, especially if that is a shared Supabase project.

### 2. Frontend

```bash
cd canteen-frontend
npm install
cp .env.example .env     # then fill in the values
npm run dev
```

The app is served at `http://localhost:5173`.

### 3. Create an admin and a staff account

Roles live in `UserProfile.role` (`user`, `staff`, `admin`). Register a normal user in the app, then set the role from the Django shell:

```bash
python manage.py shell
```
```python
from django.contrib.auth.models import User
p = User.objects.get(username="<username>").userprofile
p.role = "staff"      # or "admin"
p.save()              # saving keeps the "Staff" group in sync
```

If roles were ever changed with raw SQL or `QuerySet.update()`, re-sync the group:

```bash
python manage.py sync_staff_group --dry-run   # preview
python manage.py sync_staff_group             # apply
```

---

## Demo accounts

Use these to try each role in the app:

| Role | Username | Password | What you can do |
|---|---|---|---|
| **Admin** | `admin` | `1234567890` | Admin portal: manage menu, move orders through statuses, view analytics |
| **Staff** | `Sandeep` | `1234567890` | Order with the staff express lane (priority) |
| **Student** | `deepak` | `1234567890` | Order as a regular student |

> **Demo accounts for review and testing only.** They share a weak password. Change or remove them, and never reuse that password, before any real deployment.

---

## Environment variables

### Backend (`myproject/.env`)

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Django secret and JWT signing key. **Set a long random value; never use the default** |
| `DJANGO_DEBUG` | Debug flag |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL connection |
| `BREVO_API_KEY` | Brevo API or SMTP key for emails |
| `BREVO_SMTP_LOGIN`, `BREVO_SMTP_SERVER`, `BREVO_SMTP_PORT` | Brevo SMTP relay settings |
| `BREVO_SENDER_EMAIL`, `BREVO_SENDER_NAME` | "From" address and name on emails |

### Frontend (`canteen-frontend/.env`)

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Backend URL (`http://127.0.0.1:8000` locally) |
| `VITE_SUPABASE_URL` | Supabase project URL (for Realtime) |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon key. Only safe with Row Level Security enabled on the tables |

`.env` files are git-ignored. Never commit real secrets.

---

## How the order flow works

```
pending ──► preparing ──► prepared ──► delivered
   │            │             │
   └────────────┴─────────────┴──► cancelled   (stock restored)
```

1. A student places an order, which starts as `pending`.
2. `promote_pending` runs when an order is placed, cancelled or moved on. It starts the oldest pending orders while fewer than **15** (per canteen) are `preparing`. Quick-only orders (for example a cold drink) skip the cap.
3. **Staff** orders go straight to `preparing` (up to a limit on the express lane), still count towards the 15, and are made first at each station.
4. Admins mark orders `prepared` (which emails the student) and `delivered`.

### Waiting-time estimate

```
ready in = wait for a slot (pending only) + slowest station + packing (1 min)
```

- **Live counters** (dosa, juice): `ceil((units ahead + yours) / cooks) × minutes per unit`
- **Bulk** (biryani): plating time if portions remain, otherwise the next batch
- **Quick** items: a fixed minute

Stations, timings and item-to-station mapping live in `wait_config.py`, and can differ per canteen. Key settings: `MAX_PREPARING`, `PACKING_MINUTES`, `STAFF_MAX_EXPRESS`, `STAFF_EXPRESS_ENABLED`, `STAFF_STATION_PRIORITY`.

---

## Data model

| Table | Purpose |
|---|---|
| `auth_user`, `UserProfile` | Accounts and role (`user`, `staff`, `admin`) |
| `Canteen` | A canteen (UUID id, name, location) |
| `Product` | An item (code, name, price, type) |
| `Menu` | Product in a canteen, with its own `stock` and `is_active` (unique per canteen and product) |
| `Cart`, `CartItem` | One cart per user per canteen |
| `Order`, `OrderItem` | An order and its lines; `OrderItem.price` is a snapshot at order time |

---

## API overview

All routes are under `/api/`. Authenticated routes expect `Authorization: Bearer <access token>`.

| Group | Endpoints |
|---|---|
| **Auth** | `POST register/`, `POST login/`, `POST token/refresh/`, `POST logout/`, `GET current-user/` |
| **Browse** | `GET canteens/`, `GET canteens/<id>/menu/`, `GET canteens/<id>/wait-time/` |
| **Cart** | `POST cart/add/<canteen>/<product>`, `POST cart/update/<canteen>/<product>`, `GET cart/view/<canteen>`, `DELETE cart/remove/<canteen>/<product>/` |
| **Orders** | `POST place_order/<canteen>/`, `GET orders/`, `POST orders/cancel/<order_id>/` |
| **Admin: orders** | `GET orders/<status>/`, `GET orders/counts/`, `POST orders/move/<status>/<order_id>/` |
| **Admin: menu** | `GET admin/menu/<canteen>/`, `POST admin/menu/add/`, `POST/PUT admin/menu/update/<id>/`, `POST admin/menu/toggle/<id>/`, `DELETE admin/menu/delete/<id>/` |
| **Admin: analytics** | `GET admin/analytics/?canteen_id=...&preset=today` |

Each order returned by the API includes `status`, `queue_position`, `starts_in_minutes`, `wait_minutes`, `expected_delivery_time` and `priority`.

---

## Running the tests

```bash
cd myproject
python manage.py test Canteen_backend
```

Django creates a temporary test database. **Point `DB_*` at a local PostgreSQL** when running tests, so they never touch a shared database.

The suite covers the 15-slot cap, promotion when a slot frees, the staff express lane and its guardrail, station priority, isolation between canteens, role detection, the `sync_staff_group` command, and query counts.

---

## Deployment notes

- **Backend:** run with `gunicorn myproject.wsgi`; static files are served by WhiteNoise (`collectstatic` first). Set `DJANGO_SECRET_KEY`, turn debug off, and restrict allowed hosts and CORS origins before going live.
- **Frontend:** `npm run build` produces `dist/`; `vercel.json` rewrites all routes to `index.html` for the single-page app.
- Set `VITE_API_BASE_URL` to the deployed backend URL.

---

## Known limitations

These come from our own review and are the next items to fix:

- Demo accounts use a weak shared password and must be changed or removed before deployment.
- Order status endpoints (`move_order`, order lists) should be admin-only and scoped per canteen.
- Production settings: `DEBUG`, `ALLOWED_HOSTS` and `CORS_ALLOW_ALL_ORIGINS` are still in development mode.
- Login has no rate limiting and returns distinct messages for unknown accounts.
- Request bodies are printed in `register` and login (remove before production).
- Tokens are kept in `localStorage`; HTTP-only cookies would be safer.
- Enable Row Level Security on Supabase tables, since the frontend uses the public anon key.
- Station timings are configured, not learned. There are no per-status timestamps yet.

---

## Team

**Team name pending?** · GEN26-A0H-H017 · Genesis Hackathon
