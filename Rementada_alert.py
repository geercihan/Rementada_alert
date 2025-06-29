import requests
import os
import json

API_KEY = os.getenv("FOOTBALL_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

headers = {
    "x-apisports-key": API_KEY
}

LOG_FILE = "sent_log.json"

def load_sent_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    return []

def save_sent_log(log):
    with open(LOG_FILE, "w") as f:
        json.dump(log, f)

def send_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=data)

def get_live_matches():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    response = requests.get(url, headers=headers)
    return response.json()["response"]

def get_odds_for_fixture(fixture_id):
    url = f"https://v3.football.api-sports.io/odds?fixture={fixture_id}"
    response = requests.get(url, headers=headers)
    return response.json()["response"]

def main():
    sent_log = load_sent_log()
    matches = get_live_matches()

    for match in matches:
        fixture_id = match["fixture"]["id"]
        if fixture_id in sent_log:
            continue

        fixture = match["fixture"]
        status = fixture["status"]["elapsed"]
        if status is None or status > 45:
            continue

        goals = match["goals"]
        home_goals = goals["home"]
        away_goals = goals["away"]

        if (home_goals == 2 and away_goals == 0) or (home_goals == 0 and away_goals == 2):
            leading_team = match["teams"]["home"] if home_goals > away_goals else match["teams"]["away"]
            leading_team_name = leading_team["name"]

            odds_data = get_odds_for_fixture(fixture_id)
            if not odds_data:
                continue

            try:
                bets = odds_data[0]["bookmakers"][0]["bets"]
                win_odds = next((bet["values"] for bet in bets if bet["name"] == "Match Winner"), [])
                for odd in win_odds:
                    if odd["value"] == leading_team_name:
                        if float(odd["odd"]) >= 1.40:
                            league = match.get("league", {})
                            league_name = league.get("name") or "Unknown League"
                            league_country = league.get("country") or "Unknown Country"

                            message = (
                                f"⚽️ *Rementada Alert!*\n\n"
                                f"🏟 {match['teams']['home']['name']} vs {match['teams']['away']['name']}\n"
                                f"🏆 {league_name} - {league_country}\n"
                                f"⏱ Minute: {status}'\n"
                                f"📊 Score: {home_goals} - {away_goals}\n"
                                f"💰 {leading_team_name} Win Odds: {odd['odd']}"
                            )
                            send_alert(message)
                            sent_log.append(fixture_id)
                            save_sent_log(sent_log)
                        break
            except Exception as e:
                print(f"Error parsing odds: {e}")

if __name__ == "__main__":
    main()
