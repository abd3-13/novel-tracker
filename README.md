# Novel Tracker V2

**Novel Tracker** is my personal web application for managing and tracking my novel library.

It started as a simple project for keeping track of novels I read, but over time it grew into something much more useful: a proper library manager with search, filtering, sorting, metadata synchronization, bulk selection, authentication, and a UI designed around how I actually use my library.

V2 is a rewrite/rework of the original Novel Tracker with a cleaner structure and a much better foundation for adding features without turning the codebase into a mess.

## What It Does

Novel Tracker is basically the place where I keep my novel collection organized.

It currently includes:

- 📚 **Novel library** — Browse the collection in a clean card-based layout.
- 🔎 **Search** — Quickly find novels in the library.
- 🧩 **Filters** — Build filters using different fields and operators.
- ↕️ **Sorting** — Sort the library based on available novel metadata.
- ☑️ **Selection mode** — Select multiple novels for bulk actions.
- 🔄 **Metadata synchronization** — Keep novel information up to date from external sources.
- 📋 **Live sync logs** — See what the synchronization process is actually doing.
- 🔐 **Authentication** — Keep the application behind a login.
- 🌙 **Dark UI** — Because obviously.
- 📱 **Responsive interface** — The library should remain usable at different screen sizes.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create missing tables and default settings (safe on an existing database)
flask --app app.py init-db

# Create the first account
flask --app app.py create-user admin --role admin

# Run locally
flask --app app.py run --debug
```

Configuration is read from the environment:

| Variable | Default | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | ephemeral dev key | Session signing. Required when `APP_ENV=production`. |
| `APP_ENV` | `development` | `production` requires a real secret and enables secure cookies. |
| `DATABASE_PATH` | `data/my-novels.db` | SQLite database location. |
| `NOVEL_DATA_DIR` | `data/` | Base directory used when `DATABASE_PATH` is not set. |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | Development server binding. |
| `SESSION_COOKIE_SECURE` | `1` in production | Set to `1` when serving over HTTPS. |

`flask --app app.py init-db` is additive: it creates missing tables and
settings and leaves existing library data untouched.

## Why V2?

The first version worked, but as features were added, the codebase became harder to work with.

V2 is an attempt to fix that properly rather than continuously patching V1.

The main idea is:

> **Keep the code simple, keep things separated, and don't make a small application unnecessarily complicated.**

The frontend is split into actual components and modules instead of having one giant JavaScript file doing everything. Backend responsibilities are separated as well, so adding a new feature doesn't require digging through unrelated code.

## Frontend

The frontend uses vanilla JavaScript with ES modules rather than introducing a large frontend framework.

The UI is organized around smaller pieces such as:

- Application state
- API communication
- Library rendering
- Novel cards
- Filters
- Toolbar
- Header
- Selection mode
- Synchronization/log views
- Shared utilities and configuration

Static HTML stays in HTML/templates where possible, while dynamic content is handled by JavaScript.

The goal isn't to follow some complicated frontend architecture for the sake of it. The goal is simply to make the code easy to find, understand, and change.

## Backend

The backend is built with **Flask** and handles things such as:

- Authentication
- Database access
- Novel management
- API endpoints
- Metadata synchronization
- Background/long-running operations
- Server-side application logic

The backend and frontend communicate through the application's API rather than coupling the UI directly to server-side implementation details.

## UI

The UI is built around **Tabler** and Bootstrap components.

A few principles I want to keep consistent throughout the project:

- Keep the interface clean.
- Don't overload the user with unnecessary controls.
- Keep important controls visible.
- Make large libraries easy to navigate.
- Keep layouts consistent.
- Don't make the UI look like an admin dashboard from 2009.
- If something can be made simpler, make it simpler.

The library header and toolbar are sticky so that the main controls remain available while scrolling through a large collection.

## Metadata Synchronization

One of the more important parts of Novel Tracker is metadata synchronization.

The idea is that Novel Tracker shouldn't just be a static database of novels. It should be able to retrieve and maintain useful information from external sources.

Because synchronization can involve a lot of work, V2 also includes a live log view so I can see what's happening instead of staring at a spinner wondering whether anything is actually working.

## Code Style

I'm intentionally keeping the project relatively straightforward.

There is no goal of introducing a framework, abstraction, design pattern, or dependency unless it actually solves a problem.

In general:

- Prefer readable code over clever code.
- Prefer small modules over giant files.
- Keep related functionality together.
- Avoid unnecessary abstractions.
- Don't duplicate logic when it can reasonably be shared.
- Keep HTML readable.
- Keep JavaScript readable.
- Don't sacrifice maintainability just to save a few lines.
- Make changes that fit the existing structure instead of constantly reinventing it.

Basically, the code should be understandable when I come back to it months later.

## Current Direction

V2 is still evolving.

The application is being built feature by feature, with the structure being cleaned up along the way rather than trying to design the entire system upfront.

The general direction is:

**Library → Search & Filters → Selection & Bulk Actions → Metadata → Synchronization → Better automation**

There is plenty more that can be added, but the priority is keeping the foundation solid while the application grows.

## Tech Stack

- **Python**
- **Flask**
- **JavaScript (ES Modules)**
- **HTML / CSS**
- **Bootstrap / Tabler**
- **Database-backed storage**

## The Short Version

Novel Tracker V2 is a personal novel library manager.

It is built to do one thing well:

> **Keep my novel collection organized without making me fight the application to use it.**

And yes, V2 is also an excuse to finally build the project the way I actually wanted it built instead of continuing to pile features onto V1.
