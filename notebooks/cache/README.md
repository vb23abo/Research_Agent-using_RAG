# Cache and tracing

Stores repeated answers in Redis. Langfuse records the embed, search, and generate steps when real keys are set. Without keys, the answer is still returned and tracing is skipped.

<p align="center">
  <img src="../../static/cache_and_tracing.png" alt="Cache and tracing" width="800">
</p>

Open `cache.ipynb`.
