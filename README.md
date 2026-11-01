# Campus Cup — Feedback to Focus

A Streamlit assignment app that collects customer feedback, labels written comments with a Groq-hosted LLM, and helps a fictional café choose its next improvement.

## Business question

**Which part of the customer experience should Campus Cup improve first?**

## Labels

Every written comment gets exactly one label:

| Label | Definition |
| --- | --- |
| Product quality | A requested improvement to the taste, temperature, freshness, or availability of food and drinks. |
| Speed | A requested improvement to queue length, ordering time, or food and drink preparation time. |
| Service | A requested improvement to staff courtesy, helpfulness, communication, or order accuracy. |
| Value | A requested improvement to prices, portion sizes, or value for money. |
| Space & cleanliness | A requested improvement to seating, noise, Wi-Fi, accessibility, or cleanliness. |
| No improvement requested | Praise or a neutral café-related comment without a requested or implied improvement. |
| Manual review | The main improvement is unclear, equally split across issues, unrelated to the café, or could not be reliably labeled. |

Choose the main issue explicitly prioritized by the customer. If distinct issues are equally important, review manually. Praise about a topic is not counted as a complaint about it.

## Features

- Customer form accepts 1–5 stars, a comment, or both; rejects an empty submission.
- Every written comment is sent to Groq when configured. The app validates the JSON label, confidence, and reason. Missing keys, invalid output, API failures, and confidence below 0.75 result in a saved Manual review label. No keyword classifier or simulated LLM is used for live feedback.
- Rating-only submissions have no comment label.
- SQLite stores submissions across visitors, including model/prompt metadata and review history fields. Duplicate submission IDs are ignored.
- Owner side has three KPIs: submissions, average stars, and comments needing manual review; two graphs; full review comments; manual correction; AI retry; CSV export.
- The business answer ranks the five improvement labels by frequency; ties are explicit. Praise, rating-only submissions, and pending reviews are excluded.
- Separate, fictional, **hand-labeled example data** demonstrates charts without contaminating live data. It is not represented as LLM output.

## Run locally

```bash
python -m pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit the local secrets.toml privately with your own Groq API key.
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Use this public repository, branch `main`, entry point `app.py`, Python 3.12.
2. In Advanced settings (or app Settings → Secrets), add:

```toml
GROQ_API_KEY = "YOUR_GROQ_API_KEY"
GROQ_MODEL = "llama-3.3-70b-versatile"
```

3. Save and deploy. Obtain a free key at https://console.groq.com/keys.
4. Submit a clear complaint such as “The morning line takes 20 minutes; please speed it up.” Verify the saved label is Speed and appears on the live dashboard.

**Never put the real key in GitHub.** `.streamlit/secrets.toml`, environment files, and live SQLite data are ignored. Only the placeholder example is tracked. Without the key, the app stays usable but openly marks written feedback for review; the LLM requirement is not complete until a working key is configured and tested.

## Limits and responsible use

This is a public classroom demo, not an authenticated production customer system. Feedback and manual-label controls are public. Do not submit personal or confidential information. Written comments are sent to Groq for classification when configured. Owner exports include complete comments.

SQLite saves to the app server, **but Streamlit Community Cloud does not guarantee local file persistence**. A restart/redeploy may erase the data. Export CSV before changes. A real business deployment should use an external database and owner authentication.

Self-reported model confidence is an uncalibrated review heuristic. Comment volume is not representative of all customers, and count-based priority does not measure severity. Review labels before business decisions. The app sends only the comment, not its star rating, to the LLM and never follows instructions embedded in comments.

Official references: [Groq JSON output](https://console.groq.com/docs/structured-outputs), [Streamlit secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management), [Streamlit storage limits](https://docs.streamlit.io/develop/concepts/connections/connecting-to-data).

## Tests

```bash
python -m pip install pytest
python -m pytest -q
```

Tests cover validation, malformed/provider-failed LLM responses, the single-label rule, rating-only feedback, idempotent persistence, owner review, ties, metric denominators, and Streamlit page/form behavior. LLM mocks test error handling; a deployed Groq smoke test is still needed to validate credentials and real model access.
