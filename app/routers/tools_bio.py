"""Outils bioinformatiques — 100 % local, validation stricte des séquences."""
from __future__ import annotations

import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .. import config
from ..auth import get_current_user

router = APIRouter(prefix="/api/tools/bio", tags=["bio"], dependencies=[Depends(get_current_user)])

_SEQ_RE = re.compile(r"^[ATCGUatcgu\s\n\r]+$")
_MOTIF_RE = re.compile(r"^[ATCGUatcgu]+$")

CODON_TABLE = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}


def _clean_seq(seq: str) -> str:
    s = re.sub(r"\s+", "", seq).upper().replace("U", "T")
    if not s:
        raise HTTPException(status_code=400, detail="Séquence vide.")
    if len(s) > config.MAX_TEXT_CHARS:
        raise HTTPException(status_code=413, detail="Séquence trop longue.")
    if not _SEQ_RE.match(seq) or re.search(r"[^ATCGUatcgu\s\n\r]", seq):
        raise HTTPException(status_code=400, detail="Séquence invalide (autorisé : A T C G U).")
    return s


def _gc_stats(s: str) -> dict:
    gc = s.count("G") + s.count("C")
    at = s.count("A") + s.count("T")
    return {
        "length": len(s),
        "gc_count": gc,
        "at_count": at,
        "gc_percent": round(gc / len(s) * 100, 2),
        "at_percent": round(at / len(s) * 100, 2),
    }


class SeqIn(BaseModel):
    sequence: str = Field(max_length=600_000)


@router.post("/gc")
def gc(payload: SeqIn):
    return _gc_stats(_clean_seq(payload.sequence))


@router.post("/transcribe")
def transcribe(payload: SeqIn):
    s = _clean_seq(payload.sequence)
    return {"result": s.replace("T", "U"), **_gc_stats(s)}


@router.post("/translate")
def translate(payload: SeqIn):
    s = _clean_seq(payload.sequence)
    prot = "".join(CODON_TABLE.get(s[i:i + 3], "?") for i in range(0, len(s) - len(s) % 3, 3))
    return {"result": prot, "codons": len(s) // 3, "incomplete_tail": len(s) % 3}


class MotifIn(BaseModel):
    sequence: str = Field(max_length=600_000)
    motif: str = Field(max_length=1000)


@router.post("/motif")
def motif(payload: MotifIn):
    s = _clean_seq(payload.sequence)
    m = re.sub(r"\s+", "", payload.motif).upper().replace("U", "T")
    if not m or not _MOTIF_RE.match(m):
        raise HTTPException(status_code=400, detail="Motif invalide (autorisé : A T C G U).")
    positions = []
    start = 0
    while True:
        i = s.find(m, start)
        if i == -1:
            break
        positions.append(i + 1)  # 1-indexed (convention bio)
        start = i + 1
    return {"motif": m, "count": len(positions), "positions": positions[:1000]}


class FastaIn(BaseModel):
    fasta: str = Field(max_length=600_000)


@router.post("/fasta-stats")
def fasta_stats(payload: FastaIn):
    text = payload.fasta.strip()
    if len(text) > config.MAX_TEXT_CHARS:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux.")
    if not text.startswith(">"):
        # accepte aussi une séquence brute unique
        s = _clean_seq(text)
        return {"sequences": 1, "total_length": len(s), "min": len(s), "max": len(s),
                "avg": len(s), **_gc_stats(s), "headers": []}
    headers, seqs, current = [], [], ""
    for line in text.splitlines():
        if line.startswith(">"):
            headers.append(line[1:].strip()[:200])
            if current:
                seqs.append(_clean_seq(current))
                current = ""
        else:
            current += line.strip()
    if current:
        seqs.append(_clean_seq(current))
    if not seqs:
        raise HTTPException(status_code=400, detail="Aucune séquence trouvée.")
    total = sum(map(len, seqs))
    all_seq = "".join(seqs)
    return {
        "sequences": len(seqs),
        "total_length": total,
        "min": min(map(len, seqs)),
        "max": max(map(len, seqs)),
        "avg": round(total / len(seqs), 1),
        **_gc_stats(all_seq),
        "headers": headers[:100],
    }
