# Boloman Prints

A small e-commerce site for a custom print shop: cotton, sublimated, and drifit shirts, plus mugs, tumblers, and baseball caps. Customers pick a color and size, leave print notes, and pay by cash on delivery or GCash. Staff run orders and stock from a dashboard.

## Stack

- Django 6 and PostgreSQL (`boloman_db`)
- Bootstrap 5 and vanilla JavaScript
- django-allauth for email signup and Google login
- Settings from `.env` via python-decouple

## Setup

PostgreSQL 16 needs to be running. This machine uses port **5434** because older PostgreSQL versions already listen on 5432 and 5433. A default install is often 5432 — set `DB_PORT` to match yours.

```sql
CREATE DATABASE boloman_db;
```

The database user in `.env` is `postgres`.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` (`SECRET_KEY`, database password, business details, and GCash details). Then:

```bash
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open http://127.0.0.1:8000/

`seed_demo` loads the six categories, sample products, colors, sizes, and opening stock. Run it again safely; it will not duplicate products that already exist. `python manage.py seed_demo --reset` deletes that demo catalog (including demo orders tied to it) and loads it again.

### Staff login

If no superuser exists and `DEBUG=True`, the seed command creates one:

- Email: `admin@boloman.ph`
- Password: `BolomanAdmin!2026`

Change that password. You can also create your own:

```bash
python manage.py createsuperuser
```

The custom dashboard is at http://127.0.0.1:8000/dashboard/ (staff only). Django admin remains at http://127.0.0.1:8000/admin/.

### Google login

1. In Google Cloud, create an OAuth client (Web) and set the redirect URI to `http://127.0.0.1:8000/accounts/google/login/callback/`.
2. Put the client id and secret in `.env` as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
3. Restart the server.

Until those values are set, the Google button is visible but Google will reject the login.

Password reset emails print in the terminal (`console` email backend).

## What you can do

- Shop, filter by the six categories, and open a product.
- Pick a color and size (or capacity). Stock is per combination. Out-of-stock options are disabled.
- Order Now asks guests to log in, then returns them to checkout.
- Pay cash on delivery, or GCash with a reference number and a screenshot (JPEG, PNG, or WebP, up to 5 MB).
- Watch the order move from New Order → On Process → For Deliver → Shipped → Order Completed. Customers can cancel while it is still a new order. Stock is reserved on order and returned on cancel.

## Project layout

| Path | Purpose |
| --- | --- |
| `config/` | Settings and root URLs |
| `core/` | Home page, contact messages, site settings, demo seed |
| `accounts/` | Customer profile |
| `store/` | Categories, products, photos |
| `inventory/` | Variants, SKUs, stock ledger |
| `orders/` | Checkout, payments, status history |
| `dashboard/` | Staff panel |
| `templates/` | Public site, auth, and dashboard |
| `static/` | CSS, JavaScript, and placeholder art |

## Tests

```bash
python manage.py test inventory orders
```

Tests need permission to create a database named `test_boloman_db`.
