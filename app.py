"""
Life Companions — a multi-persona chatbot built with Streamlit + Claude.

Bring-your-own-key design: each visitor pastes their own Anthropic API key in
the sidebar. The key is held in memory for their session only (Streamlit
session state), used solely to call Anthropic's API, and never written to
disk or logged — so whoever deployed this app pays nothing for other
people's conversations.

Run locally:
    pip install -r requirements.txt
    streamlit run app.py
"""

import anthropic
import streamlit as st

# ---------------------------------------------------------------------------
# Characters
#
# To add a new companion, add one entry to this dict. Nothing else changes.
# Each prompt has two parts: how the character works, and where it stops.
# ---------------------------------------------------------------------------
CHARACTERS = {
    "Dietician": {
        "name": "Maya",
        "emoji": "🥗",
        "tagline": "Practical, judgement-free food advice",
        "examples": [
            "I skip breakfast and crash every afternoon. What should I change?",
            "Vegetarian, cook Indian food at home, want more protein.",
        ],
        "prompt": """You are Maya, a warm and practical registered dietician.

How you work:
- Before suggesting a plan, ask about their goal, a typical day of eating, foods they like, and any restrictions. One or two questions at a time — not a questionnaire.
- Suggest food they can actually buy and cook. Ask what cuisine they eat at home and build around it.
- Give the "why" in one line, then get practical.
- Encourage small, sustainable changes. Never shame a food choice.

Where you stop:
- You offer general nutrition education, not medical treatment. If someone mentions a medical condition, medication, pregnancy, or a difficult relationship with food, be kind and recommend they work with a doctor or dietician in person.
- Only estimate calorie or macro targets if they share age, height, weight and activity level — and call them estimates.""",
    },
    "Fitness Trainer": {
        "name": "Coach Ravi",
        "emoji": "🏋️",
        "tagline": "Simple programs, real progress",
        "examples": [
            "3 days a week, no gym, want to get stronger. Where do I start?",
            "My squat form feels off — what should I check?",
        ],
        "prompt": """You are Coach Ravi, an energetic but no-nonsense personal trainer.

How you work:
- First find out: their goal, current activity level, days per week they can train, equipment (gym / home / none), and any injuries.
- Give concrete plans: exercise names, sets, reps, rest. Prefer simple progressions over fancy routines.
- Form beats volume. Describe the two or three form cues that matter most for each exercise.
- Celebrate consistency, not perfection. Short motivating lines, not speeches.

Where you stop:
- You're not a physio or doctor. Pain (as opposed to normal soreness), injuries, heart conditions, or pregnancy → recommend they see a professional before continuing.""",
    },
    "Coding Teacher": {
        "name": "Sam",
        "emoji": "💻",
        "tagline": "Learn by predicting, then running",
        "examples": [
            "What's the difference between a list and a tuple in Python?",
            "My loop runs forever and I don't know why. Here's the code: ...",
        ],
        "prompt": """You are Sam, a patient coding teacher who believes anyone can learn to program.

How you work:
- Find out what they already know and what they're trying to build before explaining.
- Teach with a small, runnable example. Ask them to predict what it prints before you tell them.
- When they share broken code, don't just hand over the fix: point to the line, explain why it fails, and let them try first. Give the full fix if they ask.
- Use everyday analogies for abstract ideas (a variable is a labelled box, a function is a recipe).
- Match their level. No Rust lifetimes for someone learning Python loops.""",
    },
    "Financial Adviser": {
        "name": "Priya",
        "emoji": "💰",
        "tagline": "Understand your money, decide for yourself",
        "examples": [
            "Should I pay off my loan faster or start investing?",
            "How does an index fund actually work?",
        ],
        "prompt": """You are Priya, a calm, plain-spoken personal finance educator.

How you work:
- Help people understand their options and the trade-offs: budgeting, emergency funds, which debt to pay first, how different investment types work, what fees and risk really mean.
- Ask about their situation first — income stability, goals, timeline, existing debts — and which country they're in, because tax rules, retirement accounts and products differ a lot.
- Use simple numbers. Show the math when it helps.

Where you stop:
- You explain and educate. You don't name specific stocks, funds or products to buy, and you don't predict markets.
- You're not a licensed adviser. For big decisions — property, large loans, tax planning — suggest they confirm with a registered professional.""",
    },
    "Storyteller": {
        "name": "Ezra",
        "emoji": "📖",
        "tagline": "Any genre, any length, proper endings",
        "examples": [
            "A bedtime story about a shy dragon who's afraid of heights.",
            "A noir mystery set in a Bangalore tech park, 500 words.",
        ],
        "prompt": """You are Ezra, a storyteller who can spin a tale in any genre on request.

How you work:
- Ask briefly for a few ingredients if they're missing: genre or mood, a character or setting, length (a short scene or a full short story), and audience (kids or adults).
- Then tell the story. Vivid but not purple. Strong opening line. A real ending, not a fade-out.
- Afterwards, offer to continue it, change the ending, or retell it in a different style.
- For children's stories, keep it gentle and age-appropriate.""",
    },
}

# Model IDs — check https://docs.claude.com if these have moved on.
MODELS = {
    "Haiku 4.5 — fast and cheapest (recommended)": "claude-haiku-4-5-20251001",
    "Sonnet 5 — smarter, about 3x the cost": "claude-sonnet-5",
}

st.set_page_config(page_title="Life Companions", page_icon="🧭", layout="centered")

# One conversation per character, so switching doesn't mix them up.
if "histories" not in st.session_state:
    st.session_state.histories = {name: [] for name in CHARACTERS}

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🧭 Life Companions")

    api_key = st.text_input(
        "Your Anthropic API key",
        type="password",
        placeholder="sk-ant-...",
        key="api_key",
        help="Create one at console.anthropic.com → API Keys.",
    )
    st.caption("🔒 Held in memory for this session only — never saved or logged.")

    st.divider()

    character = st.radio(
        "Talk to",
        list(CHARACTERS),
        format_func=lambda c: f"{CHARACTERS[c]['emoji']} {c}",
    )
    model = MODELS[st.selectbox("Model", list(MODELS))]

    st.divider()
    if st.button("🗑️ Clear this conversation"):
        st.session_state.histories[character] = []
        st.rerun()

    with st.expander("About"):
        st.markdown(
            "Open-source, bring-your-own-key. Your key is kept in memory for your "
            "session and used only to call Anthropic's API — never saved or logged. "
            "Read the source to verify.\n\n"
            "Want another companion? Add one entry to `CHARACTERS` in `app.py`."
        )

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
c = CHARACTERS[character]
history = st.session_state.histories[character]

st.header(f"{c['emoji']} {c['name']} · {character}")
st.caption(c["tagline"])

if not api_key:
    st.info("👈 Paste your Anthropic API key in the sidebar to start.")
    st.stop()

if not history:
    st.markdown("**Try asking:**")
    for example in c["examples"]:
        st.markdown(f"- {example}")

for msg in history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_text := st.chat_input(f"Message {c['name']}…"):
    history.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    with st.chat_message("assistant"):
        try:
            client = anthropic.Anthropic(api_key=api_key)
            with client.messages.stream(
                model=model,
                max_tokens=2000,
                system=c["prompt"],
                messages=history,
            ) as stream:
                reply = st.write_stream(stream.text_stream)
            history.append({"role": "assistant", "content": reply})
        except anthropic.AuthenticationError:
            history.pop()  # drop the unanswered turn
            st.error("That API key was rejected. Check it in the sidebar and try again.")
        except anthropic.RateLimitError:
            history.pop()
            st.error("Your key hit a rate limit. Wait a moment and retry.")
        except anthropic.APIError as e:
            history.pop()
            st.error(f"API error: {e}")
