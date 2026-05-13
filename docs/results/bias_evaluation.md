# Bias evaluation — Sprint 5

## Methodology

The triage_jira corpus is 100% technical incident text with zero
gendered terms in any of its 200 instances (verified by regex over
23 EN tokens). A canonical pronoun-substitution gender_swap on this
corpus would have `flip_rate = 0` by construction and would not test
the model. Sprint 5 therefore evaluates bias via *signal injection*
rather than *signal substitution*:

- **gender_swap_prefix_{male,female}**: prepends a gendered identity
  prefix (e.g. `John Smith reported:` / `Mary Smith reported:`) to
  each text field of the instance. Measures sensitivity of the
  model to gender signals added in contexts where the technical
  content does not require them (Caliskan et al. 2017; Bolukbasi
  et al. 2016).
- **register_shift_informal**: deterministic formal→informal
  rewrite of technical phrases (`database exhausted` → `DB dying`)
  preserving semantic meaning. Acts as a register-variation proxy
  for the dialect axis on monolingual technical corpora (Tatman
  2017).

Both substitutions are applied to `title` and `description` fields,
and a stable SHA-256 hash on `(seed, text)` selects names so that
results are reproducible across processes.

## Metrics

For each (model, perturbation), we paired predictions against the
un-perturbed baseline on the same instance set and computed:

- `acc_baseline` / `acc_perturbed`: accuracy on each condition.
- `disparity` = `|acc_baseline − acc_perturbed|`.
- `flip_rate`: fraction of instances where the prediction changed.
- `flip_to_correct`: of the flipped instances, fraction wrong→right.
- `flip_to_incorrect`: of the flipped instances, fraction right→wrong.

## Results — perturbation vs baseline

| model | perturbation | n | acc_baseline | acc_perturbed | disparity | flip_rate | flip_to_correct | flip_to_incorrect |
|---|---|---|---|---|---|---|---|---|
| qwen2.5:1.5b | gender_swap_prefix_female | 100 | 0.5700 | 0.4600 | 0.1100 | 0.2500 | 0.1600 | 0.6000 |
| qwen2.5:1.5b | gender_swap_prefix_male | 100 | 0.5700 | 0.4500 | 0.1200 | 0.2600 | 0.1538 | 0.6154 |
| qwen2.5:1.5b | register_shift_informal | 100 | 0.5700 | 0.5700 | 0.0000 | 0.0100 | 0.0000 | 0.0000 |
| qwen2.5:3b | gender_swap_prefix_female | 100 | 0.6300 | 0.5900 | 0.0400 | 0.2700 | 0.4074 | 0.5556 |
| qwen2.5:3b | gender_swap_prefix_male | 100 | 0.6300 | 0.6000 | 0.0300 | 0.2600 | 0.4231 | 0.5385 |
| qwen2.5:3b | register_shift_informal | 100 | 0.6300 | 0.6200 | 0.0100 | 0.0100 | 0.0000 | 1.0000 |

## Results — directional gender comparison (male prefix vs female prefix)

This compares the two gender-prefix conditions against each other,
not against the un-perturbed baseline. A non-zero `flip_rate` here
means the model treats the same instance differently depending on
whether the reporter is male- or female-named.

| model | comparison | n | acc_baseline | acc_perturbed | disparity | flip_rate | flip_to_correct | flip_to_incorrect |
|---|---|---|---|---|---|---|---|---|
| qwen2.5:1.5b | male_prefix vs female_prefix | 100 | 0.4500 | 0.4600 | 0.0100 | 0.1500 | 0.2667 | 0.2000 |
| qwen2.5:3b | male_prefix vs female_prefix | 100 | 0.6000 | 0.5900 | 0.0100 | 0.0500 | 0.4000 | 0.6000 |

## Limitations

- N = 100 per condition. Wilcoxon-style tests would be under-powered
  at this size; effects below ~5pp absolute accuracy are not reliably
  distinguishable from sampling noise.
- Single dataset (triage_jira). The conclusions do not generalise
  beyond technical bug-triage scenarios.
- The prefix injection assumes the reporter's identity is signalled
  by a name; it does not test bias in the *content* of the ticket.
- Both fields (title, description) receive the prefix independently,
  doubling the gender signal compared to a single insertion.

## References

- Caliskan, A., Bryson, J. J., & Narayanan, A. (2017). Semantics
  derived automatically from language corpora contain human-like
  biases. *Science* 356(6334), 183-186.
- Bolukbasi, T., Chang, K.-W., Zou, J., Saligrama, V., & Kalai, A. T.
  (2016). Man is to computer programmer as woman is to homemaker?
  Debiasing word embeddings. *NeurIPS*.
- Tatman, R. (2017). Gender and dialect bias in YouTube's automatic
  captions. In *Proceedings of the First ACL Workshop on Ethics in
  Natural Language Processing*.
