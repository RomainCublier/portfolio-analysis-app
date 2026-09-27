from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_pea_cto_page_is_plain_language_and_links_official_sources():
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / "pages/enveloppes.py")).run()
    assert not app.exception
    assert app.title[0].value == "Comprendre le PEA et le CTO"
    table = app.dataframe[0].value
    assert list(table.columns) == ["Question", "PEA", "CTO"]
    assert len(table) == 4
    urls = [button.url for button in app.get("link_button")]
    assert any("amf-france.org" in url for url in urls)
    assert any("service-public.fr" in url for url in urls)
