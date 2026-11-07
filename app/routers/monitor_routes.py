from fastapi import APIRouter, Depends, Response
from ..auth import get_admin, get_current_user
from ..monitoring import metrics
from ..workload import workload

router = APIRouter(prefix="/api", tags=["monitoring"])


@router.get("/admin/load")
def load(response: Response, user: str = Depends(get_admin)):
    response.headers["Cache-Control"] = "no-store"
    return metrics()


@router.get("/tools/workload")
def own_workload(response: Response, user: str = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    state = workload.snapshot()
    if state["running"] and state["running"]["user"].casefold() == user.casefold():
        return {"state":"running", "position":0}
    for index, entry in enumerate(state["waiting"]):
        if entry["user"].casefold() == user.casefold():
            return {"state":"waiting", "position":index+1}
    return {"state":"idle", "position":None}
