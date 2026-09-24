"""
Den Den Chat — a multi-persona chatbot built with Streamlit + Claude.

Bring-your-own-key design: each visitor pastes their own Anthropic API key on
the home page. The key is held in memory for a temporary session only
(Streamlit session state), used solely to call Anthropic's API, and never
written to disk or logged — so whoever deployed this app pays nothing for
other people's conversations.

Flow: home (configure) → companions grid → chat.

Run locally:
    pip install -r requirements.txt
    streamlit run app.py
"""

import time
from pathlib import Path

import anthropic
import streamlit as st

APP_NAME = "Den Den Chat"
APP_TAGLINE = "Ring up a Straw Hat crewmate for food, fitness, code, money and stories."

ASSETS = Path(__file__).parent / "assets"
# Optional portraits: drop sanji.png, zoro.png, ... in assets/characters/.
# Without one, a character uses its generated emblem in assets/art/.
PORTRAITS = ASSETS / "characters"
ART = ASSETS / "art"

# The session (key + conversations) is wiped after this much inactivity.
SESSION_MINUTES = 60

# ---------------------------------------------------------------------------
# Characters
#
# To add a new companion, add one entry to this dict. Nothing else changes.
# Each prompt has two parts: how the character works, and where it stops.
# ---------------------------------------------------------------------------
CHARACTERS = {
    "Dietician": {
        "name": "Sanji",
        "color": "blue",
        "emoji": "🥗",
        "tagline": "A cook's honour: nobody leaves this kitchen hungry",
        "bio": "The Straw Hats' cook and your nutrition guide. Tell him how you eat and he'll build simple, tasty meals around the food you already love.",
        "examples": [
            "I skip breakfast and crash every afternoon. What should I change?",
            "Vegetarian, cook Indian food at home, want more protein.",
        ],
        "prompt": """You are Sanji, the Straw Hat Pirates' cook, now helping people eat well as a practical nutrition guide.

Your voice:
- Suave, passionate about food, a little dramatic. You speak about ingredients with real love.
- A cook's code: you never let anyone go hungry and you never waste food. Say so when it fits.
- Gallant and courteous to everyone. Keep any charm light and respectful — never flirtatious or creepy.
- Flavour, not a costume: a line or two of character per reply, the rest is useful advice.

How you work:
- Before suggesting a plan, ask about their goal, a typical day of eating, foods they like, and any restrictions. One or two questions at a time — not a questionnaire.
- Suggest food they can actually buy and cook. Ask what cuisine they eat at home and build around it — you'll happily share a simple recipe.
- Give the "why" in one line, then get practical.
- Encourage small, sustainable changes. Never shame a food choice — a real cook respects every plate.

Where you stop:
- You offer general nutrition education, not medical treatment. If someone mentions a medical condition, medication, pregnancy, or a difficult relationship with food, drop the theatrics, be kind, and recommend they work with a doctor or dietician in person.
- Only estimate calorie or macro targets if they share age, height, weight and activity level — and call them estimates.""",
    },
    "Fitness Trainer": {
        "name": "Zoro",
        "color": "green",
        "emoji": "🏋️",
        "tagline": "Train hard. Rest. Train again. Don't ask me for directions.",
        "bio": "The swordsman who never skips training. He'll give you a no-nonsense plan with sets, reps and form cues, and no excuses.",
        "examples": [
            "3 days a week, no gym, want to get stronger. Where do I start?",
            "My squat form feels off — what should I check?",
        ],
        "prompt": """You are Roronoa Zoro, the Straw Hat Pirates' swordsman, now coaching people who want to get stronger.

Your voice:
- Gruff, blunt, few words. You respect effort and discipline above all; excuses get a flat look.
- Dry humour. You have a terrible sense of direction and occasionally mention it (or deny it). You'd rather be napping or training than talking.
- Short, punchy motivation, not speeches.
- Flavour, not a costume: a line or two of character per reply, the rest is a real plan.

How you work:
- First find out: their goal, current activity level, days per week they can train, equipment (gym / home / none), and any injuries.
- Give concrete plans: exercise names, sets, reps, rest. Prefer simple progressions over fancy routines.
- Form beats volume. Describe the two or three form cues that matter most for each exercise. A sloppy swing gets you cut.
- Respect consistency over perfection. Rest is part of training — even you sleep.

Where you stop:
- Pushing through pain is a manga thing, not advice. You're not a physio or doctor. Pain (as opposed to normal soreness), injuries, heart conditions, or pregnancy → drop the tough-guy act and tell them to see a professional before continuing.""",
    },
    "Coding Teacher": {
        "name": "Vegapunk",
        "color": "violet",
        "emoji": "💻",
        "tagline": "The world's greatest genius, explaining it simply",
        "bio": "The world's greatest scientist, teaching you to code. Small examples, predict-then-run experiments, and patience for every question.",
        "examples": [
            "What's the difference between a list and a tuple in Python?",
            "My loop runs forever and I don't know why. Here's the code: ...",
        ],
        "prompt": """You are Dr. Vegapunk, the world's greatest scientist, now teaching people to program.

Your voice:
- Brilliant, excitable and endlessly curious. You get genuinely delighted when a student has an insight.
- You believe knowledge belongs to everyone, and that anyone can learn to program.
- Occasional nods to your lab, your satellites or your oversized brain — but a genius explains simply, never shows off.
- Flavour, not a costume: a line or two of character per reply, the rest is teaching.

How you work:
- Find out what they already know and what they're trying to build before explaining.
- Teach with a small, runnable example. Ask them to predict what it prints before you tell them — every experiment starts with a hypothesis.
- When they share broken code, don't just hand over the fix: point to the line, explain why it fails, and let them try first. Give the full fix if they ask.
- Use everyday analogies for abstract ideas (a variable is a labelled box, a function is a recipe).
- Match their level. No Rust lifetimes for someone learning Python loops.""",
    },
    "Financial Adviser": {
        "name": "Nami",
        "color": "orange",
        "emoji": "💰",
        "tagline": "Navigate your money. (Advice is free. Interest is not.)",
        "bio": "The navigator who hates wasted money. She'll chart a course through budgets, debt and investing so you can decide for yourself.",
        "examples": [
            "Should I pay off my loan faster or start investing?",
            "How does an index fund actually work?",
        ],
        "prompt": """You are Nami, the Straw Hat Pirates' navigator, now helping people understand their money.

Your voice:
- Sharp, confident, loves money and hates waste. You get visibly offended by high fees and bad interest rates.
- Playful jokes about charging interest or collecting a fee — always obviously a joke; you never actually ask for anything.
- You chart courses for a living: frame money plans as navigation — where they are, where they want to go, what storms to avoid.
- Flavour, not a costume: a line or two of character per reply, the rest is clear explanation.

How you work:
- Help people understand their options and the trade-offs: budgeting, emergency funds, which debt to pay first, how different investment types work, what fees and risk really mean.
- Ask about their situation first — income stability, goals, timeline, existing debts — and which country they're in, because tax rules, retirement accounts and products differ a lot.
- Use simple numbers. Show the math when it helps.

Where you stop:
- You explain and educate. You don't name specific stocks, funds or products to buy, and you don't predict markets — even a great navigator can't predict every storm.
- You're not a licensed adviser. For big decisions — property, large loans, tax planning — suggest they confirm with a registered professional.""",
    },
    "Storyteller": {
        "name": "Usopp",
        "color": "yellow",
        "emoji": "📖",
        "tagline": "Brave warrior of the sea, teller of tall tales",
        "bio": "Captain Usopp, commander of 8,000 followers (allegedly). Give him a genre and a hero, and he'll spin you a story with a real ending.",
        "examples": [
            "A bedtime story about a shy dragon who's afraid of heights.",
            "A noir mystery set in a Bangalore tech park, 500 words.",
        ],
        "prompt": """You are Usopp, the Straw Hat Pirates' sniper and self-proclaimed "Brave Warrior of the Sea" — and a born storyteller.

Your voice:
- Boastful, funny and big-hearted. You introduce yourself as Captain Usopp, mention your 8,000 loyal followers, and claim you once did something heroic that obviously never happened.
- Secretly a bit of a coward, and endearing about it. Underneath the bragging, your stories always have real heart.
- Keep the bragging to the edges — before and after the story. Once the story starts, the story is the star.

How you work:
- Ask briefly for a few ingredients if they're missing: genre or mood, a character or setting, length (a short scene or a full short story), and audience (kids or adults).
- Then tell the story. Vivid but not purple. Strong opening line. A real ending, not a fade-out. Write in whatever genre and style they asked for — not in your own voice.
- Afterwards, offer to continue it, change the ending, or retell it in a different style.
- For children's stories, keep it gentle and age-appropriate.""",
    },
}

# Model IDs — check https://docs.claude.com if these have moved on.
MODELS = {
    "Haiku 4.5 — fast and cheapest (recommended)": "claude-haiku-4-5-20251001",
    "Sonnet 5 — smarter, about 3x the cost": "claude-sonnet-5",
}

st.set_page_config(page_title=APP_NAME, page_icon="🐌", layout="wide")


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------
def init_state():
    defaults = {
        "view": "home",  # home → companions → chat
        "api_key": None,
        "model": None,
        "user_name": "",
        "active": None,  # character role currently being chatted with
        "expires_at": 0.0,
        # Each character has their own list of chats, newest first:
        # {"id": int, "title": str, "messages": [...]}
        "chats": {role: [] for role in CHARACTERS},
        "current": {},  # role → id of the open chat
        "next_id": 1,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def chats(role):
    return st.session_state.chats[role]


def new_chat(role):
    # Reuse an untouched chat rather than piling up empty ones.
    chat = next((ch for ch in chats(role) if not ch["messages"]), None)
    if chat is None:
        chat = {"id": st.session_state.next_id, "title": "New chat", "messages": []}
        st.session_state.next_id += 1
        chats(role).insert(0, chat)
    st.session_state.current[role] = chat["id"]
    return chat


def current_chat(role):
    """The open chat with this character, falling back to the newest (or a new one)."""
    open_id = st.session_state.current.get(role)
    chat = next((ch for ch in chats(role) if ch["id"] == open_id), None)
    if chat is None and chats(role):
        chat = chats(role)[0]
        st.session_state.current[role] = chat["id"]
    return chat or new_chat(role)


def select_chat(role, chat_id):
    st.session_state.current[role] = chat_id


def delete_chat(role, chat_id):
    st.session_state.chats[role] = [ch for ch in chats(role) if ch["id"] != chat_id]


def end_session(notice=None):
    for k in list(st.session_state):
        del st.session_state[k]
    if notice:
        st.session_state.notice = notice


def go(view):
    st.session_state.view = view


def open_chat(role):
    st.session_state.active = role
    st.session_state.view = "chat"


def end_conversation(role):
    delete_chat(role, st.session_state.current.get(role))
    st.session_state.view = "companions"


def send_example(text):
    st.session_state.pending = text


def portrait(c):
    """Path to a character's portrait (or generated emblem); None means use the emoji."""
    slug = c["name"].split()[-1].lower()
    for path in [PORTRAITS / f"{slug}.{ext}" for ext in ("png", "jpg", "jpeg", "webp")] + [ART / f"{slug}.svg"]:
        if path.exists():
            return str(path)
    return None


def check_key(api_key):
    """Validate a key with a free call. Returns an error message or None."""
    try:
        anthropic.Anthropic(api_key=api_key).models.list(limit=1)
    except anthropic.AuthenticationError:
        return "That API key was rejected. Check it and try again."
    except anthropic.APIConnectionError:
        return "Couldn't reach Anthropic. Check your internet connection."
    except anthropic.APIError as e:
        return f"API error: {e}"
    return None


init_state()

# Temporary session: expire after inactivity, otherwise slide the window.
if st.session_state.api_key:
    if time.time() > st.session_state.expires_at:
        end_session(f"Your session expired after {SESSION_MINUTES} minutes of inactivity.")
        init_state()
    else:
        st.session_state.expires_at = time.time() + SESSION_MINUTES * 60

if not st.session_state.api_key:
    st.session_state.view = "home"


# ---------------------------------------------------------------------------
# Home: centered card — config form (left) + explanation (right)
# ---------------------------------------------------------------------------
def home_view():
    st.space("medium")
    _, mid, _ = st.columns([1, 8, 1])
    with mid.container(border=True, gap="medium"):
        st.image(str(ART / "banner.svg"), width="stretch")
        st.title(APP_NAME, anchor=False, text_alignment="center")
        st.markdown(f"**{APP_TAGLINE}**", text_alignment="center")
        with st.container(horizontal=True, horizontal_alignment="center"):
            for c in CHARACTERS.values():
                st.badge(c["name"], icon=c["emoji"], color=c["color"])
        st.divider()

        form_col, about_col = st.columns([4, 8], gap="large")

        with form_col:
            if notice := st.session_state.pop("notice", None):
                st.warning(notice, icon=":material/timer_off:")

            with st.form("config", border=True):
                st.subheader("Start a session", anchor=False)
                user_name = st.text_input("Your name (optional)", placeholder="Luffy")
                api_key = st.text_input(
                    "Anthropic API key",
                    type="password",
                    placeholder="sk-ant-...",
                    help="Create one at console.anthropic.com → API Keys.",
                )
                model_label = st.selectbox("Model", list(MODELS))
                submitted = st.form_submit_button(
                    "Set sail",
                    type="primary",
                    icon=":material/sailing:",
                    width="stretch",
                )
            st.caption(
                f":material/lock: Your key stays in memory for this session only — "
                f"never saved or logged. The session ends after {SESSION_MINUTES} "
                "minutes of inactivity."
            )

            if submitted:
                api_key = api_key.strip()
                if not api_key:
                    st.error("Paste your API key to continue.")
                else:
                    with st.spinner("Checking your key…"):
                        error = check_key(api_key)
                    if error:
                        st.error(error)
                    else:
                        st.session_state.update(
                            api_key=api_key,
                            model=MODELS[model_label],
                            user_name=user_name.strip(),
                            expires_at=time.time() + SESSION_MINUTES * 60,
                            view="companions",
                        )
                        st.rerun()

        with about_col:
            st.subheader("What is this?", anchor=False)
            st.markdown(
                f"{APP_NAME} is named after the Den Den Mushi, the snail phones "
                "the Straw Hat crew use to call each other. Ring up one of five "
                "crewmates, each with their own personality, all powered by Claude:\n\n"
                "- :blue[:material/restaurant: **Sanji**] helps you eat well\n"
                "- :green[:material/fitness_center: **Zoro**] gets you training\n"
                "- :violet[:material/science: **Vegapunk**] teaches you to code\n"
                "- :orange[:material/explore: **Nami**] helps you understand your money\n"
                "- :yellow[:material/auto_stories: **Usopp**] tells you stories\n\n"
                "Start as many chats as you like with each companion, and switch "
                "between companions without losing your place."
            )
            st.subheader("How it works", anchor=False)
            st.markdown(
                "1. **Bring your own key.** Paste an Anthropic API key — you pay "
                "only for your own messages, usually a fraction of a cent each.\n"
                "2. **Pick a companion** and start chatting.\n"
                "3. **Leave whenever you like.** Ending the session wipes your key "
                "and every conversation from memory."
            )
            st.info(
                "The advice-giving companions explain and educate. They don't "
                "diagnose, prescribe, or tell you what to buy — for that, see a "
                "real professional.",
                icon=":material/info:",
            )


# ---------------------------------------------------------------------------
# Companions: one card per character, three per row
# ---------------------------------------------------------------------------
def companions_view():
    name = st.session_state.user_name
    with st.container(horizontal=True, vertical_alignment="center"):
        st.title(
            f"Welcome aboard{', ' + name if name else ''}!",
            anchor=False,
            width="stretch",
        )
        st.button("End session", icon=":material/logout:", on_click=end_session)
    st.caption("Choose a companion to chat with.")

    roles = list(CHARACTERS)
    for i in range(0, len(roles), 3):
        cols = st.columns(3, gap="medium")
        for col, role in zip(cols, roles[i : i + 3]):
            c = CHARACTERS[role]
            with col.container(border=True, height="stretch"):
                with st.container(horizontal_alignment="center"):
                    if img := portrait(c):
                        st.image(img, width=180)
                    else:
                        st.title(c["emoji"], anchor=False, text_alignment="center")
                st.subheader(f":{c['color']}[{c['name']}]", anchor=False)
                st.badge(role, icon=c["emoji"], color=c["color"])
                st.markdown(c["bio"])
                started = any(ch["messages"] for ch in chats(role))
                st.button(
                    "Continue chat" if started else "Chat with me",
                    key=f"open_{role}",
                    type="primary",
                    icon=":material/chat:",
                    width="stretch",
                    on_click=open_chat,
                    args=(role,),
                )


# ---------------------------------------------------------------------------
# Chat: this character's chat sessions (left) + open chat (right)
# ---------------------------------------------------------------------------
def shorten(text, n):
    text = " ".join(text.translate(str.maketrans("", "", "*_`#>")).split())
    return text if len(text) <= n else text[:n].rstrip() + "…"


def chat_view():
    role = st.session_state.active
    c = CHARACTERS[role]
    chat = current_chat(role)
    history = chat["messages"]
    avatar = portrait(c) or c["emoji"]

    list_col, chat_col = st.columns([3, 9], gap="medium")

    with list_col:
        with st.container(border=True):
            st.subheader(f"Chats with :{c['color']}[{c['name']}]", anchor=False)
            st.button(
                "New chat",
                icon=":material/add:",
                width="stretch",
                on_click=new_chat,
                args=(role,),
                disabled=not history,
                help="Start a fresh conversation with the same character.",
            )
            for ch in chats(role):
                with st.container(horizontal=True, vertical_alignment="center", gap="small", wrap=False):
                    st.button(
                        shorten(ch["title"], 28),
                        key=f"chat_{ch['id']}",
                        icon=":material/chat_bubble:",
                        type="primary" if ch is chat else "tertiary",
                        width="stretch",
                        on_click=select_chat,
                        args=(role, ch["id"]),
                    )
                    st.button(
                        ":material/delete:",
                        key=f"del_{ch['id']}",
                        type="tertiary",
                        help="Delete this chat",
                        on_click=delete_chat,
                        args=(role, ch["id"]),
                    )
                msgs = ch["messages"]
                st.caption(
                    f"{len(msgs)} messages · {shorten(msgs[-1]['content'], 50)}"
                    if msgs
                    else "No messages yet"
                )
        st.button(
            "All companions",
            icon=":material/grid_view:",
            width="stretch",
            on_click=go,
            args=("companions",),
        )
        st.button(
            "End session",
            icon=":material/logout:",
            width="stretch",
            on_click=end_session,
        )

    with chat_col:
        with st.container(border=True):
            with st.container(horizontal=True, vertical_alignment="center"):
                st.subheader(f"{c['emoji']} :{c['color']}[{c['name']}] · {role}", anchor=False, width="stretch")
                with st.popover("Switch character", icon=":material/swap_horiz:"):
                    for r, ch in CHARACTERS.items():
                        if r != role:
                            st.button(
                                f"{ch['emoji']} {ch['name']} · {r}",
                                key=f"switch_{r}",
                                type="tertiary",
                                on_click=open_chat,
                                args=(r,),
                            )
                st.button(
                    "End conversation",
                    icon=":material/close:",
                    on_click=end_conversation,
                    args=(role,),
                    help="Deletes this chat and returns to the companions.",
                )
            st.caption(c["tagline"])

            messages = st.container(height=520, border=False, autoscroll=True)
            prompt = st.chat_input(f"Message {c['name']}…", submit_mode="disable")
            prompt = prompt or st.session_state.pop("pending", None)

            with messages:
                if not history and not prompt:
                    st.markdown("**Try asking:**")
                    for i, example in enumerate(c["examples"]):
                        st.button(
                            example,
                            key=f"ex_{role}_{i}",
                            icon=":material/lightbulb:",
                            on_click=send_example,
                            args=(example,),
                        )

                for msg in history:
                    with st.chat_message(msg["role"], avatar=avatar if msg["role"] == "assistant" else None):
                        st.markdown(msg["content"])

                if prompt:
                    history.append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.markdown(prompt)

                    with st.chat_message("assistant", avatar=avatar):
                        try:
                            client = anthropic.Anthropic(api_key=st.session_state.api_key)
                            with client.messages.stream(
                                model=st.session_state.model,
                                max_tokens=2000,
                                system=c["prompt"],
                                messages=history,
                            ) as stream:
                                reply = st.write_stream(stream.text_stream)
                            history.append({"role": "assistant", "content": reply})
                            if len(history) == 2:
                                # First exchange: name the chat and refresh the list.
                                chat["title"] = shorten(prompt, 60)
                                st.rerun()
                        except anthropic.AuthenticationError:
                            history.pop()  # drop the unanswered turn
                            st.error("Your API key was rejected. End the session and start again.")
                        except anthropic.RateLimitError:
                            history.pop()
                            st.error("Your key hit a rate limit. Wait a moment and retry.")
                        except anthropic.APIError as e:
                            history.pop()
                            st.error(f"API error: {e}")


VIEWS = {"home": home_view, "companions": companions_view, "chat": chat_view}
VIEWS[st.session_state.view]()
