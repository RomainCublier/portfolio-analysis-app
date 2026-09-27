"""Editorial allocation examples, not optimized or profile-selected portfolios."""
from core.planning import number
import math

MODELS = {
    '30/70': {'equity': 0.30, 'description': 'Une place plus importante aux obligations.'},
    '60/40': {'equity': 0.60, 'description': 'Une majorité d’actions, complétée par des obligations.'},
    '90/10': {'equity': 0.90, 'description': 'Une exposition principalement aux actions.'},
}
EQUITY_EXAMPLES = ('IE00B4L5Y983', 'FR001400U5Q4', 'FR0000284689', 'IE00B4K48X80', 'IE00B441G979', 'IE0002XZSHO1')
BOND_EXAMPLES = ('IE00BDBRDM35',)


def saved_choices(weights):
    """Resume exact examples without coercing custom allocations."""
    for stock in EQUITY_EXAMPLES:
        for bond in BOND_EXAMPLES:
            if set(weights) == {stock, bond}:
                for name, model in MODELS.items():
                    if math.isclose(weights[stock], model['equity'], abs_tol=1e-10, rel_tol=0) and math.isclose(weights[bond], 1 - model['equity'], abs_tol=1e-10, rel_tol=0):
                        return name, stock, bond
    return None, None, None


def model_weights(model, equity_isin, bond_isin, catalog):
    if model not in MODELS:
        raise ValueError('Exemple inconnu.')
    available = {row['isin'] for row in catalog}
    if equity_isin not in EQUITY_EXAMPLES or bond_isin not in BOND_EXAMPLES:
        raise ValueError('Choisissez un exemple de support pour chaque poche.')
    if not {equity_isin, bond_isin} <= available:
        raise ValueError('Un support est absent du catalogue actuel.')
    equity = MODELS[model]['equity']
    return {equity_isin: equity, bond_isin: 1 - equity}


def hypothetical_change(model, equity_change, bond_change):
    number(equity_change, 'Variation actions', -1, 1)
    number(bond_change, 'Variation obligations', -1, 1)
    equity = MODELS[model]['equity']
    return equity * equity_change + (1 - equity) * bond_change


def keep_model(state, weights):
    # The existing editor stores widget values separately from the saved draft.
    for key in list(state):
        if key.startswith('allocation_') and key != 'allocation_draft':
            del state[key]
    state['allocation_draft'] = dict(weights)
