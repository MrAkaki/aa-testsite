# Every setting in base.py can be overloaded by redefining it here.
from .base import *

SECRET_KEY = os.environ.get("AA_SECRET_KEY")
SITE_NAME = os.environ.get("AA_SITENAME")
SITE_URL = (
    f"{os.environ.get('PROTOCOL')}"
    f"{os.environ.get('AUTH_SUBDOMAIN')}."
    f"{os.environ.get('DOMAIN')}"
)
CSRF_TRUSTED_ORIGINS = [SITE_URL]
DEBUG = os.environ.get("AA_DEBUG", False)
# MariaDB (the 'mariadb' compose service). Switched off SQLite because some plugins
# run heavy queries/joins that SQLite handles poorly under concurrent worker access.
# Credentials come from .env; mysqlclient ships in the base AA image already.
DATABASES["default"] = {
    "ENGINE": "django.db.backends.mysql",
    "NAME": os.environ.get("AA_DB_NAME", "alliance_auth"),
    "USER": os.environ.get("AA_DB_USER", "allianceauth"),
    "PASSWORD": os.environ.get("AA_DB_PASSWORD", "allianceauth"),
    "HOST": os.environ.get("AA_DB_HOST", "mariadb"),
    "PORT": os.environ.get("AA_DB_PORT", "3306"),
    "OPTIONS": {"charset": "utf8mb4"},
}
EVEUNIVERSE_LOAD_TYPE_MATERIALS = True
# Register an application at https://developers.eveonline.com for Authentication
# & API Access and fill out these settings. Be sure to set the callback URL
# to https://example.com/sso/callback substituting your domain for example.com
# Logging in to auth requires the publicData scope (can be overridden through the
# LOGIN_TOKEN_SCOPES setting). Other apps may require more (see their docs).
ESI_SSO_CALLBACK_URL = f"{SITE_URL}/sso/callback"  # Do NOT change this line!
ESI_SSO_CLIENT_ID = os.environ.get("ESI_SSO_CLIENT_ID")
ESI_SSO_CLIENT_SECRET = os.environ.get("ESI_SSO_CLIENT_SECRET")
ESI_USER_CONTACT_EMAIL = os.environ.get(
    "ESI_USER_CONTACT_EMAIL"
)  # A server maintainer that CCP can contact in case of issues.

# Registration without email: the aa-skip-email plugin's SkipEmailBackend (below) assigns
# placeholder addresses so new users never see an email step. Override the placeholder
# domain (default "no-email.invalid") with AA_SKIP_EMAIL_DOMAIN if you like.
# REGISTRATION_VERIFY_EMAIL=False also skips the verification email if any flow triggers it.
REGISTRATION_VERIFY_EMAIL = False
AUTHENTICATION_BACKENDS = [
    "aa_skip_email.authentication.backends.SkipEmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]

ROOT_URLCONF = "myauth.urls"
WSGI_APPLICATION = "myauth.wsgi.application"
STATIC_ROOT = "/var/www/myauth/static/"
BROKER_URL = f"redis://{os.environ.get('AA_REDIS', 'redis:6379')}/0"
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{os.environ.get('AA_REDIS', 'redis:6379')}/1",  # change the 1 here to change the database used
    }
}


# Add any additional apps to this list.
INSTALLED_APPS += [
    'allianceauth.services.modules.discord',
    'aadiscordbot',
    'aa_skip_email',
]

#######################################
# Add any custom settings below here. #
#######################################

# --- Local test box only (do NOT use these in production) ---
# gunicorn is exposed directly on http://localhost (host port 80 -> container 8000),
# with no nginx, so override SITE_URL to match what the browser uses (CSRF + callbacks).
ALLOWED_HOSTS = ["*"]
SITE_URL = "http://localhost"
CSRF_TRUSTED_ORIGINS = ["http://localhost", "http://127.0.0.1"]
ESI_SSO_CALLBACK_URL = f"{SITE_URL}/sso/callback"

# Serve static files straight from gunicorn via WhiteNoise (no nginx container).
# Run `collectstatic` once so STATIC_ROOT is populated.
if "whitenoise.middleware.WhiteNoiseMiddleware" not in MIDDLEWARE:
    try:
        _wn_idx = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1
    except ValueError:
        _wn_idx = 0
    MIDDLEWARE.insert(_wn_idx, "whitenoise.middleware.WhiteNoiseMiddleware")

###############################################
# Discord service (allianceauth ... discord)  #
###############################################
# Create a Discord application at https://discord.com/developers/applications and:
#   - OAuth2 redirect URL: http://localhost/discord/callback/
#   - Enable ALL three Privileged Gateway Intents (Presence, Server Members, Message Content)
# Fill these in, recreate the containers, then enable the service on AA's Services page
# and click "Link Discord Server". Empty values = service installed but dormant.
# Discord credentials are read from the environment — set them in .env.
# IMPORTANT: the Discord service builds a bot client at import time, so DISCORD_BOT_TOKEN
# MUST be NON-EMPTY or the whole app fails to load (ValueError: must provide an access
# token). The `or` fallback guarantees a non-empty value so the app always boots; put a
# real token in .env (and recreate the containers) to actually connect Discord.
DISCORD_GUILD_ID = os.environ.get("DISCORD_GUILD_ID", "")
DISCORD_APP_ID = os.environ.get("DISCORD_APP_ID", "")
DISCORD_APP_SECRET = os.environ.get("DISCORD_APP_SECRET", "")
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN") or "placeholder-bot-token"
DISCORD_CALLBACK_URL = f"{SITE_URL}/discord/callback/"
DISCORD_SYNC_NAMES = False

###############################################
# allianceauth-discordbot (aadiscordbot)      #
###############################################
# Placeholder IDs so the app imports/migrates cleanly. Replace with real Discord
# channel IDs and EVE Online IDs before using bot commands.
ADMIN_DISCORD_BOT_CHANNELS = [1234567890]
SOV_DISCORD_BOT_CHANNELS = [1234567890]
ADM_DISCORD_BOT_CHANNELS = [1234567890]
RECRUIT_CHANNEL_ID = 1234567890
RECRUITER_GROUP_ID = 1234567890

DISCORD_BOT_SOV_STRUCTURE_OWNER_IDS = [1000169]
DISCORD_BOT_MEMBER_ALLIANCES = [1234567890]

DISCORD_BOT_ADM_REGIONS = [10000002]
DISCORD_BOT_ADM_SYSTEMS = [30000142]
DISCORD_BOT_ADM_CONSTELLATIONS = [20000020]

PRICE_CHECK_HOSTNAME = "evepraisal.com"

# aadiscordbot dedicated log file (uses AA's existing 'verbose' formatter)
LOGGING["handlers"]["bot_log_file"] = {
    "level": "INFO",
    "class": "logging.handlers.RotatingFileHandler",
    "filename": os.path.join(BASE_DIR, "log/discord_bot.log"),
    "formatter": "verbose",
    "maxBytes": 1024 * 1024 * 5,
    "backupCount": 5,
}
LOGGING["loggers"]["aadiscordbot"] = {
    "handlers": ["bot_log_file"],
    "level": "DEBUG",
}
