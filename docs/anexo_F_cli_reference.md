# Anexo F — Catálogo de comandos de la plataforma PUMA (referencia técnica)

Este documento es la fuente de verdad para los comandos CLI de PUMA.
Está estructurado en dos partes:

- **Sección A**: comandos implementados y operativos en la versión
  actual del repositorio (verificables con `puma <comando> --help`).
- **Sección B**: extensiones propuestas como diseño futuro. No están
  implementadas. Su documentación describe la intención de diseño
  para su eventual implementación.

La distinción está marcada explícitamente en cada subsección. La
versión completa del Anexo F (con extensiones propuestas detalladas)
está disponible en la memoria del TFG.

## Sección A — Comandos implementados

### A.1. Comandos preexistentes (v2.0.0 — v2.3.0)

`puma profile`, `puma version`, `puma list-models`, `puma list-scenarios`,
`puma run`, `puma compare`, `puma report`, `puma migrate`, `puma test`,
`puma --help`, `puma validate-baseline`.

Para detalle de cada uno, ver `puma <comando> --help`.

### A.2. Comandos añadidos en v2.4.0 (Sprint 7 — CLI completeness)

#### A.2.1. `puma prepare-datasets`

**Sintaxis:**
```
puma prepare-datasets [--dataset <id>] [--force-redownload] [--verify]
```

**Propósito:** Descarga, prepara y registra los datasets canónicos
del experimento (`jira_balanced_200`, `tawos_estimation`,
`prioritization_jira`). Wrapper de `scripts/prepare_datasets.py`.

**Flags:**
- `--dataset <id>`: prepara solo el dataset indicado.
- `--force-redownload`: fuerza re-descarga aunque ya esté presente.
- `--verify`: verifica hashes SHA-256 tras la preparación.

**Exit codes:**
- 0: preparación exitosa
- 1: fallo al descargar (red o fuente no accesible)
- 2: hash mismatch tras --verify

**Implementación:** importar lógica del script existente y exponer
via @app.command(). Refactorizar el script para que la lógica viva
en una función importable.

#### A.2.2. `puma wilcoxon`

**Sintaxis:**
```
puma wilcoxon <run_id_a> <run_id_b> [--metric <m>] [--alpha <α>] [--output <file>]
```

**Propósito:** Test Wilcoxon signed-rank pareado entre dos runs.
Wrapper de `scripts/wilcoxon_topmodels.py` adaptado para input via
argumentos en lugar de leer de stdin/config.

**Flags:**
- `--metric <m>`: métrica (`f1_macro`, `accuracy`, `ece`). Default: `f1_macro`.
- `--alpha <α>`: nivel de significancia. Default: `0.05`.
- `--output <file>`: archivo de salida con el reporte (Markdown).

**Salidas:**
- Estadística W, p-value bilateral, marcado de significancia
  (***/**/*/n.s.), tamaño de efecto `r = Z/sqrt(N)`.

**Exit codes:**
- 0: test ejecutado
- 1: runs no comparables o sin instancias pareadas
- 2: N < 10 (test no aplicable)

#### A.2.3. `puma bias-analysis`

**Sintaxis:**
```
puma bias-analysis [--models <list>] [--perturbations <list>] [--output <file>]
```

**Propósito:** Analiza los resultados de un sweep de perturbaciones
(generado con specs bias_*). Wrapper de `scripts/bias_analysis.py`.

**Flags:**
- `--models <list>`: subset de modelos a incluir (separados por comas).
- `--perturbations <list>`: subset de perturbaciones a analizar.
- `--output <file>`: archivo de salida. Default: `docs/results/bias_evaluation.md`.

**Salidas:**
- Tabla por (modelo × perturbación) con: acc_baseline, acc_perturbed,
  disparity, flip_rate, flip_to_correct, flip_to_incorrect.
- Comparación direccional male vs female.

**Exit codes:**
- 0: análisis exitoso
- 1: no hay runs perturbadas en la BD
- 2: perturbación solicitada no presente

#### A.2.4. `puma generate-plots`

**Sintaxis:**
```
puma generate-plots [--source <fuente>] [--output <dir>] [--format <fmt>]
```

**Propósito:** Genera gráficos consolidados a partir de runs en BD.
Wrapper de `scripts/generate_phase_b_plots.py`.

**Flags:**
- `--source <fuente>`: fuente de datos (`phase_b`, `bias_eval`,
  `multi_seed`). Default: `phase_b`.
- `--output <dir>`: directorio de salida. Default: `docs/results/figures/`.
- `--format <fmt>`: formato (`png` default, `pdf`, `svg`, `all`).

**Exit codes:**
- 0: gráficos generados
- 1: fuente sin datos en BD
- 2: error al guardar

#### A.2.5. `puma list-runs`

**Sintaxis:**
```
puma list-runs [--scenario <s>] [--model <m>] [--last-n <N>] [--since <fecha>] [--json]
```

**Propósito:** Lista runs registradas en BD con sus métricas principales.
Útil para auditoría e identificación de candidatos para análisis.

**Flags:**
- `--scenario <s>`: filtra por escenario.
- `--model <m>`: filtra por modelo.
- `--last-n <N>`: muestra solo las últimas N.
- `--since <fecha>`: filtra runs posteriores (ISO o relativo: `24h`, `7d`).
- `--json`: salida en JSON.

**Salidas:**
- Tabla Rich con: run_id, scenario, model_tag, strategy, N_instances,
  F1_macro (o MAE según escenario), parse_failure_rate, duration_s,
  started_at.

**Exit codes:**
- 0: listado exitoso
- 1: BD no accesible
- 2: filtros vacíos (informativo)

**Implementación:** SELECT contra `runs` JOIN `metrics`. Reutilizar
el data loader de `src/puma/dashboard/data.py` (`load_runs`).

#### A.2.6. `puma list-ollama-models`

**Sintaxis:**
```
puma list-ollama-models [--json]
```

**Propósito:** Lista modelos efectivamente descargados en el volumen
`ollama_models` (vs. modelos catalogados que muestra `puma list-models`).

**Flags:**
- `--json`: salida en JSON.

**Salidas:**
- Tabla con columnas: model_tag, ID Ollama, tamaño (GB), modificado.
- Total: N modelos descargados, X GB ocupados.

**Implementación:** subprocess sobre `docker exec puma_ollama ollama list`,
parsea la salida tabular de Ollama y la reformatea como Rich table.

**Exit codes:**
- 0: listado exitoso
- 1: Ollama no responde

## Sección B — Extensiones propuestas

Los siguientes comandos están documentados como propuesta de diseño
para gestión profesional completa de la plataforma. Su especificación
detallada (sintaxis, flags, exit codes) se encuentra en la versión
completa del Anexo F entregada con la memoria del TFG.

**Scripts auxiliares Bash propuestos:**
- `stop_puma.sh`, `restart_puma.sh`, `clean_puma.sh`, `status_puma.sh`,
  `logs_puma.sh`

**Comandos CLI propuestos:**
- Inspección: `list-datasets`, `check-version`
- Ejecución: `smoke-test`, `sweep-phase-b`, `sweep-bias`, `multi-seed`
- Dashboard: `dashboard-start/stop/status`
- Ollama: `pull-model`, `remove-model`, `verify-datasets`
- BD: `backup-db`, `restore-db`, `clean-db`, `export-results`
- Calidad: `lint`, `format`, `precommit`

Estas extensiones representan el espacio de diseño completo para
gestión profesional. Su no-implementación en la versión actual es
una decisión consciente de scope: priorizar comandos con alto valor
añadido y bajo coste de implementación frente a wrappers cosméticos
de herramientas estándar (`pre-commit run`, `docker compose down`).
