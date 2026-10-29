"""Settings partilhados por todos os ambientes · settings shared by every environment.

PT: tudo o que é igual em dev, test e prod vive aqui; o que muda vem do ambiente
(`.env`, nunca no git). EN: everything identical across dev, test and prod lives
here; whatever differs comes from the environment (`.env`, never in git).
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")          # sem default: sem SECRET_KEY a app não arranca
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # apps do projeto · project apps
    "accounts",
    "core",
    "shop",
    # bibliotecas · third-party
    "corsheaders",                                  # Ficha 03 · Parte 3: CORS
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",     # Ficha 03 · Parte 1: blacklist
]

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    # Ficha 03 · Parte 1: JWT primeiro (pedido sem credenciais → 401, não 403)
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Ficha 03 · Parte 1: tudo fechado por omissão; abre-se endpoint a endpoint
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # Ficha 03 · Parte 3: limites por "scope" (usados com ScopedRateThrottle)
    "DEFAULT_THROTTLE_RATES": {
        "auth": "10/minute",    # login: 10 tentativas por minuto por IP
    },
}

SPECTACULAR_SETTINGS = {"TITLE": "Loja DWFA API", "VERSION": "1.0.0"}

MIDDLEWARE = [
    # Ficha 03 · Parte 3: TEM de ser o primeiro — o preflight OPTIONS não traz token
    # e não pode ser bloqueado por outro middleware antes de receber os cabeçalhos CORS.
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Ficha 03 · Parte 3: só estas origens podem ler respostas da API num browser.
# Uma lista por ambiente, vinda do .env; nunca CORS_ALLOW_ALL_ORIGINS fora de dev.
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:5173"])
CORS_URLS_REGEX = r"^/api/.*$"      # só a API; o /admin/ fica de fora

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {"default": env.db("DATABASE_URL")}

# Modelo de utilizador próprio desde o primeiro dia · custom user model from day one
AUTH_USER_MODEL = "accounts.User"

# Ficha 03 · Parte 3: Argon2 para passwords novas; PBKDF2 continua a validar as antigas
# (e o Django converte-as para Argon2 no próximo login).
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},          # Ficha 03 · Parte 3 (era 8)
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Lisbon"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Ficha 03 · Parte 1: tempos de vida e rotação dos tokens
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,      # cada refresh devolve um refresh novo
    "BLACKLIST_AFTER_ROTATION": True,   # o refresh antigo deixa de servir
    "UPDATE_LAST_LOGIN": True,
}