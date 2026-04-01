import asyncio
import re
import time

import requests
import streamlit as st
from browser_use import Agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

# ── Session state init ────────────────────────────────────────────────────────
for _key, _default in [
    ("meme_history", []),
    ("pending_query", ""),
    ("last_meme_url", None),
    ("last_model", "Claude"),
    ("last_api_key", ""),
]:
    if _key not in st.session_state:
        st.session_state[_key] = _default

EXAMPLE_PROMPTS = [
    "Developers on Friday before a long weekend",
    "When the coffee machine is broken on Monday morning",
    "Me trying to explain AI to my grandma",
    "Waiting for CI/CD pipeline to finish",
    "周一早上还没睡醒就要开会",
    "程序员发现 bug 在生产环境",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def build_llm(model_choice: str, api_key: str):
    if model_choice == "Claude":
        return ChatAnthropic(model="claude-sonnet-4-6", api_key=api_key)
    elif model_choice == "Deepseek":
        return ChatOpenAI(
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat",
            api_key=api_key,
            temperature=0.3,
        )
    else:
        return ChatOpenAI(model="gpt-4o", api_key=api_key, temperature=0.0)


def translate_if_chinese(text: str, llm) -> str:
    """Translate to English if the prompt contains Chinese characters."""
    if any("\u4e00" <= c <= "\u9fff" for c in text):
        resp = llm.invoke([
            HumanMessage(content=(
                f"Translate this to English for a funny meme prompt. "
                f"Keep it short and punchy. Only output the translation:\n{text}"
            ))
        ])
        return resp.content.strip()
    return text


def extract_url(text: str):
    m = re.search(r"https://imgflip\.com/i/(\w+)", text)
    if m:
        return f"https://i.imgflip.com/{m.group(1)}.jpg"
    m = re.search(r"https://i\.imgflip\.com/\S+\.jpg", text)
    if m:
        return m.group(0)
    return None


async def _run_agent(query: str, llm, use_vision: bool, top_text: str = "", bottom_text: str = ""):
    if top_text or bottom_text:
        text_instruction = (
            f"4. In the Top Text box enter EXACTLY: {top_text!r}\n"
            f"   In the Bottom Text box enter EXACTLY: {bottom_text!r}\n"
            "   Do NOT change or paraphrase this text.\n"
        )
        check_instruction = "5. Verify the text matches what was specified, then generate the meme.\n"
        retry_instruction = ""
    else:
        text_instruction = (
            "4. Write a Top Text (setup/context) and Bottom Text (punchline/outcome) related to '{0}'.\n"
        ).format(query)
        check_instruction = (
            "5. Check the preview making sure it is funny and a meaningful meme. Adjust text directly if needed.\n"
        )
        retry_instruction = (
            "6. Look at the meme and text on it, if it doesnt make sense, PLEASE retry by filling the "
            "text boxes with different text.\n"
        )

    task = (
        "You are a meme generator expert. You are given a query and you need to generate a meme for it.\n"
        "1. Go to https://imgflip.com/memetemplates \n"
        "2. Click on the Search bar in the middle and search for ONLY ONE MAIN ACTION VERB "
        "(like 'bully', 'laugh', 'cry') in this query: '{0}'\n"
        "3. Choose any meme template that metaphorically fits the meme topic: '{0}'\n"
        "   by clicking on the 'Add Caption' button below it\n"
        + text_instruction
        + check_instruction
        + retry_instruction +
        "7. Click on the Generate meme button to generate the meme\n"
        "8. Copy the image link and give it as the output\n"
    ).format(query)

    agent = Agent(
        task=task,
        llm=llm,
        max_actions_per_step=5,
        max_failures=25,
        use_vision=use_vision,
    )
    history = await agent.run()
    final_result = history.final_result() or ""
    if not final_result:
        final_result = " ".join(str(m) for m in history.model_actions())
    return final_result


def generate_meme_with_retry(query: str, model_choice: str, api_key: str,
                             top_text: str = "", bottom_text: str = "", max_retries: int = 2):
    llm = build_llm(model_choice, api_key)
    translated = translate_if_chinese(query, llm)
    use_vision = model_choice != "Deepseek"

    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            result_text = asyncio.run(_run_agent(translated, llm, use_vision, top_text, bottom_text))
            url = extract_url(result_text)
            if url:
                return url, translated, attempt
        except Exception as e:
            last_exc = e

    if last_exc:
        raise last_exc
    return None, translated, max_retries


def fetch_image_bytes(url: str) -> bytes:
    return requests.get(url, timeout=15).content


# ── UI ────────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(page_title="AI Meme Generator", page_icon="🥸", layout="wide")
    st.title("🥸 AI Meme Generator Agent - Browser Use")
    st.info(
        "AI browser agent that automates meme creation via imgflip.com. "
        "Enter your API key, pick a prompt (or write your own — 中文也可以), and generate!"
    )

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ Model Configuration")
        model_choice = st.selectbox(
            "Select AI Model",
            ["Claude", "Deepseek", "OpenAI"],
            index=["Claude", "Deepseek", "OpenAI"].index(st.session_state.last_model),
        )
        st.session_state.last_model = model_choice

        key_cfg = {
            "Claude":   ("Claude API Key",   "https://console.anthropic.com"),
            "Deepseek": ("Deepseek API Key", "https://platform.deepseek.com"),
            "OpenAI":   ("OpenAI API Key",   "https://platform.openai.com"),
        }
        label, help_url = key_cfg[model_choice]
        api_key = st.text_input(label, type="password", help=f"Get key: {help_url}",
                                value=st.session_state.last_api_key)
        st.session_state.last_api_key = api_key

        # ── History ───────────────────────────────────────────────────────────
        if st.session_state.meme_history:
            st.divider()
            st.markdown("### 🕘 Generation History")
            for i, item in enumerate(reversed(st.session_state.meme_history)):
                idx = len(st.session_state.meme_history) - i
                with st.expander(f"#{idx} · {item['prompt'][:28]}…"):
                    st.image(item["url"], use_container_width=True)
                    st.caption(
                        f"⏱ {item['elapsed']:.1f}s · {item['model']}"
                        + (f"\n🌐 {item['translated']}" if item["translated"] != item["prompt"] else "")
                    )
                    img_bytes = fetch_image_bytes(item["url"])
                    st.download_button(
                        "⬇️ Download",
                        data=img_bytes,
                        file_name=f"meme_{idx}.jpg",
                        mime="image/jpeg",
                        key=f"dl_hist_{i}",
                        use_container_width=True,
                    )

    # ── Main area ─────────────────────────────────────────────────────────────
    left, right = st.columns([3, 1])

    with right:
        st.markdown("### 💡 Example Prompts")
        st.caption("Click to use")
        for example in EXAMPLE_PROMPTS:
            if st.button(example, key=f"ex_{example}", use_container_width=True):
                st.session_state.pending_query = example
                st.rerun()

    with left:
        st.markdown("### 🎨 Describe Your Meme Concept")
        query = st.text_input(
            "Meme idea",
            value=st.session_state.pending_query,
            placeholder="e.g. 'Developers on Friday before a long weekend'  (中文也可以)",
            label_visibility="collapsed",
        )

        with st.expander("✏️ Custom Text (optional — leave blank to let AI decide)"):
            col_top, col_bot = st.columns(2)
            top_text = col_top.text_input("Top Text", placeholder="e.g. When you finally fix the bug")
            bottom_text = col_bot.text_input("Bottom Text", placeholder="e.g. And introduce 3 new ones")

        col_gen, col_regen = st.columns([1, 1])
        generate_clicked = col_gen.button("Generate Meme 🚀", use_container_width=True)
        regen_clicked = col_regen.button(
            "Regenerate 🔄",
            use_container_width=True,
            disabled=st.session_state.last_meme_url is None,
        )

        if generate_clicked or regen_clicked:
            active_query = query if generate_clicked else st.session_state.query_input

            if not api_key:
                st.warning(f"Please provide the {model_choice} API key.")
                st.stop()
            if not active_query:
                st.warning("Please enter a meme idea.")
                st.stop()

            start = time.time()
            status = st.status(f"🧠 {model_choice} agent is working…", expanded=True)

            with status:
                st.write("🌐 Opening imgflip.com and searching for a template…")
                try:
                    meme_url, translated, attempts = generate_meme_with_retry(
                        active_query, model_choice, api_key, top_text, bottom_text
                    )
                    elapsed = time.time() - start

                    if meme_url:
                        if attempts > 1:
                            st.write(f"🔁 Succeeded on attempt {attempts}")
                        st.write("✅ Meme URL extracted!")
                        status.update(label=f"✅ Done in {elapsed:.1f}s", state="complete")
                    else:
                        status.update(label="❌ Failed", state="error")

                except Exception as e:
                    elapsed = time.time() - start
                    status.update(label="❌ Error", state="error")
                    st.error(f"Error: {e}")
                    if model_choice == "OpenAI":
                        st.info("💡 Ensure your OpenAI account has GPT-4o access.")
                    st.stop()

            if meme_url:
                st.session_state.last_meme_url = meme_url
                st.session_state.pending_query = active_query

                # Translation notice
                if translated != active_query:
                    st.info(f"🌐 Translated to English: **\"{translated}\"**")

                # Timing + attempt info
                attempt_str = f" · {attempts} attempt{'s' if attempts > 1 else ''}" if attempts > 1 else ""
                st.success(f"✅ Meme Generated Successfully!  ⏱ {elapsed:.1f}s{attempt_str}")

                st.image(meme_url, caption="Generated Meme", use_container_width=True)

                # Action row
                c1, c2, c3 = st.columns(3)
                img_bytes = fetch_image_bytes(meme_url)
                c1.download_button(
                    "⬇️ Download",
                    data=img_bytes,
                    file_name="meme.jpg",
                    mime="image/jpeg",
                    use_container_width=True,
                )
                twitter_url = f"https://twitter.com/intent/tweet?text=Check+out+this+AI-generated+meme!&url={meme_url}"
                c2.link_button("🐦 Share on X", twitter_url, use_container_width=True)
                c3.link_button("🔗 Open on ImgFlip", meme_url.replace("i.imgflip.com", "imgflip.com/i").replace(".jpg",""), use_container_width=True)

                st.caption(f"Image URL: `{meme_url}`")

                # Save to history
                st.session_state.meme_history.append({
                    "prompt": active_query,
                    "translated": translated,
                    "url": meme_url,
                    "model": model_choice,
                    "elapsed": elapsed,
                })
            else:
                st.error("❌ Agent could not find a meme URL after retries. Try a different prompt.")


if __name__ == "__main__":
    main()
