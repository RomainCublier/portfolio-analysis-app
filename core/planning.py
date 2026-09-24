"""Deterministic educational projections. No market forecasts or recommendations."""
from dataclasses import asdict, dataclass
import json
import math


def number(value, name, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{name} : nombre attendu.")
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{name} : valeur hors limites.")
    return value


@dataclass(frozen=True)
class Project:
    goal: str = "Faire grandir mon épargne"
    initial: float = 0.0
    monthly: float = 100.0
    years: int = 10
    reserve: str = "À constituer"
    experience: str = "Je débute"
    loss_reaction: str = "Je ne sais pas encore"

    def __post_init__(self):
        number(self.initial, "Capital", 0, 100_000_000)
        number(self.monthly, "Versement", 0, 1_000_000)
        number(self.years, "Horizon", 1, 50)
        if not isinstance(self.years, int):
            raise ValueError("L’horizon doit être un nombre entier d’années.")
        for value in (self.goal, self.reserve, self.experience, self.loss_reaction):
            if not isinstance(value, str) or not value.strip() or len(value) > 200:
                raise ValueError("Description du projet invalide.")


def project_path(project, annual_return, annual_fee=0.0, inflation=0.0):
    """Effective annual factors; fees compounded; contributions at month end.

    Nominal constant contributions, no tax, no volatility; real balances in
    today's euros. This is neither a backtest nor a probabilistic simulation.
    """
    number(annual_return, "Rendement", -0.99, 1)
    number(annual_fee, "Frais", 0, 0.1)
    number(inflation, "Inflation", 0, 0.2)
    growth = ((1 + annual_return) * (1 - annual_fee)) ** (1 / 12)
    value = project.initial
    rows = []
    for month in range(project.years * 12 + 1):
        if month:
            value = value * growth + project.monthly
        contributed = project.initial + month * project.monthly
        rows.append({"Mois": month, "Versements cumulés": contributed,
                     "Capital simulé": value, "Gain / perte simulé(e)": value - contributed,
                     "Capital en euros d’aujourd’hui": value / (1 + inflation) ** (month / 12)})
    return rows


def export_project(project):
    return json.dumps({"version": 1, "kind": "investment_project", "project": asdict(project)},
                      ensure_ascii=False, indent=2)


def import_project(raw):
    if len(raw) > 20_000:
        raise ValueError("Fichier trop volumineux.")
    try:
        data = json.loads(raw)
        if data["version"] != 1 or data["kind"] != "investment_project":
            raise ValueError("Format non reconnu.")
        return Project(**data["project"])
    except (KeyError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Fichier projet invalide.") from exc
