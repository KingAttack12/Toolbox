"""Outils Texte / Dev — 100 % local, sans dépendance externe."""
from __future__ import annotations

import base64
import binascii
import csv
import difflib
import hashlib
import io
import json
import re
import secrets
import uuid
import xml.dom.minidom as minidom
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .. import config
from ..auth import get_current_user

router = APIRouter(prefix="/api/tools/text", tags=["texte"], dependencies=[Depends(get_current_user)])


def _check_len(text: str) -> str:
    if len(text) > config.MAX_TEXT_CHARS:
        raise HTTPException(status_code=413, detail=f"Texte trop long (max {config.MAX_TEXT_CHARS} caractères).")
    return text


class TextIn(BaseModel):
    text: str = Field(default="", max_length=600_000)


@router.post("/count")
def count(payload: TextIn):
    text = _check_len(payload.text)
    words = len(re.findall(r"\S+", text))
    lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0) if text else 0
    sentences = len(re.findall(r"[.!?…]+", text))
    return {
        "words": words,
        "chars": len(text),
        "chars_no_spaces": len(re.sub(r"\s", "", text)),
        "lines": lines,
        "sentences": sentences,
    }


class CleanIn(BaseModel):
    text: str = ""
    remove_extra_spaces: bool = True
    remove_empty_lines: bool = False
    trim_lines: bool = True


@router.post("/clean")
def clean(payload: CleanIn):
    text = _check_len(payload.text)
    lines = text.split("\n")
    out = []
    for ln in lines:
        if payload.trim_lines:
            ln = ln.strip()
        if payload.remove_extra_spaces:
            ln = re.sub(r"[ \t]{2,}", " ", ln)
        if payload.remove_empty_lines and not ln.strip():
            continue
        out.append(ln)
    cleaned = "\n".join(out)
    if payload.remove_extra_spaces:
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return {"result": cleaned}


class CaseIn(BaseModel):
    text: str = ""
    mode: Literal["upper", "lower", "title", "capitalize", "invert"] = "upper"


@router.post("/case")
def case(payload: CaseIn):
    text = _check_len(payload.text)
    modes = {
        "upper": text.upper,
        "lower": text.lower,
        "title": text.title,
        "capitalize": text.capitalize,
        "invert": text.swapcase,
    }
    return {"result": modes[payload.mode]()}


class B64In(BaseModel):
    data: str = ""
    mode: Literal["encode", "decode"] = "encode"


@router.post("/base64")
def b64(payload: B64In):
    _check_len(payload.data)
    try:
        if payload.mode == "encode":
            return {"result": base64.b64encode(payload.data.encode("utf-8")).decode("ascii")}
        raw = base64.b64decode(payload.data.strip(), validate=True)
        return {"result": raw.decode("utf-8")}
    except (binascii.Error, UnicodeDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Base64 invalide : {e}")


class HashIn(BaseModel):
    text: str = ""
    algo: Literal["sha256", "sha512"] = "sha256"


@router.post("/hash")
def hash_text(payload: HashIn):
    _check_len(payload.text)
    h = hashlib.new(payload.algo, payload.text.encode("utf-8"))
    return {"algo": payload.algo, "result": h.hexdigest()}


class UuidIn(BaseModel):
    count: int = Field(default=1, ge=1, le=50)


@router.post("/uuid")
def gen_uuid(payload: UuidIn):
    return {"result": [str(uuid.uuid4()) for _ in range(payload.count)]}


class PasswordIn(BaseModel):
    length: int = Field(default=20, ge=8, le=128)
    symbols: bool = True


@router.post("/password")
def gen_password(payload: PasswordIn):
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    if payload.symbols:
        alphabet += "!@#$%^&*-_=+?"
    return {"result": "".join(secrets.choice(alphabet) for _ in range(payload.length))}


class JsonIn(BaseModel):
    data: str = ""
    indent: int = Field(default=2, ge=0, le=8)


@router.post("/json-format")
def json_format(payload: JsonIn):
    _check_len(payload.data)
    try:
        obj = json.loads(payload.data)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON invalide : {e}")
    return {"result": json.dumps(obj, indent=payload.indent or None, ensure_ascii=False)}


@router.post("/json-validate")
def json_validate(payload: TextIn):
    _check_len(payload.text)
    try:
        json.loads(payload.text)
        return {"valid": True}
    except json.JSONDecodeError as e:
        return {"valid": False, "error": str(e)}


@router.post("/xml-format")
def xml_format(payload: TextIn):
    _check_len(payload.text)
    try:
        dom = minidom.parseString(payload.text)
        return {"result": dom.toprettyxml(indent="  ")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"XML invalide : {e}")


class DiffIn(BaseModel):
    a: str = ""
    b: str = ""


@router.post("/diff")
def diff(payload: DiffIn):
    _check_len(payload.a)
    _check_len(payload.b)
    lines = list(
        difflib.unified_diff(
            payload.a.splitlines(), payload.b.splitlines(), lineterm="", n=3
        )
    )
    return {"result": "\n".join(lines) if lines else "Aucune différence."}


class CsvIn(BaseModel):
    csv_text: str = ""
    delimiter: str = ","


@router.post("/csv-preview")
def csv_preview(payload: CsvIn):
    _check_len(payload.csv_text)
    if payload.delimiter not in [",", ";", "\t", "|"]:
        raise HTTPException(status_code=400, detail="Délimiteur non supporté.")
    try:
        reader = csv.reader(io.StringIO(payload.csv_text), delimiter=payload.delimiter)
        rows = [row for _, row in zip(range(101), reader)]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"CSV illisible : {e}")
    return {"rows": rows, "truncated": len(rows) == 101}
