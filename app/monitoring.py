"""Read-only Linux VM and service metrics. No shell or privileged command."""
import os
import shutil
import threading
import time
from pathlib import Path
from . import config
from .workload import workload

_lock = threading.Lock()
_previous = None


def cgroup_root():
    for line in Path("/proc/self/cgroup").read_text().splitlines():
        if line.startswith("0::"):
            return Path("/sys/fs/cgroup") / line[3:].lstrip("/")
    raise OSError("cgroup v2 unavailable")


def number(path):
    text = path.read_text().strip()
    return None if text == "max" else int(text)


def metrics():
    global _previous
    host_cpu = service_cpu = None
    memory = {"used": None, "total": None}
    service = {"used": None, "limit": None, "cpu_cores": None}
    try:
        info = {line.split(":")[0]:int(line.split()[1])*1024 for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith(("MemTotal:","MemAvailable:"))}
        memory = {"total": info["MemTotal"], "used": info["MemTotal"]-info["MemAvailable"]}
        ticks = list(map(int,Path("/proc/stat").read_text().splitlines()[0].split()[1:9]))
        total, idle = sum(ticks), ticks[3]+ticks[4]
        usage = None
        try:
            root = cgroup_root()
            service["used"] = number(root/"memory.current")
            service["limit"] = number(root/"memory.max")
            quota, period = (root/"cpu.max").read_text().split()
            service["cpu_cores"] = os.cpu_count() if quota == "max" else int(quota)/int(period)
            cpu = dict(line.split() for line in (root/"cpu.stat").read_text().splitlines())
            usage = int(cpu["usage_usec"])
        except (OSError, ValueError, KeyError):
            pass
        now = time.monotonic()
        with _lock:
            previous = _previous
            if previous and now-previous[0] >= .5:
                elapsed = now-previous[0]
                delta = total-previous[1]
                if delta > 0: host_cpu = max(0,min(100,100*(1-(idle-previous[2])/delta)))
                if usage is not None and previous[3] is not None and service["cpu_cores"]:
                    service_cpu = max(0,100*(usage-previous[3])/1_000_000/elapsed/service["cpu_cores"])
                _previous = (now,total,idle,usage)
            elif previous is None:
                _previous = (now,total,idle,usage)
    except (OSError, ValueError, KeyError):
        pass
    disk = shutil.disk_usage(config.BASE_DIR)
    return {"sampled_at": time.time(), "cpu_vm_percent": host_cpu, "cpu_service_percent": service_cpu,
            "memory_vm": memory, "service": service, "cpu_count": os.cpu_count(),
            "disk": {"total":disk.total,"used":disk.used,"free":disk.free},
            "workload": workload.snapshot(),
            "quotas": {"guest_per_hour":10,"owner_per_hour":30},
            "note":"CPU disponible après deux mesures. Activité et compteurs depuis le dernier redémarrage."}
