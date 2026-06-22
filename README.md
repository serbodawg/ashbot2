# AshBot 2

Futurystyczny, wielofunkcyjny bot Discord — ochrona, moderacja, AI, poziomy, backup serwera i dashboard.

## Funkcje

- **Administracja** — zarządzanie kanałami i kategoriami
- **Moderacja** — warny, timeout, kick, ban, tempban, purge, slowmode
- **AutoMod** — antyspam, antylink, antyraid, antycaps, antymention, antyinvite
- **AI Chat** — rozmowa z botem, kontekst kanału, komenda /ask
- **Advice** — losowe porady z bazy, zarządzanie poradami
- **Levels** — XP za wiadomości, poziomy, ranking, role za level
- **Ochrona** — Anti-Nuke (masowe akcje), Anti-Bot (whitelist/blacklist)
- **Backup** — pełny backup kanałów/rol/uprawnień, auto co 48h
- **Logi** — osobne kanały dla każdego typu zdarzeń
- **Dashboard** — FastAPI web UI z statystykami

## Wymagania

- Python 3.13+
- Supabase project (konto i klucz service_role)

## Instalacja

```bash
git clone <repo>
cd AshBot2
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Wypełnij `.env`:

```
DISCORD_TOKEN=twój_token_bota
SUPABASE_SERVICE_ROLE_KEY=klucz_service_role_z_supabase
AI_API_KEY=opcjonalnie_klucz_do_openai
DASHBOARD_SECRET=losowy_sekret_do_dashboardu
```

## Baza danych (Supabase)

W Supabase SQL Editor uruchom zawartość `schema.sql` — utworzy wszystkie tabele.

## Uruchomienie

```bash
python3 main.py
```

Dashboard będzie dostępny pod `http://localhost:8080?secret=twój_sekret`.

## Struktura projektu

```
AshBot2/
├── main.py                  # Entry point
├── config.py                # Konfiguracja z .env
├── schema.sql               # Tabele Supabase
├── generate_logo.py         # Generator logo
├── requirements.txt
├── pyproject.toml
├── .env.example
├── ashbot/
│   ├── bot.py               # Klasa bota
│   ├── cogs/
│   │   ├── admin.py         # Zarządzanie kanałami
│   │   ├── moderation.py    # Warn/kick/ban/purge
│   │   ├── automod.py       # Auto-moderation
│   │   ├── ai_cog.py        # AI chat
│   │   ├── advice_cog.py    # Porady
│   │   ├── levels.py        # XP i poziomy
│   │   ├── protection.py    # Anti-nuke, anti-bot
│   │   ├── backups.py       # Backup serwera
│   │   └── logs_cog.py      # System logów
│   ├── models/
│   │   └── database.py      # Warstwa dostępu do Supabase
│   ├── utils/
│   │   ├── permissions.py   # Sprawdzanie uprawnień
│   │   └── embeds.py        # Pomocniki embedów
│   ├── dashboard/
│   │   └── server.py        # FastAPI dashboard
│   └── templates/
│       └── dashboard.html   # HTML dashboardu
├── data/
├── logs/
└── backups/
```
