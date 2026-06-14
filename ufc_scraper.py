import aiohttp
from bs4 import BeautifulSoup
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

# Méthodes de victoire UFC
METHODS = ["KO/TKO", "Soumission", "Décision unanime", "Décision partagée", "Décision majoritaire", "No Contest"]
METHODS_SHORT = {"KO/TKO": "KO", "Soumission": "SUB", "Décision unanime": "DEC", "Décision partagée": "DEC", "Décision majoritaire": "DEC"}


async def get_next_event():
    """Scrape le prochain événement UFC depuis le site officiel"""
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get("https://www.ufc.com/events", timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    logger.warning(f"UFC.com status: {resp.status}")
                    return None
                
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                
                # Chercher le prochain event
                event_cards = soup.find_all("div", class_=re.compile(r"c-card-event--result"))
                
                for card in event_cards:
                    # Vérifier si c'est un événement futur
                    date_tag = card.find("div", class_=re.compile(r"c-card-event--result__date"))
                    if not date_tag:
                        continue
                    
                    name_tag = card.find("h3", class_=re.compile(r"c-card-event--result__headline"))
                    if not name_tag:
                        name_tag = card.find("div", class_=re.compile(r"c-card-event--result__headline"))
                    
                    location_tag = card.find("div", class_=re.compile(r"c-card-event--result__location"))
                    
                    link_tag = card.find("a", href=True)
                    
                    if name_tag:
                        event_name = name_tag.get_text(strip=True)
                        event_date = date_tag.get_text(strip=True)
                        event_location = location_tag.get_text(strip=True) if location_tag else ""
                        event_url = f"https://www.ufc.com{link_tag['href']}" if link_tag else None
                        
                        fights = []
                        if event_url:
                            fights = await get_event_fights(session, event_url)
                        
                        return {
                            "name": event_name,
                            "date": event_date,
                            "location": event_location,
                            "url": event_url,
                            "fights": fights
                        }
        
        return None
    
    except Exception as e:
        logger.error(f"Erreur scraping UFC.com: {e}")
        return None


async def get_event_fights(session, event_url):
    """Récupère les combats d'un événement UFC"""
    fights = []
    try:
        async with session.get(event_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return fights
            
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            
            fight_cards = soup.find_all("div", class_=re.compile(r"c-listing-fight"))
            
            for i, card in enumerate(fight_cards):
                fighters = card.find_all("div", class_=re.compile(r"c-listing-fight__corner-name"))
                
                if len(fighters) >= 2:
                    f1 = fighters[0].get_text(strip=True).replace("\n", " ").strip()
                    f2 = fighters[1].get_text(strip=True).replace("\n", " ").strip()
                    
                    weight_tag = card.find("div", class_=re.compile(r"c-listing-fight__class-text"))
                    weight = weight_tag.get_text(strip=True) if weight_tag else ""
                    
                    # Détecter si c'est le main event (premier combat = main event)
                    is_main = (i == 0)
                    
                    # Rounds : title fights = 5, reste = 3
                    max_rounds = 5 if ("Title" in weight or i == 0) else 3
                    
                    fights.append({
                        "fighter1": f1,
                        "fighter2": f2,
                        "weight_class": weight,
                        "is_main_event": is_main,
                        "max_rounds": max_rounds,
                        "position": len(fight_cards) - i
                    })
    
    except Exception as e:
        logger.error(f"Erreur scraping combats: {e}")
    
    return fights


async def search_ufc_event(query):
    """Recherche un événement UFC par nom (fallback)"""
    try:
        search_url = f"https://www.ufc.com/events?search={query.replace(' ', '+')}"
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(search_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    name_tag = soup.find("h3", class_=re.compile(r"c-card-event--result__headline"))
                    if name_tag:
                        return name_tag.get_text(strip=True)
        return None
    except:
        return None
