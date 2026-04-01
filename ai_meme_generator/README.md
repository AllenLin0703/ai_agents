# 🥸 AI Meme Generator Agent

An AI-powered browser automation agent that generates memes from text prompts. The agent autonomously navigates [imgflip.com](https://imgflip.com), selects a fitting meme template, fills in captions, and returns the generated image.

## Demo

> Describe your idea → AI browses imgflip.com → Meme generated ✅

## Features

- 🤖 **Browser automation** — AI agent controls a real browser to interact with imgflip.com
- 🌐 **Chinese input support** — Automatically translates Chinese prompts to English
- ✏️ **Custom text** — Optionally specify your own Top Text and Bottom Text
- 💡 **Example prompts** — One-click example ideas to get started
- 🔁 **Auto retry** — Retries up to 2 times on failure
- ⏱ **Generation timer** — Shows how long each meme took to generate
- 📥 **Download** — Save the generated meme as a JPG
- 🐦 **Share on X** — One-click share to Twitter/X
- 🕘 **History** — View all memes generated in the current session

## Supported Models

| Model | Provider | Notes |
|-------|----------|-------|
| Claude (claude-sonnet-4-6) | Anthropic | Best quality, vision enabled |
| GPT-4o | OpenAI | Vision enabled |
| Deepseek v3 | Deepseek | No vision |

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/AllenLin0703/ai_agents.git
cd ai_agents
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Set your API key

Create a `.env` file in the project root:

```
# Use whichever model you prefer
ANTHROPIC_API_KEY=your_key_here
# or
OPENAI_API_KEY=your_key_here
# or
DEEPSEEK_API_KEY=your_key_here
```

### 5. Run the app

```bash
streamlit run ai_meme_generator_agent.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

## Dependencies

```
streamlit
browser-use==0.1.26
playwright==1.49.1
langchain-openai
langchain-anthropic
```

## How It Works

1. User enters a meme idea (English or Chinese)
2. If Chinese is detected, the LLM translates it to English
3. A `browser-use` Agent is launched with the task instructions
4. The agent opens imgflip.com, searches for a template, fills in captions
5. The generated meme URL is extracted and displayed in the UI

## Project Structure

```
.
├── ai_meme_generator_agent.py   # Main Streamlit app
├── requirements.txt
├── .env                         # API keys (not committed)
└── .gitignore
```

## License

MIT
