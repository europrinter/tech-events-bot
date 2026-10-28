from datetime import datetime, timezone
import json
import os
import re
import requests

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
SEEN_FILE = "seen_events.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
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

def is_usable_language(text):
    if not text:
        return True
    # Rejette les alphabets non latins : cyrillique (russe) et idéogrammes asiatiques (CJK)
    has_cyrillic = bool(re.search(r'[\u0400-\u04FF]', text))
    has_cjk = bool(re.search(r'[\u4e00-\u9fff]', text))
    return not (has_cyrillic or has_cjk)

def get_ctfs(limit=12):
    now = int(datetime.now(timezone.utc).timestamp())
    url = f"https://ctftime.org/api/v1/events/?limit={limit}&start={now}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"Erreur API CTFtime : {e}")
        return []

def get_hackathons_devpost(limit=5):
    url = "https://devpost.com/api/hackathons?challenge_type[]=online&status[]=upcoming&status[]=open"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data.get("hackathons", [])[:limit]
    except Exception as e:
        print(f"Erreur API Devpost : {e}")
        return []

def send_to_all_webhooks(embed):
    if not DISCORD_WEBHOOK_URL:
        print("Aucun webhook Discord configuré.")
        return

    urls = [u.strip() for u in DISCORD_WEBHOOK_URL.split(",") if u.strip()]

    for url in urls:
        try:
            res = requests.post(url, json={"embeds": [embed]}, timeout=10)
            if res.status_code not in (200, 204):
                print(f"Erreur d'envoi vers {url[:35]}... : code {res.status_code}")
        except requests.RequestException as e:
            print(f"Exception lors de l'envoi vers {url[:35]}... : {e}")

def main():
    seen_ids = load_seen_ids()
    new_ids = set()

    # 1. CTFtime
    for event in get_ctfs(limit=12):
        is_onsite = event.get("onsite", False)
        location = (event.get("location") or "").lower()
        title = event.get("title", "")
        description = event.get("description", "")

        # Filtre 1 : pas de présentiel hors France
        if is_onsite and ("france" not in location):
            continue

        # Filtre 2 : pays explicitement non adaptés
        banned_locations = ["russia", "belarus", "ru", "china"]
        if any(b in location for b in banned_locations):
            continue

        # Filtre 3 : rejet des caractères cyrilliques/asiatiques
        if not is_usable_language(title) or not is_usable_language(description[:150]):
            continue

        event_id = f"ctf_{event.get('id')}"
        if event_id not in seen_ids:
            new_ids.add(event_id)
            is_beginner = any(k in title.lower() for k in ["beginner", "junior", "student", "intro", "101"])
            tag = "🌱 [Débutant] " if is_beginner else ""

            embed = {
                "title": f"🚩 CTF : {tag}{title}",
                "url": event.get("url") or event.get("ctftime_url"),
                "description": "🤝 *Réagissez pour former une équipe avec d'autres étudiants !*",
                "color": 0xE74C3C,
                "fields": [
                    {"name": "Début", "value": str(event.get("start", "N/A"))[:16].replace("T", " "), "inline": True},
                    {"name": "Fin", "value": str(event.get("finish", "N/A"))[:16].replace("T", " "), "inline": True},
                    {"name": "Format", "value": "En ligne" if not is_onsite else f"Présentiel ({event.get('location')})", "inline": True},
                ],
                "footer": {"text": "CTFtime • Accessible aux étudiants"}
            }
            send_to_all_webhooks(embed)

    # 2. Devpost (100 % en ligne)
    for h in get_hackathons_devpost(limit=5):
        event_id = f"hack_{h.get('id')}"
        if event_id not in seen_ids:
            new_ids.add(event_id)
            embed = {
                "title": f"💻 Hackathon : {h.get('title')}",
                "url": h.get("url"),
                "description": "💡 *Projet en ligne • Idéal pour étoffer son portfolio GitHub.*",
                "color": 0x2ECC71,
                "fields": [
                    {"name": "💰 Cashprize / Prix", "value": h.get("prize_amount", "Non spécifié"), "inline": True},
                    {"name": "🏷️ Thèmes", "value": ", ".join([t.get("name") for t in h.get("themes", [])][:3]) or "Général", "inline": True},
                    {"name": "🤝 Recherche équipe", "value": "Discutez-en dans ce salon", "inline": False},
                ],
                "footer": {"text": "Devpost • Participation en ligne gratuite"}
            }
            send_to_all_webhooks(embed)

    if new_ids:
        seen_ids.update(new_ids)
        save_seen_ids(seen_ids)
        print(f"{len(new_ids)} nouvel(aux) événement(s) notifié(s).")
    else:
        print("Aucun nouvel événement à notifier.")

if __name__ == "__main__":
    main()
