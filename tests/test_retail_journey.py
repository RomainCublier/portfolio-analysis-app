from io import BytesIO
from pathlib import Path

from streamlit.testing.v1 import AppTest

from core.dossier import export_dossier
from core.journey import next_step
from core.planning import Project

ROOT = Path(__file__).resolve().parents[1]


def test_every_public_v1_page_renders_without_external_credentials():
    app = AppTest.from_file(str(ROOT / "app.py")).run()
    pages = [
        "pages/assistant.py", "pages/dossier.py", "pages/offre.py",
        "pages/informations.py", "pages/commencer.py", "pages/enveloppes.py",
        "pages/modeles.py", "pages/revue.py", "pages/positions_reelles.py",
        "pages/suivi.py", "pages/catalogue.py", "pages/allocation.py",
    ]
    for page in pages:
        app.switch_page(page).run()
        assert not app.exception, page


def test_full_navigation_project_portfolio_and_dossier():
    app = AppTest.from_file(str(ROOT / 'app.py')).run()
    app.switch_page('pages/commencer.py').run()
    app.number_input[0].set_value(1000)
    app.number_input[1].set_value(100)
    next(b for b in app.button if b.label == 'Enregistrer mon projet').click().run()
    assert not app.exception
    app.switch_page('pages/modeles.py').run()
    app.radio[0].set_value('60/40').run()
    app.selectbox[0].select('IE0002XZSHO1')
    app.selectbox[1].select('IE00BDBRDM35').run()
    next(b for b in app.button if b.label == 'Garder ce portefeuille fictif').click().run()
    assert not app.exception
    app.switch_page('pages/dossier.py').run()
    assert not app.exception
    assert app.get('download_button')
    app.switch_page('pages/modeles.py').run()
    assert not app.exception
    assert app.radio[0].value == '60/40'
    assert app.selectbox[0].value == 'IE0002XZSHO1'
    assert app.selectbox[1].value == 'IE00BDBRDM35'


def test_saved_example_returns_to_guided_page():
    step = next_step(Project(), {'IE0002XZSHO1': .6, 'IE00BDBRDM35': .4})
    assert step.page == 'pages/modeles.py'
    custom = next_step(Project(), {'IE0002XZSHO1': .65, 'IE00BDBRDM35': .35})
    assert custom.page == 'pages/allocation.py'


def test_dossier_restore_is_available_without_an_account_and_requires_confirmation():
    raw = export_dossier({'project': Project(goal='Mon projet retrouvé'),
                          'allocation_draft': {'IE0002XZSHO1': .6, 'IE00BDBRDM35': .4}}).encode()
    script = f'''
from unittest.mock import patch
from io import BytesIO
import runpy
with patch('streamlit.file_uploader', return_value=BytesIO({raw!r})):
    runpy.run_path({str(ROOT / 'pages/dossier.py')!r}, run_name='__main__')
'''
    app = AppTest.from_string(script).run()
    assert not app.exception
    assert app.button[0].disabled
    app.checkbox[0].check().run()
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state['project'].goal == 'Mon projet retrouvé'
    assert next_step(app.session_state['project'], app.session_state['allocation_draft']).page == 'pages/modeles.py'
