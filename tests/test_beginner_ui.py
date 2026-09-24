from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_project_form_and_projection():
    app = AppTest.from_file(str(ROOT / "pages/commencer.py")).run()
    assert not app.exception
    app.number_input[0].set_value(1000)
    app.number_input[1].set_value(1000)
    app.slider[0].set_value(20)
    app.button[1].click().run()
    assert not app.exception
    assert app.metric[0].value == "241 000 €"
    assert app.metric[1].value == "241 000 €"
    assert app.session_state.project.years == 20


def test_real_snapshot_empty_and_cash_only():
    app = AppTest.from_file(str(ROOT / "pages/positions_reelles.py")).run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    assert app.metric[0].value == "0.00 €"
    app.number_input[0].set_value(250)
    app.button[0].click().run()
    assert not app.exception
    assert app.metric[0].value == "250.00 €"


def test_real_snapshot_groups_duplicates_without_losing_value():
    import pandas as pd
    app = AppTest.from_file(str(ROOT / "pages/positions_reelles.py"))
    app.session_state.real_positions = pd.DataFrame({
        "Compte": ["PEA", "PEA", "CTO"], "Support / ISIN": ["A", "A", "B"],
        "Valeur actuelle (€)": [100., 200., 300.]})
    app.run().button[0].click().run()
    assert not app.exception
    assert app.metric[0].value == "600.00 €"
    assert len(app.dataframe[-1].value) == 2


def test_navigation_opens_beginner_page_without_market_calls():
    app = AppTest.from_file(str(ROOT / "app.py")).run()
    assert not app.exception
    assert app.title[0].value == "Mon assistant"


def test_assistant_saves_note_and_displays_only_declared_value():
    import pandas as pd
    from datetime import date
    app = AppTest.from_file(str(ROOT / 'app.py'))
    app.session_state.real_snapshot = (pd.DataFrame({'Compte': ['PEA'], 'Support / ISIN': ['A'], 'Valeur actuelle (€)': [100.]}), 50., date(2025, 1, 1))
    app.run()
    app.text_area[0].set_value('Mon horizon reste inchangé.')
    app.button[0].click().run()
    assert not app.exception
    assert app.metric[0].value == '150.00 €'
    assert app.session_state.decision_journal[0]['note'] == 'Mon horizon reste inchangé.'


def test_saved_positions_reopen_with_cash_and_date():
    import pandas as pd
    from datetime import date
    app = AppTest.from_file(str(ROOT / 'pages/positions_reelles.py'))
    frame = pd.DataFrame({'Compte': ['CTO'], 'Support / ISIN': ['A'], 'Valeur actuelle (€)': [100.]})
    app.session_state.real_positions = frame
    app.session_state.real_snapshot = (frame, 50., date(2025, 1, 1))
    app.run().button[0].click().run()
    assert not app.exception
    assert app.metric[0].value == '150.00 €'
    assert app.date_input[0].value == date(2025, 1, 1)
