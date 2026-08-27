# 11:00 IST slot — week of 27 Aug 2026

## The shape

The 5-item roundup we shipped on 26 Aug is a **weekly** format, not a daily one.
"5 things AI did this week" cannot run seven days running without repeating
itself, and the sweep says we could not feed it anyway.

So the daily 11:00 post is **one topic, 7 slides, 2–3 of them video** — which is
what @evolving.ai's non-roundup carousels do. The roundup gets one slot a week.

## Where footage comes from

Sourcing a clip per item is the expensive half of this format. There are two
routes, and which one a topic uses is decided by the topic:

| Route | Use for | Cost | Supply |
|---|---|---|---|
| **Self-recorded** (`scripts/record_screen.py`) | tools, repos, licences, star history | free, instant | unlimited |
| **Found footage** (`scripts/discover_reels.py`) | news, robots, launches, demos | needs crediting | **8 clips left** |

The 21-day sweep across six handles returned **13 clips**, five of them spent on
26 Aug. @evolving.ai was effectively the only productive source; @aivalleyai,
@theaiadvantage and @coderss_world contributed nothing usable. Found footage is
rationed to the weekly roundup for that reason.

## The week

| Date | Topic | Video slides | Route |
|---|---|---|---|
| Thu 27 | Chinese open models beating the paid ones | ollama repo, DeepSeek-V3 stars, star-history | self |
| Fri 28 | Run a real model on your own laptop, free | ollama repo, llama.cpp repo | self |
| Sat 29 | The repo that quietly hit 202K stars | n8n repo, n8n star-history chart | self |
| Sun 30 | Free AI tools you can legally bill for | LICENSE files: MIT vs CC-BY-NC | self |
| Mon 31 | Chinese open video models you can actually run | HF model pages, demo output | self + found |
| Tue 1 Sep | What the humanoid games actually proved | Games footage | found |
| Wed 2 Sep | **Weekly roundup #2** | 5 news items | found |

## Verified numbers (26 Aug 2026, GitHub API)

Re-check before each post — these move daily.

| Repo | Stars | Licence |
|---|---|---|
| n8n-io/n8n | 202,475 | Sustainable Use (NOT open source — say so) |
| significant-gravitas/AutoGPT | 186,878 | MIT |
| ollama/ollama | 179,473 | MIT |
| f/awesome-chatgpt-prompts | 167,926 | CC0 |
| AUTOMATIC1111/stable-diffusion-webui | 164,669 | AGPL-3.0 |
| huggingface/transformers | 164,455 | Apache-2.0 |
| open-webui/open-webui | 149,964 | BSD-3 |
| langchain-ai/langchain | 145,033 | MIT |
| comfyanonymous/ComfyUI | 130,056 | GPL-3.0 |
| ggml-org/llama.cpp | 125,713 | MIT |
| deepseek-ai/DeepSeek-V3 | 104,417 | MIT |
| vllm-project/vllm | 90,100 | Apache-2.0 |
| QwenLM/Qwen3 | 27,557 | Apache-2.0 |
| MoonshotAI/Kimi-K2 | 11,104 | Modified MIT |
| zai-org/GLM-4.5 | 4,415 | Apache-2.0 |

## Corrections applied to already-queued posts

- **30 Aug** claimed a repo went *9K → 210K stars*. No repo is at 210K. n8n is
  the one that fits the arc at **202,475**. Retitled to "quietly hit 202K", and
  the licence point is now part of the post rather than a silent error — n8n is
  under the Sustainable Use Licence, so calling it open source would be wrong.
