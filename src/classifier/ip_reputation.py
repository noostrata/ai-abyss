# AI Abyss — Proof of Concept (2026)
# https://github.com/terrorswift/ai-abyss
# IP reputation and ASN lookup for known AI company infrastructure

from __future__ import annotations

import ipaddress
import json
from dataclasses import dataclass
from pathlib import Path

try:
    import maxminddb
    HAS_MAXMIND = True
except ImportError:
    HAS_MAXMIND = False


@dataclass
class IPReputation:

    is_known_ai_range: bool
    org: str | None
    asn: str | None
    source: str


class IPReputationChecker:

    def __init__(
        self,
        ip_data_path: str | Path = "data/ai_crawler_ips.json",
        maxmind_db_path: str | Path | None = None,
    ) -> None:
        self._known_ranges: list[tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, str, str]] = []
        self._known_asns: dict[str, dict] = {}
        self._maxmind_reader: object | None = None
        self._load_ip_data(Path(ip_data_path))
        if maxmind_db_path and HAS_MAXMIND:
            self._load_maxmind(Path(maxmind_db_path))

    def _load_ip_data(self, path: Path) -> None:
        if not path.exists():
            return
        with open(path) as f:
            data = json.load(f)
        for entry in data.get("ranges", []):
            try:
                network = ipaddress.ip_network(entry["cidr"], strict=False)
                self._known_ranges.append((network, entry["org"], "IP range match"))
            except ValueError:
                continue
        for entry in data.get("asns", []):
            self._known_asns[entry["asn"]] = entry

    def _load_maxmind(self, path: Path) -> None:
        if path.exists() and HAS_MAXMIND:
            self._maxmind_reader = maxminddb.open_database(str(path))

    def lookup_ip(self, ip_str: str) -> IPReputation:
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            return IPReputation(
                is_known_ai_range=False, org=None, asn=None, source="invalid IP"
            )

        for network, org, source in self._known_ranges:
            if addr in network:
                return IPReputation(
                    is_known_ai_range=True, org=org, asn=None, source=source
                )

        asn_info = self._lookup_asn(ip_str)
        if asn_info:
            asn_str = f"AS{asn_info.get('autonomous_system_number', '')}"
            org = asn_info.get("autonomous_system_organization", "")
            if asn_str in self._known_asns:
                return IPReputation(
                    is_known_ai_range=True,
                    org=self._known_asns[asn_str].get("org", org),
                    asn=asn_str,
                    source="ASN match",
                )
            return IPReputation(
                is_known_ai_range=False, org=org, asn=asn_str, source="ASN lookup"
            )

        return IPReputation(
            is_known_ai_range=False, org=None, asn=None, source="no match"
        )

    def _lookup_asn(self, ip_str: str) -> dict | None:
        if not self._maxmind_reader or not HAS_MAXMIND:
            return None
        try:
            return self._maxmind_reader.get(ip_str)  # type: ignore[union-attr]
        except Exception:
            return None

    def score(self, ip_str: str) -> tuple[float, IPReputation]:
        rep = self.lookup_ip(ip_str)
        if rep.is_known_ai_range:
            # ASN-only match is weaker — many legit services use the same ASNs
            if rep.source == "ASN match":
                return 0.5, rep
            return 0.8, rep
        return 0.0, rep
