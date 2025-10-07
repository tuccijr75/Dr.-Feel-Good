#!/usr/bin/env python3
# ==========================================================
# 🧠 Dr. Feel Good — DSM / ICD Update Checker
# ==========================================================
# Checks the WHO ICD-11 release endpoint and refreshes the
# DSM_ICD_Update_Notice.txt file with the newest version data.
# (DSM updates are always manual via APA official site.)
#
# Usage:
#   python E:\Dr-Feel-Good\FeelGood_Update_Checker.py
#
# Dependencies: requests (install with `pip install requests`)
# ==========================================================

import requests
import json
from datetime import datetime
from pathlib import Path

# ---------- Configuration ----------
BASE_PATH = Path("E:/Dr-Feel-Good")
NOTICE_FILE = BASE_PATH / "DSM_ICD_Update_Notice.txt"

DSM_URL = "https://www.psychiatry.org/psychiatrists/practice/dsm"
ICD_API_URL = "https://id.who.int/icd/release/11/mms"
ICD_HUMAN_URL = "https://icd.who.int/en"

# ---------- Functions ----------
def get_icd_release():
    """Query WHO ICD-11 API and return release date string."""
    try:
        resp = requests.get(ICD_API_URL, timeout=10)
        if not resp.ok:
            return f"⚠️  Unable to reach ICD API (HTTP {resp.status_code})"
        data = resp.json()
        release_date = data.get("releaseDate", None)
        if release_date:
            return f"ICD-11 latest release date: {release_date}"
        return "⚠️  ICD-11 release date not found in response."
    except Exception as e:
        return f"⚠️  Error checking ICD API: {e}"

# ---------- Main ----------
def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    icd_line = get_icd_release()

    header = (
        "=============================================\n"
        "🧾  Dr. Feel Good — DSM-5-TR / ICD-11 Update Notice\n"
        "=============================================\n\n"
        f"Last automatic check: {now}\n\n"
    )

    dsm_section = (
        f"DSM-5-TR official reference page:\n"
        f"▶  {DSM_URL}\n"
        "Latest confirmed release: DSM-5-TR (2022) Text Revision\n"
        "Next expected bulletin: Q1 2026 (APA periodic supplement)\n\n"
    )

    icd_section = (
        f"ICD-11 official reference:\n"
        f"▶  {ICD_HUMAN_URL}\n"
        f"WHO API endpoint: {ICD_API_URL}\n"
        f"{icd_line}\n\n"
    )

    footer = (
        "----------------------------------------------------------\n"
        "Update procedure\n"
        "----------------------------------------------------------\n"
        "1. Run this script monthly (manual or Task Scheduler).\n"
        "2. If newer versions are found, open the URLs above and\n"
        "   download the official DSM or ICD materials.\n"
        "3. Insert key notes under:\n"
        "   === DSM / ICD Reference Section ===\n"
        "   inside Dr_Feel_Good_Persona.md\n\n"
        "End of file\n"
    )

    with open(NOTICE_FILE, "w", encoding="utf-8") as f:
        f.write(header + dsm_section + icd_section + footer)

    print("✅  Update check complete.  See DSM_ICD_Update_Notice.txt for details.")

# ---------- Entry ----------
if __name__ == "__main__":
    main()
