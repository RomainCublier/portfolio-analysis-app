"""A factual review of declared records, without inferred performance."""
from datetime import date
import math

from core.tracking import validate_tracking


def review_summary(valuations, flows, today=None):
    validate_tracking(valuations, flows)
    today = today or date.today()
    ordered = sorted(valuations, key=lambda row: row['date'])
    latest = ordered[-1] if ordered else None
    previous = ordered[-2] if len(ordered) > 1 else None
    included = [flow for flow in flows
                if previous and previous['date'] < flow['date'] <= latest['date']]
    pending = [flow for flow in flows if latest and flow['date'] > latest['date']]
    return {
        'latest': latest,
        'previous': previous,
        'age_days': (today - date.fromisoformat(latest['date'])).days if latest else None,
        'movement_count': len(included),
        'declared_net_flows': math.fsum(flow['amount'] for flow in included) if previous else None,
        'pending_count': len(pending),
    }
