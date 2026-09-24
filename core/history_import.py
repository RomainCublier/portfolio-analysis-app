"""Untrusted research imports: validate bytes, never grant commercial rights."""
import csv
from dataclasses import asdict, replace
import hashlib
import io
import json
import re

import pandas as pd
from core.history import SeriesMetadata, validate_panel

MAX_BYTES = 5_000_000


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Clé JSON répétée : {key}")
        result[key] = value
    return result


def import_history(csv_bytes, manifest_bytes):
    """Calendar is supplied separately; completeness is relative to that declaration.

    The uploader's metadata is not independently verified. Commercial approval
    cannot be acquired through a client-supplied manifest.
    """
    try:
        if not csv_bytes or not manifest_bytes or max(len(csv_bytes), len(manifest_bytes)) > MAX_BYTES:
            raise ValueError("Deux fichiers non vides de 5 Mo maximum sont requis.")
        manifest = json.loads(manifest_bytes.decode("utf-8"), object_pairs_hook=_json_object)
        if set(manifest) != {"schema_version", "expected_dates", "calendar_source_url", "series"} or manifest["schema_version"] != 1:
            raise ValueError("Structure du manifeste non reconnue.")
        if not isinstance(manifest["calendar_source_url"], str) or not manifest["calendar_source_url"].startswith("https://"):
            raise ValueError("Source du calendrier requise.")
        rows = list(csv.reader(io.StringIO(csv_bytes.decode("utf-8-sig")), strict=True))
        if len(rows) < 3 or len(rows[0]) < 2 or rows[0][0] != "date":
            raise ValueError("CSV attendu : date,identifiant… et au moins deux observations.")
        header = rows[0]
        if len(set(header)) != len(header) or any(not x.strip() for x in header):
            raise ValueError("Identifiants vides ou répétés.")
        if any(len(row) != len(header) for row in rows[1:]):
            raise ValueError("Lignes CSV de longueur incohérente.")
        dates = [row[0] for row in rows[1:]]
        expected = manifest["expected_dates"]
        if not isinstance(expected, list) or any(not isinstance(d, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) for d in dates + expected):
            raise ValueError("Dates au format AAAA-MM-JJ requises.")
        levels = pd.DataFrame([row[1:] for row in rows[1:]], columns=header[1:],
                              index=pd.DatetimeIndex(pd.to_datetime(dates, format="%Y-%m-%d"))).astype(float)
        digest = hashlib.sha256(csv_bytes).hexdigest()
        metadata = {}
        for key, entry in manifest["series"].items():
            m = SeriesMetadata(**entry)
            if m.raw_sha256 != digest:
                raise ValueError("Empreinte du fichier différente de celle déclarée dans le manifeste.")
            metadata[key] = replace(m, license_status="unknown", license_reference="")
        calendar = pd.DatetimeIndex(pd.to_datetime(expected, format="%Y-%m-%d"))
        report = validate_panel(levels, metadata, calendar)
        report.update(raw_sha256=digest, calendar_source_url=manifest["calendar_source_url"],
                      verification="technical_only", commercial_ready=False,
                      sources={k: m.source_url for k, m in metadata.items()},
                      retrieved_at={k: m.retrieved_at for k, m in metadata.items()},
                      metadata={k: asdict(m) for k, m in metadata.items()})
        return levels, metadata, calendar, report
    except (TypeError, KeyError, AttributeError, UnicodeError, csv.Error, OverflowError) as exc:
        raise ValueError("Fichiers invalides : vérifier le format CSV et le manifeste JSON.") from exc
