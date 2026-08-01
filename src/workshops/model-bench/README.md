# Workshop 1 · The model bench

The foundation workshop, and the only standalone one — workshops 2–8 build one
evolving assistant, while this builds the tool you measure it with.

`before/` is your scaffold (TODOs); `after/` is the working reference.
Brief: [`WORKSHOP-MODEL-BENCH.md`](WORKSHOP-MODEL-BENCH.md).

```bash
cd after && make check              # the reference passes, offline, in a second
cd before && make check             # your job: make this pass

make test-integration               # the same bench against real Ollama
python -m bench.cli --providers local,gpt-mini
python -m bench.cli --providers local --json > bench-$(date +%F).json
```

The fast tier never touches the network: candidates are dicts, the runner is a fake
with scripted replies, and the clock is injected. The integration tier needs
`ollama serve` and `ollama pull qwen3.5:8b`; add `OPENAI_API_KEY` only if you want
the hosted candidates too.
