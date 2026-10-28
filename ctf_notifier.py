from datetime import datetime, timezone
import json
import os
import requests

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
SEEN_FILE = "seen_events.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def load_seen_ids():
    if not os.path.exists(SEEN_FILE):
        return set()
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, IOError):
        return set()

def save_seen_ids(seen_ids):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen_ids), f, indent=2)

def get_ctfs(limit=5):
    now = int(datetime.now(timezone.utc).timestamp())
    url = f"https://ctftime.org/api/v1/events/?limit={limit}&start={now}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"Erreur API CTFtime : {e}")
        return []

def get_hackathons(limit=5):
    url = "https://devpost.com/api/hackathons?challenge_type[]=online&status[]=upcoming&status[]=open"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data.get("hackathons", [])[:limit]
    except Exception as e:
        print(f"Erreur API Devpost : {e}")
        return []

def build_ctf_embed(event):
    start_raw = event.get("start", "")
    start_fmt = "Date non précisée"
    if start_raw:
        dt = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
        start_fmt = dt.strftime("%d/%m/%Y à %H:%M UTC")

    return {
        "title": f"🚩 CTF : {event.get('title', 'Sans titre')}",
        "url": event.get("ctftime_url", "https://ctftime.org"),
        "color": 0x3498DB,  # Bleu
        "fields": [
            {"name": "Format", "value": event.get("format", "N/A"), "inline": True},
            {"name": "Type", "value": "En ligne" if event.get("onsite") is False else "Présentiel", "inline": True},
            {"name": "Début", "value": start_fmt, "inline": False},
            {"name": "Lien officiel", "value": f"[Accéder au site]({event.get('url')})" if event.get("url") else "Non renseigné", "inline": False}
        ],
        "footer": {"text": f"Source : CTFtime • Poids : {event.get('weight', 0)}"}
    }

def build_hackathon_embed(event):
    prize = event.get("prize_amount", "Non précisé")
    dates = event.get("submission_period_dates", "Dates non précisées")
    url = event.get("url", "https://devpost.com")

    return {
        "title": f"🏆 Hackathon : {event.get('title', 'Sans titre')}",
        "url": url,
        "color": 0x9B59B6,  # Violet
        "fields": [
            {"name": "Période", "value": dates, "inline": False},
            {"name": "Prix / Cashprize", "value": prize, "inline": True},
            {"name": "Lien d'inscription", "value": f"[Participer sur Devpost]({url})", "inline": False}
        ],
        "footer": {"text": "Source : Devpost"}
    }

def main():
    seen_ids = load_seen_ids()
    embeds = []
    new_ids = set()

    # 1. Traitement des CTF
    for ctf in get_ctfs(limit=5):
        ctf_id = f"ctf_{ctf.get('id')}"
        if ctf_id not in seen_ids:
            embeds.append(build_ctf_embed(ctf))
            new_ids.add(ctf_id)

    # 2. Traitement des Hackathons
    for h in get_hackathons(limit=5):
        h_id = f"hackathon_{h.get('id')}"
        if h_id not in seen_ids:
            embeds.append(build_hackathon_embed(h))
            new_ids.add(h_id)

    if not embeds:
        print("Aucun nouvel événement à notifier.")
        return

    # Discord limite à 10 embeds par message
    payload = {
        "content": f"⚡ **{len(embeds)} nouvel(aux) événement(s) tech détecté(s) :**",
        "embeds": embeds[:10]
    }

    try:
        res = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        res.raise_for_status()
        seen_ids.update(new_ids)
        save_seen_ids(seen_ids)
        print(f"{len(embeds)} alertes envoyées avec succès.")
    except Exception as e:
        print(f"Erreur d'envoi Discord : {e}")

if __name__ == "__main__":
    main()
