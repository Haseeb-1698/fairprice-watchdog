"""
bd_create_zone.py — create a Bright Data proxy zone via the Zone Management API.

Creates a residential (default), datacenter, or ISP zone and prints the zone's
password so you can drop it into .env. Requires BRIGHTDATA_API_KEY (the account
API token) in .env.

    python scripts/bd_create_zone.py fairprice_resi            # residential (geo-capable)
    python scripts/bd_create_zone.py my_dc datacenter
    python scripts/bd_create_zone.py --list                    # list active zones
    python scripts/bd_create_zone.py --password fairprice_resi # fetch a zone's password

Docs: https://docs.brightdata.com/api-reference/account-management-api
"""
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests                                  # noqa: E402

from app.core.config import settings             # noqa: E402

API = "https://api.brightdata.com"

# Plan presets per proxy type. Residential zones support state/city/ZIP geo
# targeting via the proxy username (-country-us-state-ca / -zip-30301).
PLANS = {
    # city:1 enables state/city/ZIP geo targeting on the zone (the demo axis).
    "resi":        {"type": "resident", "country": "us", "city": 1, "ips_type": "shared", "bandwidth": "payperusage"},
    "residential": {"type": "resident", "country": "us", "city": 1, "ips_type": "shared", "bandwidth": "payperusage"},
    "datacenter":  {"type": "static", "ip_alloc_preset": "shared_block", "ips_type": "datacenter"},
    "isp":         {"type": "static", "ip_alloc_preset": "shared_block", "ips_type": "res_static"},
    # Web Unlocker with city:1 — anti-bot bypass AND state/ZIP geo (via proxy mode).
    "unlocker":    {"type": "unblocker", "country": "us", "city": 1},
}


def _headers() -> dict:
    if not settings.BRIGHTDATA_API_KEY:
        sys.exit("❌ BRIGHTDATA_API_KEY is empty in .env — paste your Bright Data account API token first.")
    return {"Authorization": f"Bearer {settings.BRIGHTDATA_API_KEY}", "Content-Type": "application/json"}


def create_zone(name: str, kind: str = "resi") -> None:
    plan = PLANS.get(kind, PLANS["resi"])
    body = {"zone": {"name": name, "type": plan["type"]}, "plan": plan}
    print(f"→ POST {API}/zone  {body}")
    r = requests.post(f"{API}/zone", headers=_headers(), json=body, timeout=60)
    print(f"  status={r.status_code}\n  {r.text[:600]}")
    if r.ok:
        print("\n✅ Zone created. Fetching password...")
        get_password(name)


def get_password(name: str) -> None:
    r = requests.get(f"{API}/zone/passwords", headers=_headers(), params={"zone": name}, timeout=60)
    print(f"  passwords status={r.status_code}: {r.text[:300]}")
    if r.ok:
        print(f"\nAdd to .env (residential geo zone):\n"
              f"  BRIGHTDATA_RESIDENTIAL_ZONE={name}\n"
              f"  BRIGHTDATA_RESIDENTIAL_PASSWORD=<password shown above>")


def list_zones() -> None:
    r = requests.get(f"{API}/zone/get_active_zones", headers=_headers(), timeout=60)
    print(f"status={r.status_code}\n{r.text[:1500]}")


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 0
    if args[0] == "--list":
        list_zones()
    elif args[0] == "--password" and len(args) > 1:
        get_password(args[1])
    else:
        name = args[0]
        kind = args[1] if len(args) > 1 else "resi"
        create_zone(name, kind)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
