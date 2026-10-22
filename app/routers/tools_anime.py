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
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import get_current_user

router = APIRouter(prefix="/api/tools/anime", tags=["anime"], dependencies=[Depends(get_current_user)])

_ANILIST_URL = "https://graphql.anilist.co"
_UA = "Toolbox/1.0 (private toolbox; https://github.com/KingAttack12/Toolbox)"

# Plateformes légales (vérifiées à la main). free = offre gratuite réelle.
PLATFORMS = [
    {"name": "MangaPlus (Shueisha)", "type": "manga", "free": True,
     "url": "https://mangaplus.shueisha.co.jp/",
     "note": "One Piece, Jujutsu Kaisen… gratuits et officiels, en plusieurs langues."},
    {"name": "Webtoon", "type": "manga", "free": True,
     "url": "https://www.webtoons.com/fr/",
     "note": "Webtoons officiels, gratuits, avec version française."},
    {"name": "Manga.io (Glénat)", "type": "manga", "free": True,
     "url": "https://www.manga.io/",
     "note": "Extraits et découvertes gratuites, éditeur français."},
    {"name": "France TV Slash", "type": "anime", "free": True,
     "url": "https://www.france.tv/slash/",
     "note": "Animés et séries gratuits, sans compte."},
    {"name": "ADN — Anime Digital Network", "type": "anime", "free": True,
     "url": "https://animationdigitalnetwork.com/",
     "note": "Une partie du catalogue gratuite avec un compte."},
    {"name": "Crunchyroll", "type": "anime", "free": False,
     "url": "https://www.crunchyroll.com/",
     "note": "Référence de l'animé légal ; offre gratuite limitée avec publicité."},
    {"name": "Netflix", "type": "anime", "free": False,
     "url": "https://www.netflix.com/fr/browse/genre/7424",
     "note": "Catalogue d'animés inclus dans l'abonnement."},
    {"name": "Prime Video", "type": "anime", "free": False,
     "url": "https://www.primevideo.com/",
     "note": "Animés inclus dans l'abonnement et chaînes additionnelles."},
    {"name": "Izneo", "type": "manga", "free": False,
     "url": "https://www.izneo.com/fr/",
     "note": "Manga et BD numériques légaux (achat ou abonnement)."},
]

# Domaines considérés comme éditeurs / diffuseurs officiels.
_LEGAL_DOMAINS = (
    "crunchyroll.com", "netflix.com", "primevideo.com", "amazon.com", "amazon.fr",
    "animationdigitalnetwork.com", "adn.tv", "mangaplus.shueisha.co.jp",
    "webtoons.com", "manga.io", "france.tv", "disneyplus.com", "hulu.com",
    "hidive.com", "wakanim.tv", "vrv.co", "bilibili.tv", "iq.com",
    "bookwalker.jp", "comixology.com", "izneo.com", "kana.fr", "glenat.com",
    "youtube.com", "youtu.be",
)

SORT_KEYS = ("SEARCH_MATCH", "TRENDING_DESC", "POPULARITY_DESC", "SCORE_DESC",
             "FAVOURITES_DESC", "START_DATE_DESC")
DISCOVER_SORT_KEYS = ("TRENDING_DESC", "POPULARITY_DESC", "SCORE_DESC",
                      "FAVOURITES_DESC", "START_DATE_DESC")

GENRES = ("Action", "Adventure", "Comedy", "Drama", "Ecchi", "Fantasy", "Horror",
          "Mahou Shoujo", "Mecha", "Music", "Mystery", "Psychological", "Romance",
          "Sci-Fi", "Slice of Life", "Sports", "Supernatural", "Thriller")

_SORT_MAP = {
    "SEARCH_MATCH": ["SEARCH_MATCH"],
    "TRENDING_DESC": ["TRENDING_DESC"],
    "POPULARITY_DESC": ["POPULARITY_DESC"],
    "SCORE_DESC": ["SCORE_DESC", "POPULARITY_DESC"],
    "FAVOURITES_DESC": ["FAVOURITES_DESC"],
    "START_DATE_DESC": ["START_DATE_DESC", "POPULARITY_DESC"],
}

_GQL = """
query ($q: String, $type: MediaType, $sort: [MediaSort], $genre: String, $n: Int) {
  Page(page: 1, perPage: $n) {
    media(search: $q, type: $type, sort: $sort, genre: $genre, isAdult: false) {
      id
      type
      title { romaji english native }
      coverImage { extraLarge large color }
      bannerImage
      description(asHtml: false)
      averageScore
      popularity
      favourites
      format
      status
      season
      episodes
      chapters
      volumes
      duration
      genres
      startDate { year }
      siteUrl
      trailer { id site }
      externalLinks { site url type language }
    }
  }
}
"""

_CACHE: dict[str, tuple[float, object]] = {}
_TTL = 600.0


def _cached(key: str, producer):
    now = time.monotonic()
    hit = _CACHE.get(key)
    if hit and now - hit[0] < _TTL:
        return hit[1]
    value = producer()
    if len(_CACHE) > 128:
        _CACHE.clear()
    _CACHE[key] = (now, value)
    return value


def _clean(text: str | None, limit: int = 420) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", _html.unescape(text)).strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def _is_official(url: str) -> bool:
    host = (urllib.parse.urlsplit(url).netloc or "").lower()
    return any(host == d or host.endswith("." + d) for d in _LEGAL_DOMAINS)


def _streaming(media: dict) -> list[dict]:
    out, seen = [], set()
    for link in media.get("externalLinks") or []:
        url = link.get("url") or ""
        site = link.get("site") or ""
        if link.get("type") != "STREAMING" or not url or site in seen:
            continue
        seen.add(site)
        out.append({
            "site": site,
            "url": url,
            "official": _is_official(url),
            "language": link.get("language") or "",
        })
    out.sort(key=lambda x: (not x["official"], x["site"].lower()))
    return out[:5]


def _shape(media: dict) -> dict:
    titles = media.get("title") or {}
    title = titles.get("english") or titles.get("romaji") or titles.get("native") or "?"
    alt = next((v for v in (titles.get("romaji"), titles.get("native"))
                if v and v != title), "")
    cover = media.get("coverImage") or {}
    avg = media.get("averageScore")
    trailer = media.get("trailer") or {}
    trailer_url = ""
    if trailer.get("site") == "youtube" and trailer.get("id"):
        trailer_url = f"https://www.youtube.com/watch?v={trailer['id']}"
    elif trailer.get("site") == "dailymotion" and trailer.get("id"):
        trailer_url = f"https://www.dailymotion.com/video/{trailer['id']}"
    return {
        "id": media.get("id"),
        "type": (media.get("type") or "").lower() or "anime",
        "title": title,
        "alt": alt,
        "native": titles.get("native") or "",
        "cover": cover.get("extraLarge") or cover.get("large") or "",
        "desc": _clean(media.get("description")),
        "score": round(avg / 10, 1) if avg else None,
        "popularity": media.get("popularity") or 0,
        "favourites": media.get("favourites") or 0,
        "format": media.get("format") or "",
        "status": media.get("status") or "",
        "season": media.get("season") or "",
        "episodes": media.get("episodes"),
        "chapters": media.get("chapters"),
        "volumes": media.get("volumes"),
        "duration": media.get("duration"),
        "genres": (media.get("genres") or [])[:4],
        "year": ((media.get("startDate") or {}).get("year")) or None,
        "anilist": media.get("siteUrl") or "",
        "trailer": trailer_url,
        "streaming": _streaming(media),
    }


def _anilist(query: str | None, media_type: str, sort: str, genre: str | None, n: int) -> list[dict]:
    body = json.dumps({
        "query": _GQL,
        "variables": {
            "q": query or None,
            "type": media_type.upper(),
            "sort": _SORT_MAP.get(sort, ["SEARCH_MATCH"]),
            "genre": genre or None,
            "n": n,
        },
    }).encode()
    req = urllib.request.Request(
        _ANILIST_URL, data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": _UA},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise HTTPException(status_code=429, detail="AniList est saturé, réessayez dans une minute.")
        raise HTTPException(status_code=502, detail="AniList injoignable pour le moment.")
    except Exception:
        raise HTTPException(status_code=502, detail="AniList injoignable pour le moment.")
    if data.get("errors"):
        raise HTTPException(status_code=502, detail="Réponse AniList invalide.")
    media = ((data.get("data") or {}).get("Page") or {}).get("media") or []
    return [_shape(m) for m in media]


def _check_genre(genre: str | None) -> str | None:
    if not genre:
        return None
    for g in GENRES:
        if g.lower() == genre.strip().lower():
            return g
    raise HTTPException(status_code=400, detail="Genre inconnu.")


class SearchIn(BaseModel):
    query: str = Field(min_length=2, max_length=100)
    type: Literal["anime", "manga"] = "anime"
    sort: Literal["SEARCH_MATCH", "TRENDING_DESC", "POPULARITY_DESC", "SCORE_DESC",
                  "FAVOURITES_DESC", "START_DATE_DESC"] = "SEARCH_MATCH"
    genre: str | None = None


@router.get("/legal")
def legal():
    return {"platforms": PLATFORMS, "free": [p for p in PLATFORMS if p["free"]],
            "paid": [p for p in PLATFORMS if not p["free"]]}


@router.get("/options")
def options():
    return {"sorts": list(SORT_KEYS), "discoverSorts": list(DISCOVER_SORT_KEYS), "genres": list(GENRES)}


@router.post("/search")
def search(payload: SearchIn):
    query = payload.query.strip()
    if len(query) < 2:
        raise HTTPException(status_code=400, detail="Titre trop court (2 lettres minimum).")
    genre = _check_genre(payload.genre)
    key = f"search:{payload.type}:{payload.sort}:{genre}:{query.lower()}"
    results = _cached(key, lambda: _anilist(query, payload.type, payload.sort, genre, 12))
    if not results:
        raise HTTPException(status_code=404, detail="Rien trouvé. Essayez le titre original (romaji).")
    return {"type": payload.type, "query": query, "count": len(results),
            "source": "AniList", "results": results}


@router.get("/discover")
def discover(
    type: Literal["anime", "manga"] = "anime",
    sort: Literal["TRENDING_DESC", "POPULARITY_DESC", "SCORE_DESC",
                  "FAVOURITES_DESC", "START_DATE_DESC"] = "TRENDING_DESC",
    genre: str | None = None,
    limit: int = Query(10, ge=1, le=24),
):
    genre = _check_genre(genre)
    key = f"discover:{type}:{sort}:{genre}:{limit}"
    results = _cached(key, lambda: _anilist(None, type, sort, genre, limit))
    return {"type": type, "count": len(results), "source": "AniList", "results": results}
