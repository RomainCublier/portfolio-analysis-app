"""Navigation based on saved work, without investment advice."""
from dataclasses import dataclass
from core.models import saved_choices


@dataclass(frozen=True)
class NextStep:
    title: str
    description: str
    page: str
    action: str


def next_step(project=None, allocation=None, snapshot=None):
    if snapshot is not None:
        return NextStep(
            "Faire le point sur mon portefeuille",
            "Retrouvez vos valeurs et vos apports pour comprendre votre évolution. Aucun ordre à passer n'est nécessaire pour faire le point.",
            "pages/revue.py", "Faire le point",
        )
    if project is None:
        return NextStep(
            "Commençons par votre projet",
            "Votre objectif, votre horizon et votre épargne : posez les bases avant de choisir des placements.",
            "pages/commencer.py", "Définir mon projet",
        )
    if not allocation:
        return NextStep(
            "Explorer mon premier portefeuille fictif",
            "Comparez des répartitions, découvrez leurs supports et conservez votre essai.",
            "pages/modeles.py", "Comparer les portefeuilles",
        )
    return NextStep(
        "Reprendre mon portefeuille fictif",
        "Votre essai est enregistré dans cette session. Retrouvez sa répartition et ses points de vigilance.",
        "pages/modeles.py" if saved_choices(allocation)[0] else "pages/allocation.py", "Revoir mon essai",
    )
