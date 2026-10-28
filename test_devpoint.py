import requests

def get_upcoming_hackathons(limit=3):
    # Endpoint JSON de Devpost filtré sur les hackathons en ligne à venir / ouverts
    url = "https://devpost.com/api/hackathons?challenge_type[]=online&status[]=upcoming&status[]=open"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    res = requests.get(url, headers=headers, timeout=10)
    res.raise_for_status()
    data = res.json()

    hackathons = data.get("hackathons", [])[:limit]
    return hackathons

if __name__ == "__main__":
    try:
        hackathons = get_upcoming_hackathons(limit=3)
        print(f"Trouvé {len(hackathons)} hackathons sur Devpost :\n")
        
        for h in hackathons:
            title = h.get("title")
            url = h.get("url")
            prize = h.get("prize_amount", "Non précisé")
            submission_period = h.get("submission_period_dates", "Dates non précisées")
            
            print(f"🏆 {title}")
            print(f"   Dates : {submission_period}")
            print(f"   Prix  : {prize}")
            print(f"   Lien  : {url}\n")
            
    except Exception as e:
        print(f"Erreur : {e}")
