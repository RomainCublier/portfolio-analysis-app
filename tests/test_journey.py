from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core.journey import journey_progress, next_step
from core.planning import Project


@pytest.mark.parametrize("project,allocation,snapshot,page", [
    (None, None, None, "pages/commencer.py"),
    (Project(), {}, None, "pages/modeles.py"),
    (Project(), {"example": 100}, None, "pages/allocation.py"),
    (None, None, ([], 0, None), "pages/revue.py"),
    (Project(), {"example": 100}, ([], 0, None), "pages/revue.py"),
])
def test_next_step_uses_saved_work(project, allocation, snapshot, page):
    assert next_step(project, allocation, snapshot).page == page


@pytest.mark.parametrize("project,allocation,snapshot,completed", [
    (None, None, None, 0),
    (Project(), {}, None, 1),
    (Project(), {"example": 100}, None, 2),
    (Project(), {"example": 100}, ([], 0, None), 3),
])
def test_journey_progress_counts_only_saved_milestones(project, allocation, snapshot, completed):
    assert journey_progress(project, allocation, snapshot).completed == completed


def test_home_hides_internal_lab_by_default():
    root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(root / "app.py")).run()
    assert not app.exception
    assert any(item.value == "Commençons par votre projet" for item in app.subheader)
    assert not app.sidebar.checkbox


def test_internal_lab_can_be_explicitly_enabled(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("QUANTDESK_ENABLE_LAB", "true")
    app = AppTest.from_file(str(root / "app.py")).run()
    assert not app.exception
    assert not app.sidebar.checkbox[0].value
    app.sidebar.checkbox[0].check().run()
    assert not app.exception
