#!/usr/bin/env python3
"""Publish a demo business event to the EventBridge bus.

Usage:
    python3 scripts/publish_demo_event.py user.signed_up
    python3 scripts/publish_demo_event.py kyc.approved --country GH
    python3 scripts/publish_demo_event.py kyc.approved --country NG

Watch how the rules route it:
- user.signed_up        -> welcome-email-queue + analytics-queue
- kyc.approved (GH)     -> compliance-queue   + analytics-queue
- kyc.approved (NG)     -> analytics-queue only  (content filter excludes compliance)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make `helper` importable when run from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from helper.business_event_publisher import publish_business_event
from helper.business_events import KycApproved, UserSignedUp


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish a demo EventBridge event")
    parser.add_argument("detail_type", choices=["user.signed_up", "kyc.approved"])
    parser.add_argument("--user-id", default="demo-user-1")
    parser.add_argument("--country", default="GH")
    parser.add_argument("--tier", default="gold")
    args = parser.parse_args()

    if args.detail_type == "user.signed_up":
        event = UserSignedUp(
            user_id=args.user_id,
            email="demo@example.com",
            first_name="Demo",
            country=args.country,
        )
    else:
        event = KycApproved(user_id=args.user_id, country=args.country, tier=args.tier)

    ok = publish_business_event(event)
    print(f"published={ok} detail_type={event.detail_type} country={args.country}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
