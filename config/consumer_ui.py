"""Lightweight layout for the retail journey; native controls retain their theme."""
CSS = """
<style>
[data-testid="stMainBlockContainer"] { max-width: 1120px; padding-top: 2rem; }
h1 { font-size: 2rem; letter-spacing: 0; }
h2 { font-size: 1.4rem; letter-spacing: 0; }
h3 { font-size: 1.15rem; letter-spacing: 0; }
[data-testid="stMetricValue"] { font-size: 1.65rem; overflow-wrap: anywhere; }
[data-testid="stMetricLabel"] { white-space: normal; }
@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"] { padding: 1rem; }
  h1 { font-size: 1.65rem; }
}
</style>
"""
