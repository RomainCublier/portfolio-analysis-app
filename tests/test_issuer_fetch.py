from datetime import date
from unittest.mock import MagicMock, patch

import pytest
import requests

from core.issuer_fetch import download_export, fetch_europe_bonds
from core.ishares_import import SOURCE_URL, BOND_SOURCE_URL


def response(status=200, chunks=(b'export',)):
    result = MagicMock()
    result.__enter__.return_value = result
    result.status_code = status
    result.iter_content.return_value = iter(chunks)
    return result


def test_fixed_source_streamed_without_redirects():
    with patch('core.issuer_fetch.requests.get', return_value=response()) as get:
        assert download_export(SOURCE_URL) == b'export'
        assert get.call_args.kwargs['allow_redirects'] is False
    with patch('core.issuer_fetch.requests.get') as get:
        with pytest.raises(ValueError):
            download_export('https://example.com/arbitrary')
        get.assert_not_called()


@pytest.mark.parametrize('status,chunks', [(302, (b'x',)), (403, (b'x',)), (200, ())])
def test_failed_downloads_not_accepted(status, chunks):
    with patch('core.issuer_fetch.requests.get', return_value=response(status, chunks)):
        with pytest.raises(ValueError):
            download_export(SOURCE_URL)


def test_size_and_network_failures_are_actionable():
    with patch('core.issuer_fetch.MAX_EXPORT_BYTES', 3), patch('core.issuer_fetch.requests.get', return_value=response(chunks=(b'four',))):
        with pytest.raises(ValueError, match='volumineux'):
            download_export(SOURCE_URL)
    with patch('core.issuer_fetch.requests.get', side_effect=requests.Timeout):
        with pytest.raises(ValueError, match='Connexion'):
            download_export(SOURCE_URL)


def test_pair_is_validated_before_returning_and_uses_exact_dates():
    start, end = date(2021, 12, 31), date(2022, 12, 30)
    result = (None, None, None, {'commercial_ready': False})
    with patch('core.issuer_fetch.download_export', side_effect=[b'europe', b'bonds']) as get, patch('core.issuer_fetch.import_multi_asset_exports', return_value=result) as parse:
        actual = fetch_europe_bonds(start, end)
        assert [c.args[0] for c in get.call_args_list] == [SOURCE_URL, BOND_SOURCE_URL]
        assert parse.call_args.args[:2] == (b'europe', b'bonds')
        assert parse.call_args.args[-2:] == (start, end)
        assert actual[3]['commercial_ready'] is False
        assert actual[3]['retrieval'] == 'direct_issuer_download'
    with patch('core.issuer_fetch.download_export') as get:
        with pytest.raises(ValueError):
            fetch_europe_bonds(end, start)
        get.assert_not_called()
