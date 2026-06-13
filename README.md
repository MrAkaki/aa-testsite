# Alliance Auth — minimal test instance (Podman + SQLite)

A small, throwaway **Alliance Auth v5.1.4** instance for developing/testing AA plugins,
with **[allianceauth-discordbot](https://pypi.org/project/allianceauth-discordbot/)**
baked in. Deliberately bare-bones: no MariaDB, nginx, Grafana, or nginx-proxy-manager.

- **Database:** SQLite (`data/db.sqlite3`, WAL mode) — no DB container.
- **Web:** gunicorn on **http://localhost**, serving static files via WhiteNoise (no nginx).
- **Async:** one Celery worker with the beat scheduler embedded (`-B`).
- **Discord:** the `run_authbot` bot service is defined but stays stopped until you add a real token.
- **Registration:** no email required — the [`aa-skip-email`](https://gitlab.com/zima-corp/aa-skip-email) plugin removes the email step at sign-up.

> ⚠️ This is for local testing only — not a production deployment. AA officially recommends
> MySQL/MariaDB; SQLite is used here purely for simplicity.

---

## Contents

```
.
├─ .env.example         # template — copy to .env and fill in real values
├─ .env                 # your real env / secrets (gitignored — never commit)
├─ docker-compose.yml   # the 4 services: redis, gunicorn, worker(+beat), discordbot
├─ custom.dockerfile    # AA base image + extra pip packages + data/log dirs
├─ conf/
│  ├─ local.py          # Django settings overrides (SQLite, WhiteNoise, Discord, aadiscordbot, skip-email)
│  ├─ celery.py         # Celery config + task→queue routing
│  ├─ requirements.txt  # extra packages (allianceauth-discordbot, whitenoise, aa-skip-email)
│  └─ urls.py           # AA URL conf (stock)
└─ README.md
```

`conf/local.py`, `conf/celery.py`, and `conf/urls.py` are **bind-mounted** into the
containers, so editing them only needs a container **restart** (no rebuild).
`requirements.txt` / `custom.dockerfile` changes need a **rebuild**.

---

## Prerequisites

- **Podman** (tested with 5.8) with a working compose provider — check with:
  ```bash
  podman compose version
  ```
  (On this machine it resolves to the bundled `docker-compose.exe`.) The Podman machine
  must be running: `podman machine start`.
- That's it — Python/Redis/DB all live inside containers.

All commands below are **Bash** (Git Bash on Windows, or WSL), run from this folder (`c:\dev\aa-testsite`).

---

## First-time setup

```bash
# 1. Create your .env from the template, then edit it (see "What to put in .env" below)
cp .env.example .env
#    At minimum set AA_SECRET_KEY (e.g. `openssl rand -hex 24`) and your EVE ESI id/secret.

# 2. Build the custom image (AA base + allianceauth-discordbot + whitenoise)
podman compose --env-file=.env build

# 3. Start the core (redis + web) so we can initialise the database
podman compose --env-file=.env up -d redis allianceauth_gunicorn

# 4. Create the SQLite schema, collect static files, and make an admin user
podman compose --env-file=.env exec allianceauth_gunicorn python manage.py migrate
podman compose --env-file=.env exec allianceauth_gunicorn python manage.py collectstatic --noinput
podman compose --env-file=.env exec allianceauth_gunicorn python manage.py createsuperuser

# 5. Start the Celery worker (with embedded beat)
podman compose --env-file=.env up -d allianceauth_worker
```

> Run migrations **before** starting the worker — its embedded beat needs the
> `django_celery_beat` tables to exist.

### What to put in `.env`
Copy `.env.example` → `.env` and fill in:
- **`AA_SECRET_KEY`** — required. Generate a random value: `openssl rand -hex 24`.
- **`ESI_SSO_CLIENT_ID` / `ESI_SSO_CLIENT_SECRET`** — from your EVE app (see
  [Adding real credentials](#adding-real-credentials)). Leave the placeholders if you
  just want the app to boot without working EVE login for now.
- **`DISCORD_*`** — guild id, app id/secret and bot token (see
  [Adding real credentials](#adding-real-credentials)). `DISCORD_BOT_TOKEN` must stay
  **non-empty** — a dummy is fine until you have real values.

`.env` is **gitignored** — never commit it. Everything is configured here in `.env`;
[conf/local.py](conf/local.py) just reads it.

---

## Running it

```bash
# Start everything except the bot (the bot needs a real Discord token first)
podman compose --env-file=.env up -d redis allianceauth_gunicorn allianceauth_worker

# Status
podman compose --env-file=.env ps

# Logs (follow)
podman compose --env-file=.env logs -f allianceauth_gunicorn
podman compose --env-file=.env logs -f allianceauth_worker

# Stop (keeps the database + volumes)
podman compose --env-file=.env stop

# Stop and remove containers (still keeps named volumes / DB)
podman compose --env-file=.env down
```

### Access
- Site: **http://localhost**  ·  Admin: **http://localhost/admin**
- Default superuser (from setup): **`admin` / `Admin12345`**
- If a command-line tool can't reach `localhost`, use **http://127.0.0.1** — Podman
  publishes on IPv4 and some tools try IPv6 (`::1`) first. Browsers work with either.

---

## Adding real credentials

Out of the box, EVE login and the live Discord bot are **stubbed** so the app can boot.

### EVE Online SSO (needed to actually log in)
1. Create an application at <https://developers.eveonline.com> with callback URL
   **`http://localhost/sso/callback`**.
2. Put the Client ID and Secret in [.env](.env): `ESI_SSO_CLIENT_ID`, `ESI_SSO_CLIENT_SECRET`.
3. Recreate the containers so they pick up the new env:
   ```bash
   podman compose --env-file=.env up -d --force-recreate allianceauth_gunicorn allianceauth_worker
   ```

### Discord service + bot
> The AA Discord service constructs its bot client **at import time**, so
> `DISCORD_BOT_TOKEN` in [.env](.env) must always be **non-empty**.
> It currently holds a dummy value so the app starts.

1. Create an application + bot at <https://discord.com/developers/applications>:
   - OAuth2 redirect URL: **`http://localhost/discord/callback/`**
   - Enable **all three Privileged Gateway Intents** (Presence, Server Members, Message Content).
2. Set the `DISCORD_*` values in [.env](.env) — the **App ID**, **App Secret**,
   **Bot Token**, and your server's **Guild ID**.
3. Recreate web/worker and start the bot:
   ```bash
   podman compose --env-file=.env up -d --force-recreate allianceauth_gunicorn allianceauth_worker
   podman compose --env-file=.env up -d allianceauth_discordbot
   podman compose --env-file=.env logs -f allianceauth_discordbot   # should log the bot connecting
   ```
4. In AA → **Services**, click **Link Discord Server**; configure the bot in the admin
   site under **aadiscordbot**.

---

## Adding your own plugin to test

**A published / pip-installable plugin:**
1. Add the package name to [conf/requirements.txt](conf/requirements.txt).
2. Add the app to `INSTALLED_APPS` in [conf/local.py](conf/local.py).
3. Rebuild, recreate, migrate:
   ```bash
   podman compose --env-file=.env build
   podman compose --env-file=.env up -d --force-recreate allianceauth_gunicorn allianceauth_worker
   podman compose --env-file=.env exec allianceauth_gunicorn python manage.py migrate
   podman compose --env-file=.env exec allianceauth_gunicorn python manage.py collectstatic --noinput
   ```

**A plugin you're editing locally (editable install):**
1. Bind-mount the source into the base service `volumes:` in
   [docker-compose.yml](docker-compose.yml), e.g. `../my-plugin:/home/allianceauth/my-plugin`.
2. Add `RUN pip install -e /home/allianceauth/my-plugin` to [custom.dockerfile](custom.dockerfile)
   (or `pip install -e` it inside a running container).
3. Add it to `INSTALLED_APPS`, then rebuild + recreate + migrate as above. Restart the
   web/worker containers after code changes to reload.

---

## Reset / wipe

```bash
# Remove containers AND volumes (deletes the SQLite DB, static, redis data)
podman compose --env-file=.env down -v
# Then redo "First-time setup".
```

---

## Troubleshooting

- **gunicorn crash-loops / `ValueError: You must provide an access token`** — `DISCORD_BOT_TOKEN`
  in `.env` is empty. It must be non-empty (the Discord service builds its client at import
  time). Set a value and `up -d --force-recreate allianceauth_gunicorn`.
- **`exec` fails with exit 137** — the target container is restarting (usually the token issue
  above) or out of memory. Fix the boot error, or give the Podman machine more RAM
  (`podman machine stop; podman machine set --memory 6144; podman machine start`).
- **Can't reach the site from a script** — use `http://127.0.0.1` instead of `localhost`.
- **Port 80 already in use** — change the gunicorn mapping in
  [docker-compose.yml](docker-compose.yml) from `"80:8000"` to e.g. `"8000:8000"`, set
  `SITE_URL`/`CSRF_TRUSTED_ORIGINS` in `conf/local.py` to include `:8000`, and recreate.
- **`AA_DEBUG`** — AA treats *any* value as truthy, so to turn debug **off**, delete the
  `AA_DEBUG` line in [.env](.env) entirely (don't set it to `False`).
- **SQLite “database is locked”** — already mitigated with WAL + a 20s busy timeout; if it
  still bites under load, lower the worker `--concurrency` / gunicorn `--workers` in
  [docker-compose.yml](docker-compose.yml).

---

## License

Licensed under the **GNU General Public License v2** — the same license Alliance Auth
uses — see [LICENSE](LICENSE).
