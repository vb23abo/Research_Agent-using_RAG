# Agent and Telegram

Runs a LangGraph flow that checks the question, retrieves passages, grades them, and rewrites the query when the passages do not fit. A question outside CS/AI/ML papers is refused. The Telegram bot can call the same flow, and it stays off unless a bot token is set.

<p align="center">
  <img src="../../static/agent_and_telegram.png" alt="Agent and Telegram" width="800">
</p>

Open `agentic_rag.ipynb`.
