#!/usr/bin/env python3

import os
import subprocess
import logging
import sys
import time

LOG_FILE = "/var/log/system_fix_v3.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ---------------- UI ---------------- #

def line():
    print("=" * 50)

def section(title):
    line()
    print(title)
    line()

def progress(step, total):
    percent = int((step / total) * 100)
    bar = "#" * (percent // 5) + "-" * (20 - percent // 5)
    print(f"[{bar}] {percent}%")

# ---------------- CORE RUN ---------------- #

def run(cmd_list, use_shell=False):
    cmd_str = cmd_list if isinstance(cmd_list, str) else " ".join(cmd_list)
    print(f"\n>> {cmd_str}")
    logging.info(f"RUN: {cmd_str}")

    try:
        process = subprocess.Popen(
            cmd_list,
            shell=use_shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line_out in process.stdout:
            print(line_out, end="")

        process.wait()

        if process.returncode == 0:
            print("OK\n")
        else:
            print(f"FAILED ({process.returncode})\n")

        return process.returncode

    except Exception as e:
        print(f"Execution failed: {e}")
        logging.error(str(e))
        return -1

# ---------------- ROOT ---------------- #

def require_root():
    if os.geteuid() != 0:
        print("Run with sudo")
        sys.exit(1)

# ---------------- TASKS ---------------- #

def full_update():
    section("SYSTEM UPDATE")
    run(["apt", "update"])
    run(["apt", "upgrade", "-y"])
    run(["apt", "dist-upgrade", "-y"])

def fix_broken():
    section("FIX BROKEN PACKAGES")
    run(["dpkg", "--configure", "-a"])
    run(["apt", "install", "-f", "-y"])

def clean():
    section("SYSTEM CLEAN")
    run(["apt", "autoremove", "-y"])
    run(["apt", "autoclean"])

def check_swap():
    section("SWAP CHECK")

    result = subprocess.run(["swapon", "--show"], stdout=subprocess.PIPE, text=True)

    if not result.stdout.strip():
        print("No swap found. Creating 2GB swap...")

        if not os.path.exists("/swapfile"):
            run(["fallocate", "-l", "2G", "/swapfile"])
            run(["chmod", "600", "/swapfile"])
            run(["mkswap", "/swapfile"])

        run(["swapon", "/swapfile"])

        with open("/etc/fstab", "r") as f:
            content = f.read()

        if "/swapfile" not in content:
            with open("/etc/fstab", "a") as f:
                f.write("\n/swapfile none swap sw 0 0\n")
            print("Swap added to fstab")
        else:
            print("Swap already in fstab")

    else:
        print("Swap active:")
        print(result.stdout)

def restart_failed():
    section("FAILED SERVICES")

    result = subprocess.run(
        ["systemctl", "--failed", "--no-legend"],
        stdout=subprocess.PIPE,
        text=True
    )

    lines = result.stdout.strip().splitlines()

    if not lines:
        print("No failed services")
        return

    for line_item in lines:
        service = line_item.split()[0]
        print(f"Restarting {service}")
        run(["systemctl", "restart", service])

def health_check():
    section("HEALTH CHECK")

    print("\n[1] Disk")
    run(["df", "-h"])

    print("\n[2] Logs")
    run("journalctl -p 3 -b --no-pager | tail -n 20", use_shell=True)

    print("\n[3] Network")
    run(["ping", "-c", "2", "8.8.8.8"])

    print("\n[4] Ports")
    run(["ss", "-tulnp"])

# ---------------- FULL FIX ---------------- #

def full_fix():
    total = 5
    step = 1

    section("FULL SYSTEM FIX")

    progress(step, total)
    full_update()
    step += 1

    progress(step, total)
    fix_broken()
    step += 1

    progress(step, total)
    clean()
    step += 1

    progress(step, total)
    check_swap()
    step += 1

    progress(step, total)
    restart_failed()

    progress(total, total)
    section("DONE")

# ---------------- MENU ---------------- #

def menu():
    print("""
1. Full Fix
2. Update
3. Fix Packages
4. Clean
5. Swap Fix
6. Restart Services
7. Health Check
8. Exit
""")

def main():
    require_root()

    while True:
        menu()
        choice = input("Select: ").strip()

        if choice == "1":
            full_fix()
        elif choice == "2":
            full_update()
        elif choice == "3":
            fix_broken()
        elif choice == "4":
            clean()
        elif choice == "5":
            check_swap()
        elif choice == "6":
            restart_failed()
        elif choice == "7":
            health_check()
        elif choice == "8":
            print("Exit")
            break
        else:
            print("Invalid")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user")
        sys.exit(0)
