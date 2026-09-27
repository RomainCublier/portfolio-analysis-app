"""Investor profile framing without product recommendation."""
from __future__ import annotations

from dataclasses import dataclass

from core.planning import Project


@dataclass(frozen=True)
class ProfileFrame:
    horizon_bucket: str
    risk_budget: str
    complexity: str
    equity_floor: float
    equity_ceiling: float
    stock_picking_cap: float
    reserve_message: str
    envelope_notes: tuple[str, ...]
    building_blocks: tuple[dict[str, str], ...]
    guardrails: tuple[str, ...]


def profile_frame(project: Project) -> ProfileFrame:
    """Translate user inputs into an explainable investment frame.

    This is a rules-based education layer: no expected return, no suitability
    conclusion and no claim that a given instrument is appropriate for a person.
    """
    if not isinstance(project, Project):
        raise ValueError("Projet invalide.")

    defensive = project.years <= 3 or project.loss_reaction == "J’aurais besoin de récupérer cet argent"
    long_horizon = project.years >= 8 and project.loss_reaction == "Je pourrais attendre malgré la baisse"
    experienced = project.experience == "J’ai déjà investi"

    if project.years <= 3:
        horizon_bucket = "Court terme"
    elif project.years <= 7:
        horizon_bucket = "Moyen terme"
    else:
        horizon_bucket = "Long terme"

    if defensive:
        risk_budget = "Préservation prioritaire"
        equity_floor, equity_ceiling = 0.0, 0.35
        stock_picking_cap = 0.0
    elif long_horizon:
        risk_budget = "Croissance assumée"
        equity_floor, equity_ceiling = 0.60, 1.0
        stock_picking_cap = 0.20 if experienced else 0.0
    else:
        risk_budget = "Croissance encadrée"
        equity_floor, equity_ceiling = 0.30, 0.75
        stock_picking_cap = 0.10 if experienced else 0.0

    complexity = "ETF et fonds diversifiés" if experienced else "ETF larges et liquidités"
    reserve_message = (
        "Épargne de précaution déclarée disponible : le projet peut être analysé séparément du coussin de sécurité."
        if project.reserve == "Déjà disponible"
        else "Épargne de précaution non confirmée : commencer par isoler les liquidités nécessaires aux imprévus."
    )
    envelope_notes = (
        "PEA : enveloppe utile pour les actions européennes et certains ETF éligibles, avec contraintes d’éligibilité à vérifier support par support.",
        "CTO : univers plus large, notamment ETF internationaux, obligations, fonds non éligibles PEA et actions étrangères, avec fiscalité à traiter séparément.",
    )
    blocks = [
        {"role": "Liquidités / monétaire", "use": "Réserve, attente, risque de marché limité", "catalog_filter": "Taux au jour le jour"},
        {"role": "Actions mondiales", "use": "Moteur de croissance diversifié", "catalog_filter": "Actions — marchés développés"},
        {"role": "Actions Europe / PEA", "use": "Brique actions potentiellement logeable en PEA si éligibilité documentée", "catalog_filter": "Actions — Europe"},
    ]
    if project.years >= 5:
        blocks.append({"role": "Small caps", "use": "Complément plus volatil, à plafonner dans l’allocation", "catalog_filter": "petites capitalisations"})
        blocks.append({"role": "Marchés émergents", "use": "Complément actions plus risqué, devise et pays à surveiller", "catalog_filter": "marchés émergents"})
    if not defensive:
        blocks.append({"role": "Obligations investment grade", "use": "Diversification et réduction potentielle de volatilité, risque de taux inclus", "catalog_filter": "Obligations"})
    if experienced:
        blocks.append({"role": "Fonds actifs", "use": "Sélection qualitative à documenter : frais, mandat, benchmark, équipe, encours, historique", "catalog_filter": "gestion active"})
        blocks.append({"role": "Actions individuelles", "use": f"Satellite plafonné à {stock_picking_cap:.0%} du portefeuille modèle", "catalog_filter": "Action individuelle"})

    guardrails = (
        "Un portefeuille modèle doit totaliser 100 %, rester long-only et afficher les poches non couvertes par les données.",
        "Aucun rendement attendu n’est déduit du profil : les simulations doivent séparer versements, performance et frais.",
        "Le stock picking reste une poche satellite, jamais le socle de diversification.",
        "Les fonds et ETF doivent garder leur source officielle, leur date de revue et leur statut de données de marché.",
    )
    return ProfileFrame(
        horizon_bucket=horizon_bucket,
        risk_budget=risk_budget,
        complexity=complexity,
        equity_floor=equity_floor,
        equity_ceiling=equity_ceiling,
        stock_picking_cap=stock_picking_cap,
        reserve_message=reserve_message,
        envelope_notes=envelope_notes,
        building_blocks=tuple(blocks),
        guardrails=guardrails,
    )


def matching_catalog_rows(rows, block, limit=4):
    if not isinstance(limit, int) or limit <= 0:
        raise ValueError("Limite invalide.")
    needle = block["catalog_filter"].casefold()
    matches = []
    for row in rows:
        haystack = " ".join([row.get("category", ""), row.get("name", ""), row.get("instrument_kind", "")]).casefold()
        if needle in haystack:
            matches.append(row)
    return matches[:limit]
