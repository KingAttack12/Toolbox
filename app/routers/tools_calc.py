"""Calculatrices — 100 % local."""
from __future__ import annotations

import ast
import math
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import get_current_user

router = APIRouter(prefix="/api/tools/calc", tags=["calculatrices"], dependencies=[Depends(get_current_user)])

# ---------- Pourcentages / TVA ----------

class PercentIn(BaseModel):
    value: float
    percent: float
    mode: Literal["of", "increase", "decrease"] = "of"


@router.post("/percent")
def percent(p: PercentIn):
    if p.mode == "of":
        return {"result": p.value * p.percent / 100}
    if p.mode == "increase":
        return {"result": p.value * (1 + p.percent / 100)}
    return {"result": p.value * (1 - p.percent / 100)}


class TvaIn(BaseModel):
    amount: float = Field(gt=0)
    rate: float = Field(ge=0, le=100)
    mode: Literal["ht_to_ttc", "ttc_to_ht"] = "ht_to_ttc"


@router.post("/tva")
def tva(p: TvaIn):
    if p.mode == "ht_to_ttc":
        ttc = p.amount * (1 + p.rate / 100)
        return {"ht": p.amount, "tva": ttc - p.amount, "ttc": ttc}
    ht = p.amount / (1 + p.rate / 100)
    return {"ht": ht, "tva": p.amount - ht, "ttc": p.amount}


# ---------- Conversions d'unités (facteurs vers unité de base) ----------

_CONVERSIONS: dict[str, dict[str, float]] = {
    "length": {"mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0, "in": 0.0254, "ft": 0.3048, "mi": 1609.344},
    "mass": {"mg": 1e-6, "g": 0.001, "kg": 1.0, "t": 1000.0, "oz": 0.0283495, "lb": 0.453592},
    "volume": {"ml": 0.001, "cl": 0.01, "l": 1.0, "m3": 1000.0, "floz": 0.0295735, "gal": 3.78541},
    "speed": {"m/s": 1.0, "km/h": 1 / 3.6, "mph": 0.44704, "kn": 0.514444},
    "storage": {"o": 1.0, "ko": 1024.0, "mo": 1024.0**2, "go": 1024.0**3, "to": 1024.0**4},
}


class ConvertIn(BaseModel):
    category: Literal["length", "mass", "volume", "speed", "storage"] = "length"
    value: float
    from_unit: str = Field(alias="from")
    to_unit: str = Field(alias="to")

    class Config:
        populate_by_name = True


@router.post("/convert")
def convert(p: ConvertIn):
    table = _CONVERSIONS[p.category]
    if p.from_unit not in table or p.to_unit not in table:
        raise HTTPException(status_code=400, detail=f"Unités supportées : {sorted(table)}")
    base = p.value * table[p.from_unit]
    return {"result": base / table[p.to_unit]}


class TempIn(BaseModel):
    value: float = Field(ge=-10000, le=10000)
    from_unit: Literal["C", "F", "K"] = Field(alias="from")
    to_unit: Literal["C", "F", "K"] = Field(alias="to")

    class Config:
        populate_by_name = True


@router.post("/temperature")
def temperature(p: TempIn):
    c = {"C": p.value, "F": (p.value - 32) * 5 / 9, "K": p.value - 273.15}[p.from_unit]
    out = {"C": c, "F": c * 9 / 5 + 32, "K": c + 273.15}[p.to_unit]
    return {"result": out}


# ---------- Dates / moyennes ----------

class DateDiffIn(BaseModel):
    date1: str  # ISO YYYY-MM-DD
    date2: str


@router.post("/date-diff")
def date_diff(p: DateDiffIn):
    try:
        d1 = datetime.fromisoformat(p.date1).date()
        d2 = datetime.fromisoformat(p.date2).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Dates attendues au format AAAA-MM-JJ.")
    delta = abs((d2 - d1).days)
    return {"days": delta, "weeks": round(delta / 7, 2), "months_approx": round(delta / 30.44, 2)}


class Note(BaseModel):
    value: float = Field(ge=0, le=20)
    coef: float = Field(default=1, ge=0.1, le=20)


class MoyenneIn(BaseModel):
    notes: list[Note] = Field(max_length=100)


@router.post("/moyenne")
def moyenne(p: MoyenneIn):
    if not p.notes:
        raise HTTPException(status_code=400, detail="Ajoutez au moins une note.")
    total_coef = sum(n.coef for n in p.notes)
    avg = sum(n.value * n.coef for n in p.notes) / total_coef
    mention = (
        "TB (≥16)" if avg >= 16 else "B (≥14)" if avg >= 14 else "AB (≥12)"
        if avg >= 12 else "Passable (≥10)" if avg >= 10 else "Ajourné (<10)"
    )
    return {"moyenne": round(avg, 2), "total_coef": total_coef, "mention": mention}


# ---------- Calculatrice scientifique : évaluateur sûr via AST ----------

_ALLOWED_FUNCS = {
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
    "exp": math.exp, "abs": abs, "round": round, "floor": math.floor, "ceil": math.ceil,
}
_ALLOWED_CONSTS = {"pi": math.pi, "e": math.e, "tau": math.tau}


class ExprIn(BaseModel):
    expression: str = Field(max_length=500)


def _safe_eval(expr: str) -> float:
    tree = ast.parse(expr, mode="eval")
    allowed = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Load,
        ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
        ast.USub, ast.UAdd, ast.FloorDiv,
    )
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise ValueError(f"Élément non autorisé : {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in _ALLOWED_FUNCS and node.id not in _ALLOWED_CONSTS:
            raise ValueError(f"Nom non autorisé : {node.id}")
        if isinstance(node, ast.Call) and not (
            isinstance(node.func, ast.Name) and node.func.id in _ALLOWED_FUNCS
        ):
            raise ValueError("Fonction non autorisée.")
    code = compile(tree, "<calc>", "eval")
    return eval(code, {"__builtins__": {}}, {**_ALLOWED_FUNCS, **_ALLOWED_CONSTS})  # noqa: S307


@router.post("/expr")
def expr(p: ExprIn):
    try:
        result = _safe_eval(p.expression.strip())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Expression invalide : {e}")
    if not isinstance(result, (int, float)) or isinstance(result, bool):
        raise HTTPException(status_code=400, detail="Expression invalide.")
    return {"result": result}
