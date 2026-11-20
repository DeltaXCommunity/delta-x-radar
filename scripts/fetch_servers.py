"""DELTA X RADAR — actualiza data/servers.json con la lista real de servidores
públicos de Steal An Egg desde la API pública de Roblox.

Se ejecuta desde GitHub Actions cada 5 minutos. Solo usa la librería estándar
de Python. Si la API falla, NO sobrescribe el archivo anterior: la página
sigue mostrando los últimos datos buenos con su antigüedad.
"""
import json
import os
import time
import urllib.error
import urllib.request

PLACE_ID = "107778070777162"
BASE = "https://games.roblox.com/v1/games/{}/servers/Public".format(PLACE_ID)


def fetch_page(cursor=None, order="Asc"):
    url = BASE + "?sortOrder=" + order + "&limit=100"
    if cursor:
        url += "&cursor=" + cursor
    req = urllib.request.Request(url, headers={"User-Agent": "DELTA-X-RADAR/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def fetch_pages(order, count):
    """Devuelve hasta count páginas en el orden dado (Asc = más vacíos)."""
    out = []
    cursor = None
    for _ in range(count):
        try:
            data = fetch_page(cursor, order)
        except urllib.error.HTTPError as exc:
            if exc.code == 429:  # límite de Roblox: esperar y reintentar una vez
                time.sleep(10)
                data = fetch_page(cursor, order)
            else:
                raise
        out.extend(data.get("data", []))
        cursor = data.get("nextPageCursor")
        if not cursor:
            break
    return out


def main():
    # Mezcla: primero los servidores con espacio (Asc) y luego algunos
    # llenos (Desc), para que la lista sirva para entrar y para mirar.
    raw = fetch_pages("Asc", 2) + fetch_pages("Desc", 1)
    seen = set()
    servers = []
    for s in raw:
        if s.get("id") in seen:
            continue
        seen.add(s.get("id"))
        servers.append({
            "id": s.get("id"),
            "playing": s.get("playing"),
            "maxPlayers": s.get("maxPlayers"),
            "fps": s.get("fps"),
            "ping": s.get("ping"),
            "name": s.get("name"),
            "players": [
                {"id": p.get("id"), "name": p.get("name"),
                 "displayName": p.get("displayName")}
                for p in s.get("players", [])
            ],
        })

    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "place_id": PLACE_ID,
        "count": len(servers),
        "servers": servers,
    }
    os.makedirs("data", exist_ok=True)
    with open("data/servers.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print("wrote {} servers".format(len(servers)))


if __name__ == "__main__":
    main()
