"""
Owl Picks - black & gold college football predictions.
Run with:  streamlit run app.py   (reads predictions_2026.csv from this folder)
"""
import html
import re
import pandas as pd
import streamlit as st

MODEL = "qwen3:4b"   # match the name shown by `ollama list`
GOLD, BLACK = "#FDBB30", "#0B0B0B"

st.set_page_config(page_title="Owl Picks", page_icon="🦉", layout="wide")
st.markdown(f"""
<style>
.stApp {{ background: {BLACK}; color: #FFFFFF; }}
h1, h2, h3 {{ color: {GOLD} !important; }}
[data-testid="stSidebar"] {{ background: #1A1A1A; }}
.card {{ border: 2px solid {GOLD}; border-radius: 10px; padding: 12px 16px; margin-bottom: 6px; }}
.bar {{ background: #333; border-radius: 6px; height: 14px; overflow: hidden; }}
.fill {{ background: {GOLD}; height: 100%; }}
.answer {{ background: #1A1A1A; border-left: 4px solid {GOLD}; padding: 10px 14px; border-radius: 6px; margin-bottom: 14px; }}
</style>
""", unsafe_allow_html=True)

# ---- data
games = pd.read_csv("predictions_2026.csv")
games["date"] = pd.to_datetime(games["date"], format="mixed", errors="coerce")


def ask_analyst(row):
    import ollama
    facts = (
        f"{row['away']} at {row['home']}. Model gives {row['home']} a {row['home_win_prob']:.0%} chance to win.\n"
        f"{row['home']}: point margin last 5 games {row['home_point_margin_l5']:+.1f}, win % {row['home_won_std']:.0%}.\n"
        f"{row['away']}: point margin last 5 games {row['away_point_margin_l5']:+.1f}, win % {row['away_won_std']:.0%}."
    )
    prompt = ("/no_think\nYou are a college football analyst. Using ONLY these facts, explain the pick "
              "in 3 sentences. Don't invent stats or players.\n\n" + facts)
    messages = [{"role": "user", "content": prompt}]
    try:
        resp = ollama.chat(model=MODEL, messages=messages, think=False, options={"num_predict": 500})
    except TypeError:   # older ollama package that doesn't know `think`
        resp = ollama.chat(model=MODEL, messages=messages, options={"num_predict": 500})
    reply = resp["message"]["content"]
    reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.S)   # finished thinking block
    reply = re.sub(r"<think>.*", "", reply, flags=re.S).strip()    # thinking that got cut off
    return html.escape(reply) or "The analyst ran out of time before answering. Click Why? again."


# ---- sidebar
st.sidebar.title("🦉 Owl Picks")
ksu_only = st.sidebar.checkbox("Kennesaw State games only")
week = st.sidebar.selectbox("Week", sorted(games["week"].unique()))

if ksu_only:
    view = games[(games["home"] == "Kennesaw State") | (games["away"] == "Kennesaw State")]
else:
    view = games[games["week"] == week]

# ---- page
st.title("Owl Picks")
st.caption("Black & gold college football predictions · XGBoost picks · Qwen commentary")

if view.empty:
    st.info("No upcoming games here.")

for i, row in view.iterrows():
    p = row["home_win_prob"]
    pick = row["home"] if p >= 0.5 else row["away"]
    pct = max(p, 1 - p)
    when = row["date"].strftime("%a %b %d") if pd.notna(row["date"]) else "TBD"

    st.markdown(f"""
<div class="card">
  <small>{when}</small>
  <h3 style="margin:4px 0">{row['away']} @ {row['home']}</h3>
  Pick: <b style="color:{GOLD}">{pick}</b> ({pct:.0%})
  <div class="bar"><div class="fill" style="width:{p * 100:.0f}%"></div></div>
  <small>{row['away']} {1 - p:.0%} · {row['home']} {p:.0%}</small>
</div>
""", unsafe_allow_html=True)

    key = f"answer_{i}"
    if st.button("🎙️ Why?", key=f"why_{i}"):
        with st.spinner("🦉 Breaking down the film... (can take up to a minute)"):
            try:
                st.session_state[key] = ask_analyst(row)
            except Exception as e:
                st.session_state[key] = f"⚠️ Couldn't reach Ollama: {e}"
    if key in st.session_state:   # keep the answer on screen after it arrives
        st.markdown(f'<div class="answer">{st.session_state[key]}</div>', unsafe_allow_html=True)