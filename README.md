# 🧭 Life Companions

A small Streamlit chatbot with five personas — a dietician, a fitness trainer, a coding teacher, a financial educator and a storyteller — powered by Claude.

**Bring your own key.** Paste your Anthropic API key in the sidebar and chat. The key is held in memory for your session only, never saved or logged, and used solely to call Anthropic's API. `app.py` is about 150 lines — read it to verify.

## Run locally

```bash
git clone <your-repo-url>
cd life-companions
pip install -r requirements.txt
streamlit run app.py
```

Opens at http://localhost:8501.

## Deploy free

Push to a public GitHub repo, then at share.streamlit.io → **New app** → pick the repo and `app.py`. Nothing to configure in secrets, because every user brings their own key.

## Add a companion

Add one entry to the `CHARACTERS` dict in `app.py`: a name, emoji, tagline, two example prompts, and a system prompt. The sidebar and chat pick it up automatically.

Each system prompt has two sections: *how you work* (voice, what to ask first, how to answer) and *where you stop* (what the persona hands off to a real professional). The advice-giving personas — diet, fitness, money — explain and educate; they don't diagnose, prescribe, or name products to buy.

## Cost

Whoever's key is used pays. Haiku 4.5 (the default) is about $1 per million input tokens and $5 per million output — a long conversation costs a fraction of a cent. You can set a monthly spend limit in the Anthropic console.

## Stack

Python · Streamlit · Anthropic Python SDK
