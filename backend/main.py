from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psutil
import subprocess
import time
import socket
import requests
import threading
import os

app = FastAPI(title="Raspberry Monitor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NTFY_TOPIC = os.getenv("NTFY_TOPIC")
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}" if NTFY_TOPIC else None


def get_temperature():
    try:
        result = subprocess.run(
            ["vcgencmd", "measure_temp"],
            capture_output=True,
            text=True
        )

        return float(
            result.stdout
            .replace("temp=", "")
            .replace("'C", "")
            .strip()
        )
    except Exception:
        return None


def get_service_status(service_name: str):
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True
        )

        status = result.stdout.strip()

        return {
            "name": service_name,
            "status": status,
            "running": status == "active"
        }

    except Exception:
        return {
            "name": service_name,
            "status": "unknown",
            "running": False
        }


def get_docker_container_status(container_name: str):
    try:
        result = subprocess.run(
            [
                "docker",
                "inspect",
                "-f",
                "{{.State.Status}}",
                container_name
            ],
            capture_output=True,
            text=True
        )

        status = result.stdout.strip()

        return {
            "name": container_name,
            "status": status if status else "not_found",
            "running": status == "running"
        }

    except Exception:
        return {
            "name": container_name,
            "status": "unknown",
            "running": False
        }


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "raspberry-monitor"
    }


@app.get("/api/system")
def system_info():
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    try:
        ssd = psutil.disk_usage("/mnt/photos")
        ssd_info = {
            "mounted": True,
            "total_gb": round(ssd.total / 1024**3, 2),
            "used_gb": round(ssd.used / 1024**3, 2),
            "free_gb": round(ssd.free / 1024**3, 2),
            "percent": ssd.percent,
        }
    except Exception:
        ssd_info = {
            "mounted": False,
            "total_gb": 0,
            "used_gb": 0,
            "free_gb": 0,
            "percent": 0,
        }

    return {
        "status": "online",
        "hostname": socket.gethostname(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "temperature": get_temperature(),

        "memory": {
            "total_gb": round(memory.total / 1024**3, 2),
            "used_gb": round(memory.used / 1024**3, 2),
            "percent": memory.percent,
        },

        "disk": {
            "total_gb": round(disk.total / 1024**3, 2),
            "used_gb": round(disk.used / 1024**3, 2),
            "free_gb": round(disk.free / 1024**3, 2),
            "percent": disk.percent,
        },

        "ssd": ssd_info,

        "uptime_seconds": int(time.time() - psutil.boot_time()),
    }


@app.get("/api/services")
def services():
    return {
        "systemd": [
    get_service_status("childskills-backend.service"),
    get_service_status("childskills-frontend.service"),
    get_service_status("photo-server.service"),
    get_service_status("raspberry-monitor.service"),
],

        "apps": [
            get_port_status("Raspberry Monitor", 8200),
            get_port_status("Photo Server", 8100),
            get_port_status("Child Skills", 8000),
        ],

        "docker": [
            get_docker_container_status("immich_server"),
            get_docker_container_status("immich_postgres"),
            get_docker_container_status("immich_redis"),
        ]
    }

def get_port_status(name: str, port: int):
    for conn in psutil.net_connections(kind="inet"):
        if conn.laddr and conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
            return {
                "name": name,
                "port": port,
                "status": "running",
                "running": True
            }

    return {
        "name": name,
        "port": port,
        "status": "stopped",
        "running": False
    }

ALLOWED_SYSTEMD_SERVICES = {
    "childskills-backend": "childskills-backend.service",
    "childskills-frontend": "childskills-frontend.service",
    "photo-server": "photo-server.service",
}

ALLOWED_DOCKER_CONTAINERS = {
    "immich_server",
    "immich_postgres",
    "immich_redis",
}


@app.post("/api/services/systemd/{service_key}/{action}")
def control_systemd_service(service_key: str, action: str):
    if service_key not in ALLOWED_SYSTEMD_SERVICES:
        raise HTTPException(status_code=400, detail="Service not allowed")

    if action not in {"start", "stop", "restart"}:
        raise HTTPException(status_code=400, detail="Action not allowed")

    service_name = ALLOWED_SYSTEMD_SERVICES[service_key]

    result = subprocess.run(
        ["sudo", "systemctl", action, service_name],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=result.stderr.strip()
        )

    return {
        "success": True,
        "service": service_key,
        "action": action,
    }


@app.post("/api/services/docker/{container}/{action}")
def control_docker_container(container: str, action: str):
    if container not in ALLOWED_DOCKER_CONTAINERS:
        raise HTTPException(status_code=400, detail="Container not allowed")

    if action not in {"start", "stop", "restart"}:
        raise HTTPException(status_code=400, detail="Action not allowed")

    result = subprocess.run(
        ["docker", action, container],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=result.stderr.strip()
        )

    return {
        "success": True,
        "container": container,
        "action": action,
    }


@app.post("/api/system/shutdown")
def shutdown_system():
    subprocess.Popen(
        [
            "sudo",
            "/usr/sbin/shutdown",
            "-h",
            "now",
        ]
    )

    return {
        "success": True,
        "message": "Raspberry Pi išjungiamas"
    }

@app.get("/api/processes")
def top_processes():
    processes = []

    try:
        # Pirmas CPU matavimo ciklas
        for proc in psutil.process_iter():
            try:
                proc.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Trumpas matavimo tarpas
        time.sleep(0.3)

        # Antras ciklas – jau gauname realų CPU %
        for proc in psutil.process_iter(
            ["pid", "name", "memory_percent"]
        ):
            try:
                cpu = proc.cpu_percent(interval=None)

                processes.append({
                    "pid": proc.info["pid"],
                    "name": proc.info["name"] or "unknown",
                    "cpu": round(cpu, 1),
                    "memory": round(
                        proc.info["memory_percent"] or 0,
                        1
                    ),
                })

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                continue

        processes.sort(
            key=lambda p: p["cpu"],
            reverse=True
        )

        return processes[:8]

    except Exception as e:
        return {
            "error": str(e)
        }

def send_ntfy(title: str, message: str, priority: str = "high"):
    priority_map = {
        "min": 1,
        "low": 2,
        "default": 3,
        "high": 4,
        "urgent": 5,
    }

    try:
        response = requests.post(
            "https://ntfy.sh/",
            json={
                "topic": NTFY_TOPIC,
                "title": title,
                "message": message,
                "priority": priority_map.get(priority, 3),
                "tags": ["warning"],
            },
            timeout=10,
        )

        response.raise_for_status()

    except Exception as e:
        print(
            f"ntfy error: {e} - "
            f"{response.text if 'response' in locals() else ''}",
            flush=True
        )

alert_state = {
    "ssd": False,
    "temperature": False,
    "cpu": False,
    "services": {},
}

def alert_monitor():
    high_temp_since = None
    high_cpu_since = None

    while True:
        try:
            # =========================
            # SSD
            # =========================
            ssd_mounted = any(
                part.mountpoint == "/mnt/photos"
                for part in psutil.disk_partitions(all=False)
            )

            if not ssd_mounted and not alert_state["ssd"]:
                send_ntfy(
                    "SSD atsijungė",
                    "Raspberry Pi nebemato /mnt/photos. Immich gali neveikti tinkamai.",
                    "urgent",
                )
                alert_state["ssd"] = True

            elif ssd_mounted and alert_state["ssd"]:
                send_ntfy(
                    "SSD vėl prijungtas",
                    "/mnt/photos vėl pasiekiamas.",
                    "default",
                )
                alert_state["ssd"] = False

            # =========================
            # TEMPERATŪRA
            # =========================
            temp = get_temperature()

            if temp is not None and temp > 75:
                if high_temp_since is None:
                    high_temp_since = time.time()

                if (
                    time.time() - high_temp_since >= 300
                    and not alert_state["temperature"]
                ):
                    send_ntfy(
                        "Aukšta Raspberry temperatūra",
                        f"CPU temperatūra {temp:.1f} °C jau ilgiau nei 5 min.",
                        "urgent",
                    )
                    alert_state["temperature"] = True

            else:
                high_temp_since = None

                if alert_state["temperature"]:
                    send_ntfy(
                        "Temperatūra normalizavosi",
                        f"CPU temperatūra dabar {temp:.1f} °C.",
                        "default",
                    )
                    alert_state["temperature"] = False

            # =========================
            # CPU
            # =========================
            cpu = psutil.cpu_percent(interval=1)

            if cpu > 95:
                if high_cpu_since is None:
                    high_cpu_since = time.time()

                if (
                    time.time() - high_cpu_since >= 600
                    and not alert_state["cpu"]
                ):
                    send_ntfy(
                        "Didelė CPU apkrova",
                        f"CPU apkrova {cpu:.1f}% jau ilgiau nei 10 min.",
                        "high",
                    )
                    alert_state["cpu"] = True

            else:
                high_cpu_since = None

                if alert_state["cpu"]:
                    send_ntfy(
                        "CPU apkrova sumažėjo",
                        f"CPU apkrova dabar {cpu:.1f}%.",
                        "default",
                    )
                    alert_state["cpu"] = False

            # =========================
            # SYSTEMD SERVISAI
            # =========================
            systemd_services = [
                "childskills-backend.service",
                "childskills-frontend.service",
                "photo-server.service",
            ]

            for service_name in systemd_services:
                status = get_service_status(service_name)
                key = f"systemd:{service_name}"

                previous = alert_state["services"].get(key, True)

                if not status["running"] and previous:
                    send_ntfy(
                        "Servisas sustojo",
                        f"{service_name} neveikia.",
                        "high",
                    )
                    alert_state["services"][key] = False

                elif status["running"] and not previous:
                    send_ntfy(
                        "Servisas vėl veikia",
                        f"{service_name} sėkmingai paleistas.",
                        "default",
                    )
                    alert_state["services"][key] = True

                elif key not in alert_state["services"]:
                    alert_state["services"][key] = status["running"]

            # =========================
            # IMMICH DOCKER
            # =========================
            docker_services = [
                "immich_server",
                "immich_postgres",
                "immich_redis",
            ]

            for container_name in docker_services:
                status = get_docker_container_status(container_name)
                key = f"docker:{container_name}"

                previous = alert_state["services"].get(key, True)

                if not status["running"] and previous:
                    send_ntfy(
                        "Immich problema",
                        f"{container_name} neveikia.",
                        "high",
                    )
                    alert_state["services"][key] = False

                elif status["running"] and not previous:
                    send_ntfy(
                        "Immich atsistatė",
                        f"{container_name} vėl veikia.",
                        "default",
                    )
                    alert_state["services"][key] = True

                elif key not in alert_state["services"]:
                    alert_state["services"][key] = status["running"]

        except Exception as e:
            print(f"Alert monitor error: {e}", flush=True)

        # Tikriname kas 30 sekundžių
        time.sleep(30)

@app.on_event("startup")
def start_alert_monitor():
    thread = threading.Thread(
        target=alert_monitor,
        daemon=True
    )
    thread.start()

        # Systemd servisai
systemd_services = [
    "childskills-backend.service",
    "childskills-frontend.service",
    "photo-server.service",
]

for service_name in systemd_services:
    status = get_service_status(service_name)
    key = f"systemd:{service_name}"

    previous = alert_state["services"].get(key, True)

    print(
    f"ALERT SERVICE: {service_name} "
    f"running={status['running']} "
    f"previous={previous}",
    flush=True
)

    if not status["running"] and previous:
        send_ntfy(
            "Servisas sustojo",
            f"{service_name} neveikia.",
            "high",
        )
        alert_state["services"][key] = False

    elif status["running"] and not previous:
        send_ntfy(
            "Servisas vėl veikia",
            f"{service_name} sėkmingai paleistas.",
            "default",
        )
        alert_state["services"][key] = True


# Immich Docker konteineriai
docker_services = [
    "immich_server",
    "immich_postgres",
    "immich_redis",
]

for container_name in docker_services:
    status = get_docker_container_status(container_name)
    key = f"docker:{container_name}"

    previous = alert_state["services"].get(key, True)

    if not status["running"] and previous:
        send_ntfy(
            "Immich problema",
            f"{container_name} neveikia.",
            "high",
        )
        alert_state["services"][key] = False

    elif status["running"] and not previous:
        send_ntfy(
            "Immich atsistatė",
            f"{container_name} vėl veikia.",
            "default",
        )
        alert_state["services"][key] = True

        time.sleep(30)
