# Frequently Asked Questions

### Can I run PUMA without Docker?

Yes. Install Python 3.11+, run a separate Ollama server, then
`pip install -e .` inside the cloned repository. See `CONTRIBUTING.md` for the
full development setup. The Docker path is recommended because it pins every
runtime dependency.

### Can I run PUMA without a GPU?

Yes. Small models (1.5–3 B parameters) run comfortably on the `cpu-lite`
profile, and 7 B models run on `cpu-standard` (slower but viable). See
[Models and Datasets](Models-And-Datasets) for the profile matrix.

### Which model gives the best results?

It depends on the scenario. For `triage_jira` on the Jira SR balanced 200 set,
`qwen2.5:7b` and `gemma3:9b` lead the indicative reference numbers, but the
gap closes once you account for energy per correct prediction. Run your own
sweep — that is what PUMA is for.

### How long does a benchmark take?

A 10-instance triage run takes about 90 seconds on CPU with a 3 B model, or
about 25 seconds on an entry GPU with the same model. A full 200-instance
sweep across six models on `gpu-mid` finishes in roughly 20 minutes.

### Why is reproducibility important?

Local LLM evaluation is noisy: small temperature changes, seed differences,
and even Ollama version drift can shift metrics meaningfully. PUMA pins
`seed=42`, `temperature=0`, and stores the full run specification so the same
input yields the same output. See [Architecture](Architecture) for the full
list of reproducibility guarantees.

### How do I contribute?

Read `CONTRIBUTING.md` in the repo root for the development workflow, coding
standards, and test expectations. New scenarios, prompting strategies, and
dataset readers are especially welcome.

### Where do I report bugs?

Open an issue at
[pumacp/puma/issues](https://github.com/pumacp/puma/issues). Include the
output of `puma preflight`, the command you ran, and the full traceback if
applicable.

### Can I publish results from a custom model?

Yes. Off-catalog models are accepted by PUMA Community but are flagged as
"experimental" in the submission metadata so other users know the model's
provenance hasn't been independently vetted.
