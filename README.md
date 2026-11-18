# 🌾 Legit88

Paste a farm-job ad (or upload a screenshot) and get a 🔴 / 🟠 / 🟢 verdict, the reasons, and questions to ask the employer.
Built for Working Holiday backpackers who need 88 days of regional farm work for a second visa.

**How it works:** the AI only *reads* the ad. The verdict comes from simple rules and official data. Legit88 reports *risk signals*; it never accuses anyone.

```
ad (text / screenshot) -> extractor.py (AI, or regex fallback) -> checks.py + abn.py -> verdict.py -> app.py
```

Verdict: any red signal -> RED, 2+ orange -> ORANGE, otherwise GREEN.

## Run it on your computer

Needs Python 3.10+. In a terminal, inside this folder:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m pytest                # tests need no keys
streamlit run app.py            # opens http://localhost:8501
```

Without keys the app runs in **demo mode** (the ad is read with regex rules). Screenshots need the AI key.

### Keys (optional)

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in:

- `OPENROUTER_API_KEY` from openrouter.ai (model: `google/gemini-2.5-flash`)
- `ABN_LOOKUP_GUID` (free) from abr.business.gov.au -> Web services registration

`secrets.toml` is in `.gitignore`: never commit it.

## Deploy (free)

1. Push this folder to a GitHub repository (without `secrets.toml`).
2. Go to share.streamlit.io, sign in with GitHub, **Create app**, pick the repo, branch `main`, file `app.py`.
3. **Advanced settings -> Secrets**: paste the content of your `secrets.toml`.
4. Deploy. You get a public `*.streamlit.app` link.

## Data sources (check them before the demo)

| Data | Where in the code | Official source | Status |
|---|---|---|---|
| Horticulture Award minimums: A$25.74/h, A$32.18/h casual (from 1 July 2026) | top of `legit88/checks.py` | horticulture.fairwork.gov.au/pay-and-piece-rates | confirmed |
| Regional postcodes for 88 days | `data/regional_postcodes.csv` | immi.homeaffairs.gov.au (Working Holiday, specified work) | VIC / QLD / WA rows marked `to_verify` |
| ABN checksum + live lookup | `legit88/abn.py` | abr.business.gov.au (ABN Lookup web services) | official algorithm |
| Labour hire licence registers (QLD, VIC, SA) | `LABOUR_HIRE_REGISTERS` in `checks.py` | state government sites | links only |

## Usage tracking

Each analysis (verdict only, no ad text) and each click on the fake-door "88-day pass" button is appended to `data/events.csv` (git-ignored). On Streamlit Cloud this file is erased when the app restarts, so note the numbers regularly.

## Known limits

- Hospitality work counts only in some areas: it is flagged orange, not fully checked.
- Labour hire licences are linked, not looked up automatically.
- The old French documentation is in `README.fr.md`.
