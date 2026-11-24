import os
import time
import json
import csv
import argparse
import logging
import subprocess
import shutil
from datetime import datetime


# -----------------------------
# 1. CPU MONITORING
# -----------------------------

def parse_cpu_line(line):
    values = list(map(int, line.split()[1:]))
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    total = sum(values)
    return total, idle


def get_cpu_usage(interval=1):
    with open("/proc/stat") as file:
        first = parse_cpu_line(file.readline())

    time.sleep(interval)

    with open("/proc/stat") as file:
        second = parse_cpu_line(file.readline())

    total_diff = second[0] - first[0]
    idle_diff = second[1] - first[1]

    if total_diff <= 0:
        return 0.0

    return round(
        (1 - idle_diff / total_diff) * 100, 2
    )


# -----------------------------
# 2. RAM MONITORING
# -----------------------------

def parse_meminfo(content):
    memory = {}

    for line in content.splitlines():
        key, value = line.split(":", 1)
        memory[key] = int(value.strip().split()[0])

    total = memory["MemTotal"]
    available = memory["MemAvailable"]
    used = total - available

    return {
        "total_mb": round(total / 1024, 2),
        "used_mb": round(used / 1024, 2),
        "available_mb": round(available / 1024, 2),
        "percent": round(used / total * 100, 2)
    }


def get_ram_usage():
    with open("/proc/meminfo") as file:
        return parse_meminfo(file.read())


# -----------------------------
# 3. DISK MONITORING
# -----------------------------

def get_disk_usage():
    disk = shutil.disk_usage("/")

    return {
        "total_gb": round(disk.total / (1024 ** 3), 2),
        "used_gb": round(disk.used / (1024 ** 3), 2),
        "free_gb": round(disk.free / (1024 ** 3), 2),
        "percent": round(disk.used / disk.total * 100, 2)
    }


# -----------------------------
# 4. UPTIME MONITORING
# -----------------------------

def get_uptime():
    with open("/proc/uptime") as file:
        seconds = float(file.read().split()[0])

    return {
        "seconds": round(seconds, 2),
        "hours": round(seconds / 3600, 2)
    }


# -----------------------------
# 5. TOP PROCESSES
# -----------------------------

def get_top_processes(limit=5):
    result = subprocess.run(
        ["ps", "-eo", "pid,comm,%cpu,%mem",
         "--sort=-%cpu"],
        capture_output=True,
        text=True,
        check=True
    )

    processes = []

    for line in result.stdout.splitlines()[1:limit + 1]:
        parts = line.split(None, 3)

        if len(parts) == 4:
            processes.append({
                "pid": int(parts[0]),
                "name": parts[1],
                "cpu": float(parts[2]),
                "ram": float(parts[3])
            })

    return processes


# -----------------------------
# 6. THRESHOLD ALERTS
# -----------------------------

def check_thresholds(cpu, ram, disk,
                     cpu_limit=80,
                     ram_limit=80,
                     disk_limit=80):

    alerts = []

    metrics = {
        "CPU": cpu,
        "RAM": ram,
        "DISK": disk
    }

    limits = {
        "CPU": cpu_limit,
        "RAM": ram_limit,
        "DISK": disk_limit
    }

    for name, value in metrics.items():
        if value >= limits[name]:
            alerts.append(
                f"WARNING: {name} usage is "
                f"{value}% (Threshold: {limits[name]}%)"
            )

    return alerts


# -----------------------------
# 7. COLLECT SYSTEM DATA
# -----------------------------

def collect_health_data():
    return {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
        "cpu_percent": get_cpu_usage(),
        "ram": get_ram_usage(),
        "disk": get_disk_usage(),
        "uptime": get_uptime(),
        "top_processes": get_top_processes()
    }


# -----------------------------
# 8. LOG ALERTS
# -----------------------------

def setup_logging():
    os.makedirs("logs", exist_ok=True)

    logging.basicConfig(
        filename="logs/health.log",
        level=logging.WARNING,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )


def display_alerts(alerts):
    if not alerts:
        print("\nSYSTEM STATUS: HEALTHY")
        return

    print("\nSYSTEM ALERTS:")

    for alert in alerts:
        print(alert)
        logging.warning(alert)


# -----------------------------
# 9. JSON REPORT
# -----------------------------

def save_json(data, filename):
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)

    with open(filename, "w") as file:
        json.dump(data, file, indent=4)


# -----------------------------
# 10. CSV REPORT
# -----------------------------

def save_csv(data, filename):
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)

    row = {
        "timestamp": data["timestamp"],
        "cpu_percent": data["cpu_percent"],
        "ram_percent": data["ram"]["percent"],
        "ram_used_mb": data["ram"]["used_mb"],
        "disk_percent": data["disk"]["percent"],
        "disk_used_gb": data["disk"]["used_gb"],
        "uptime_hours": data["uptime"]["hours"],
        "top_processes": json.dumps(data["top_processes"])
    }

    with open(filename, "w", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=row.keys()
        )
        writer.writeheader()
        writer.writerow(row)


# -----------------------------
# 11. MAIN PROGRAM
# -----------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Linux Host Health Checker"
    )

    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json"
    )

    parser.add_argument("--cpu-limit", type=float, default=80)
    parser.add_argument("--ram-limit", type=float, default=80)
    parser.add_argument("--disk-limit", type=float, default=80)

    args = parser.parse_args()

    setup_logging()

    data = collect_health_data()

    alerts = check_thresholds(
        data["cpu_percent"],
        data["ram"]["percent"],
        data["disk"]["percent"],
        args.cpu_limit,
        args.ram_limit,
        args.disk_limit
    )

    data["alerts"] = alerts

    print("\n===== LINUX HOST HEALTH CHECKER =====")

    print(f"CPU Usage: {data['cpu_percent']}%")
    print(f"RAM Usage: {data['ram']['percent']}%")
    print(f"Disk Usage: {data['disk']['percent']}%")
    print(f"Uptime: {data['uptime']['hours']} hours")

    print("\nTOP PROCESSES:")

    for process in data["top_processes"]:
        print(process)

    display_alerts(alerts)

    filename = f"reports/report.{args.format}"

    if args.format == "json":
        save_json(data, filename)
    else:
        save_csv(data, filename)

    print(f"\nReport saved to: {filename}")


if __name__ == "__main__":
    main()
    