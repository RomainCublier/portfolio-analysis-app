"""On-demand research downloads from two fixed issuer endpoints."""
from datetime import datetime, timezone
import time

import requests

from core.ishares_import import SOURCE_URL, BOND_SOURCE_URL, import_multi_asset_exports
from core.ishares_import import WORLD_SOURCE_URL, import_world_bond_exports
from core.wpea_import import SOURCE_URL as WPEA_SOURCE_URL, import_wpea_bonds

MAX_EXPORT_BYTES = 32_000_000


def download_export(url):
    if url not in (SOURCE_URL, BOND_SOURCE_URL, WORLD_SOURCE_URL, WPEA_SOURCE_URL):
        raise ValueError('Source non prise en charge.')
    started = time.monotonic()
    try:
        with requests.get(url, stream=True, timeout=(15, 15), allow_redirects=False) as response:
            if response.status_code != 200:
                raise ValueError(f'Source indisponible (HTTP {response.status_code}). Réessayez plus tard ou importez l’export officiel.')
            chunks, size = [], 0
            for chunk in response.iter_content(chunk_size=65536):
                size += len(chunk)
                if size > MAX_EXPORT_BYTES or time.monotonic() - started > 30:
                    raise ValueError('Téléchargement trop volumineux ou trop lent.')
                chunks.append(chunk)
            raw = b''.join(chunks)
            if not raw:
                raise ValueError('Le fournisseur a renvoyé un fichier vide.')
            return raw
    except requests.RequestException as exc:
        raise ValueError('Connexion au fournisseur impossible. Réessayez plus tard ou utilisez l’import de fichier.') from exc


def fetch_europe_bonds(start, end):
    return _fetch_pair(SOURCE_URL, import_multi_asset_exports, start, end)


def fetch_world_bonds(start, end):
    return _fetch_pair(WORLD_SOURCE_URL, import_world_bond_exports, start, end)


def fetch_wpea_bonds(start, end):
    return _fetch_pair(WPEA_SOURCE_URL, import_wpea_bonds, start, end)


def _fetch_pair(stock_url, parser, start, end):
    if start >= end:
        raise ValueError('La fin doit suivre le début de la période.')
    europe = download_export(stock_url)
    bonds = download_export(BOND_SOURCE_URL)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    result = parser(europe, bonds, retrieved_at, start, end)
    result[3]['retrieval'] = 'direct_issuer_download'
    result[3]['retrieved_at'] = retrieved_at
    return result
