"""
Prüft einmal, ob im Online-Terminportal ein Termin frei ist, und schickt
bei Erfolg eine Push-Nachricht über ntfy. Gedacht für GitHub Actions.

Alle persönlichen Angaben kommen aus Umgebungsvariablen (GitHub Secrets):
  PORTAL_URL, NTFY_TOPIC, TERMINART, KEINE_TERMINE_HINWEIS
"""
import os
import sys
import urllib.request

from playwright.sync_api import sync_playwright

URL = os.environ["PORTAL_URL"]
NTFY_TOPIC = os.environ["NTFY_TOPIC"]
TERMINART = os.environ["TERMINART"]
KEINE_TERMINE_HINWEIS = os.environ["KEINE_TERMINE_HINWEIS"].strip().lower()
NUR_TEST = os.environ.get("NUR_TEST") == "1"


def benachrichtigen(text):
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=text.encode("utf-8"),
        headers={"Title": "Termin moeglicherweise frei"},
    )
    urllib.request.urlopen(req, timeout=15)


def dropdown_waehlen(page, select_id, option_text):
    sel = page.locator(f"#{select_id}")
    sel.wait_for(state="attached", timeout=20000)
    optionen = sel.locator("option").all_text_contents()
    index = next((i for i, t in enumerate(optionen) if t.strip() == option_text), None)
    if index is None:
        raise RuntimeError("Option im Dropdown nicht gefunden")
    sel.select_option(index=index, force=True)
    page.wait_for_timeout(800)


def seite_pruefen():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        dropdown_waehlen(page, "input_service", TERMINART)
        dropdown_waehlen(page, "input_practitioner", "Alle")
        page.get_by_role("button", name="Termine suchen").click(timeout=15000)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)
        text = page.inner_text("body")
        browser.close()
        return text


def main():
    if NUR_TEST:
        benachrichtigen("Testnachricht vom GitHub-Terminskript")
        print("Testnachricht gesendet.")
        return

    try:
        text = seite_pruefen()
    except Exception as e:
        # Nur den Fehlertyp ausgeben, damit nichts Persönliches im öffentlichen Log landet
        print("Fehler beim Prüfen:", type(e).__name__)
        return

    if KEINE_TERMINE_HINWEIS in text.lower():
        print("nichts frei")
    else:
        print("frei")
        try:
            benachrichtigen("Beim gesuchten Termin scheint etwas frei zu sein. Bitte Portal öffnen!")
        except Exception as e:
            print("Benachrichtigung fehlgeschlagen:", type(e).__name__)
            sys.exit(1)


if __name__ == "__main__":
    main()
