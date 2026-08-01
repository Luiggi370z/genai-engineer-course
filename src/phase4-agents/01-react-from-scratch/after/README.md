# 4.1 ReAct from scratch — reference

The whole loop in ~30 lines, with a hard step cap + wall-clock deadline. The model brain is injected so tests are deterministic and offline; wire it to your Phase-1 client for the live version (try it against qwen3.5:9b and watch tool-arg reliability).
