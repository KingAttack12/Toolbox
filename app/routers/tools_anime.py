"""Recherche animés/mangas 100 % légale — métadonnées via AniList (API
publique gratuite, sans clé) + liste éditoriale de plateformes gratuites
et officielles (MangaPlus, ADN, France TV Slash...).

Aucun lien pirate : uniquement des fiches + renvois vers les offres
légales déclarées par AniList (externalLinks) et la liste curated.
"""
from __future__ import annotations

import html as _html
import json
import re
import urllib.error
import urllib.request
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import get_current_user

router = APIRouter(prefix="/api/tools/anime", tags=["anime"], dependencies=[Depends(get_current_user)])

_ANILIST_URL = "https://graphql.anilist.co"

# Plateformes légales avec offre gratuite (vérifiées à la main).
LEGAL_FREE = [
    {"name": "MangaPlus (Shueisha)", "type": "manga", "url": "https://mangaplus.shueisha.co.jp/",
     "note": "One Piece, Jujutsu Kaisen... gratuits et officiels, en anglais/espagnol."},
    {"name": "ADN — Anime Digital Network", "type": "anime", "url": "https://animationdigitalnetwork.com/",
     "note": "Une partie du catalogue gratuite (avec compte)."},
    {"name": "France TV Slash", "type": "anime", "url": "https://www.france.tv/slash/",
     "note": "Séries et animés gratuits, sans compte."},
    {"name": "Crunchyroll", "type": "anime", "url": "https://www.crunchyroll.com/",
     "note": "Essentiellement premium aujourd'hui ; catalogue légal de référence."},
    {"name": "Webtoon", "type": "manga", "url": "https://www.webtoons.com/fr/",
     "note": "Webtoons gratuits et officiels."},
    {"name": "Manga.io (Glénat)", "type": "manga", "url": "https://www.manga.io/",
     "note": "Extraits et découvertes gratuites, éditeur français."},
]

_GQL = """
query ($q: String, $type: MediaType, $n: Int) {
  Page(perPage: $n) {
    media(search: $q, type: $type, sort: SEARCH_MATCH) {
      title { romaji english native }
      coverImage { large }
      description(asHtml: false)
      averageScore format status
      episodes chapters volumes startDate { year }
      siteUrl externalLinks { site url type }
    }
  }
}
"""


def _clean(text: str | None, limit: int = 600) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = _html.unescape(text).strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


class SearchIn(BaseModel):
    query: str = Field(min_length=2, max_length=100)
    type: Literal["anime", "manga"] = "anime"


@router.get("/legal")
def legal():
    return {"platforms": LEGAL_FREE}


@router.post("/search")
def search(payload: SearchIn):
    query = payload.query.strip()
    if len(query) < 2:
        raise HTTPException(status_code=400, detail="Titre trop court (2 lettres min).")
    body = json.dumps({
        "query": _GQL,
        "variables": {"q": query, "type": payload.type.upper(), "n": 8},
    }).encode()
    req = urllib.request.Request(
        _ANILIST_URL, data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "Toolbox/1.0 (private toolbox; https://github.com/KingAttack12/Toolbox)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise HTTPException(status_code=429, detail="AniList saturé, réessayez dans une minute.")
        raise HTTPException(status_code=502, detail="AniList injoignable pour le moment.")
    except Exception:
        raise HTTPException(status_code=502, detail="AniList injoignable pour le moment.")
    results = []
    for m in ((data.get("data") or {}).get("Page") or {}).get("media") or []:
        title = (m.get("title") or {})
        links = [
            {"site": l.get("site"), "url": l.get("url")}
            for l in (m.get("externalLinks") or [])
            if l.get("type") == "STREAMING" and l.get("url")
        ][:6]
        results.append({
            "title": title.get("english") or title.get("romaji") or title.get("native") or "?",
            "native": title.get("native") or "",
            "cover": ((m.get("coverImage") or {}).get("large")) or "",
            "desc": _clean(m.get("description")),
            "score": (m.get("averageScore") or 0) / 10 if m.get("averageScore") else None,
            "format": m.get("format") or "?",
            "episodes": m.get("episodes") or m.get("chapters") or "?",
            "year": ((m.get("startDate") or {}).get("year")) or "?",
            "anilist": m.get("siteUrl") or "",
            "streaming": links,
        })
    if not results:
        raise HTTPException(status_code=404, detail="Rien trouvé. Essayez le titre original (romaji).")
    return {"results": results}
