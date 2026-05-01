PUMA — Instrucciones de implementación para Claude Code
Documento operativo. Dirigido a Claude Code trabajando sobre el repositorio pumacp/puma. Objetivo. Evolucionar PUMA desde su estado MVP actual (PEC2: qwen2.5:3b zero-shot, F1=0.5867, MAE=1.89 SP) hacia una plataforma de benchmarking multi-dimensional local, reproducible y adaptativa a hardware, descrita en INDEX.md. Restricciones. PUMA es un proyecto independiente: ni el código, ni los commits, ni los nombres de módulos, ni la documentación mencionarán "HELM", "Stanford", "CRFM" ni "PUMA-HELM". El proyecto se llama PUMA y conserva su identidad. Las metodologías inspiradoras se describen como "evaluación multi-dimensional de LLMs" sin atribución externa.


0. Principios operativos (de obligada lectura antes de empezar)
Toda la documentación y comentarios de código producida debe de estar en inglés. No se deben de incluir comentarios, nombres de archivos, documentación, nombres de variables, clases o cualquier otra información, en un idioma diferente al inglés.
Se debe de partir de la versión actual de código, eliminando todos aquellos archivos o códigos o carpetas que no sean necesarios para la versión final descrita a continuación. 
Se debe de seguir el modelo de "https://github.com/stanford-crfm/helm" como ejemplo para implementar las diferentes funcionalidades, pero siempre sin nombrar HELM en ningún lugar de PUMA.
El repositorio original del Proyecto PUMA es "https://github.com/pumacp/puma". Contiene la última versión publicada que debe de servir de ejemplo inicial a partir del cual se debe de comenzar a implementar las nuevas funcionalidades que se describen en este documento y en index.md.
No se deben de hacer referencia a las diferentes fases de implementación descritas a continuación, ni en el código, ni en los posibles commits, ni en la documentación generada. Las diferentes fases indicadas a continuación unicamente servirán como guía interna para la implementación de las nuevas funcionalidades.
Spec-first. Antes de escribir código nuevo, Claude Code redacta la spec correspondiente en /specs/ y la hace aprobar (aunque sea por sí mismo) mediante un checklist explícito. Las specs son Markdown con frontmatter YAML.
Iteración incremental con gates. Cada fase termina con un gate verificable (tests en verde + smoke test + check manual). No se pasa a la siguiente fase sin el gate.
Conservación agresiva. No se elimina código existente que funcione. Se refactoriza a los nuevos módulos preservando funcionalidad. Cada eliminación requiere justificación en el commit.
Determinismo por defecto. Toda función de inferencia acepta seed y temperature explícitos. Los tests de integración fallan si dos ejecuciones con mismos parámetros producen resultados distintos (salvo en tests específicos de varianza).
Logging estructurado. Todo evento relevante (inicio de run, llamada a Ollama, cálculo de métrica, error) se registra en JSON line en logs/puma.jsonl con timestamp, level, module, event, payload.
Dos escenarios de HW soportados simultáneamente. Todo código debe funcionar en cpu-standard (16 GB RAM, sin GPU) y en gpu-entry+ (16 GB RAM + GPU con ≥6 GB VRAM). Los tests de integración se ejecutan en ambos modos vía fixtures parametrizados.
Commits atómicos y convencionales. Formato Conventional Commits (feat:, fix:, refactor:, test:, docs:). Un commit = un cambio lógico. Los commits referencian el ID de la tarea (F1.1, F2.3…).
Tests antes que features en módulos críticos (runtime, metrics, perturbations, preflight). Para UI y CLI, tests tras implementación.


1. Estado inicial que Claude Code debe asumir
Al comenzar, Claude Code ejecuta en el repo:

git status

git log --oneline -20

ls -la

cat README.md 2>/dev/null || true

find . -maxdepth 3 -name "*.py" | head -30

find . -maxdepth 3 -name "*.yaml" -o -name "*.yml" | head -20

cat docker-compose.yml 2>/dev/null || true

Produce en docs/baseline_inventory.md un inventario del estado actual: módulos existentes, scripts presentes, dependencias en requirements.txt/pyproject.toml, cobertura de tests si existe. Este documento sirve de referencia para el refactor conservador posterior.

Si el repositorio no tiene pyproject.toml, lo crea con layout src (src/puma/). Si ya usa otro layout, lo conserva y adapta los imports.


2. Arquitectura objetivo (contrato con INDEX.md)
Claude Code lee INDEX.md como fuente única de verdad del alcance funcional. Todo PR o implementación debe poder justificarse con una sección concreta de INDEX.md. Si algo que se quiere implementar no está en INDEX.md, primero se actualiza INDEX.md con una propuesta explícita.

Módulos a crear/consolidar bajo src/puma/:

preflight/      — autodetección HW, selección de perfil, verificación provisioning

datasets/       — jira_sr, tawos; descarga, verificación, carga en DataFrame. TAWOS se encuentra descomprimida en la carpeta "db/" con el nombre "TAWOS.sql". Se utiliza la versión de "https://github.com/SOLAR-group/TAWOS"

runtime/        — cliente Ollama con logprobs, retries, timeouts, caché

scenarios/      — triage, estimation, prioritization (+ targeted evaluations)

adaptation/     — zero/one/few-shot, CoT, RCOIF, anchoring, self-consistency

perturbations/  — typos, case, truncation, reorder, tech-noise

metrics/        — accuracy, calibration (ECE), robustness, fairness, efficiency,

                  stability, sustainability

sustainability/ — wrapper CodeCarbon, métricas derivadas (gCO2/F1-point)

storage/        — SQLAlchemy models, migraciones, caché de inferencias

dashboard/      — Streamlit app

cli.py          — Typer entrypoint


3. Plan de implementación — 7 fases con gates
Fase 0 — Fundamentos y reestructuración
Objetivo. Tener un repo con la estructura final, INDEX.md como fuente de verdad, tests corriendo, y preservando toda la funcionalidad MVP.

Tareas:

F0.1 Crear estructura src/puma/<módulos>/ con __init__.py y docstrings por módulo.
F0.2 Migrar pyproject.toml. Dependencias mínimas: typer, httpx, pydantic, pyyaml, jinja2, pandas, numpy, scikit-learn, scipy, sqlalchemy, psutil, codecarbon, streamlit, langdetect, pytest, pytest-cov, ruff, mypy.
F0.3 Migrar requirements.txt → pyproject.toml manteniendo versiones actuales. Añadir requirements-dev.txt con pytest, ruff, mypy, pre-commit.
F0.4 Crear INDEX.md con el contenido provisto en este paquete. Eliminar README.md antiguo desactualizado y generar uno nuevo mínimo que apunte a INDEX.md y ofrezca un quickstart en 3 comandos.
F0.5 Mover código MVP existente a los nuevos módulos preservando APIs públicas. Cada movimiento es un commit refactor: con test de no-regresión.
F0.6 Configurar ruff (line-length 100, target py311) y mypy (strict en módulos metrics, runtime, preflight; gradual en el resto).
F0.7 Crear suite pytest mínima: tests/unit/, tests/integration/, tests/smoke/. Fixture compartida ollama_client_mock para tests que no requieren Ollama real.
F0.8 CI local vía Makefile: make lint, make test, make smoke.

Gate F0 (no se pasa a F1 sin esto):

pytest tests/ pasa en verde (incluso si solo hay 10 tests básicos).
ruff check src/ tests/ sin errores.
El comando MVP original (evaluación triaje qwen2.5:3b) sigue ejecutándose y produce F1 ≈ 0.5867 ± 0.01.
INDEX.md en main.


Fase 1 — Preflight y perfiles HW
Objetivo. start_puma.sh detecta HW y selecciona perfil automáticamente. PUMA puede levantarse en CPU-only o con GPU sin intervención manual.

Tareas:

F1.1 Implementar puma.preflight.detect:

OS, arquitectura (platform)
CPU: modelo, núcleos físicos/lógicos, frecuencia (psutil.cpu_freq, /proc/cpuinfo)
RAM total y disponible (psutil.virtual_memory)
Disco libre en . (shutil.disk_usage)
GPU: intenta en orden nvidia-smi --query-gpu=name,memory.total --format=csv,noheader, luego rocm-smi, luego system_profiler SPDisplaysDataType en macOS (Metal). Si ninguno responde: gpu=None.
Ollama: ollama --version y curl http://localhost:11434/api/version si está arriba.
Retorna un dataclass SystemCapabilities.

F1.2 Implementar puma.preflight.profile:

Lee config/profiles.yaml (5 perfiles: cpu-lite, cpu-standard, gpu-entry, gpu-mid, gpu-high con umbrales).
Función select_profile(caps: SystemCapabilities) -> Profile aplica reglas simples:
Si GPU con ≥24 GB VRAM → gpu-high
Si GPU con 12-23 GB VRAM → gpu-mid
Si GPU con 6-11 GB VRAM → gpu-entry
Si no GPU y RAM ≥16 GB → cpu-standard
Si no GPU y RAM 8-15 GB → cpu-lite
Si no GPU y RAM <8 GB → error con mensaje claro.
Permite sobrescritura manual con --profile <name>.

F1.3 Implementar puma.preflight.provisioning:

Verifica espacio en disco suficiente para el perfil (suma tamaños GGUF de modelos del perfil + 5 GB margen).
Verifica Docker + docker-compose instalados.
Verifica GPU accesible desde Docker (si aplica) ejecutando docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi.
Reporta lista de problemas con severidad (error, warning).

F1.4 Crear config/profiles.yaml con los umbrales y listas de modelos por perfil exactamente como en INDEX.md §2.1.

F1.5 Crear config/models_catalog.yaml: para cada modelo, ollama_tag, params_b, gguf_size_gb, context_window, logprobs_supported, profiles_compatible, notes.

F1.6 Reescribir start_puma.sh:

#!/usr/bin/env bash

set -euo pipefail

# Parse flags, invoca `python -m puma.preflight` que:

#  1. detecta HW, escribe config/runtime_profile.yaml

#  2. imprime resumen legible

#  3. si --profile != auto, valida compatibilidad y sobrescribe

# Luego levanta docker-compose con el overlay adecuado.

F1.7 Comando CLI puma preflight que solo ejecuta detección y muestra el perfil recomendado sin levantar servicios.

F1.8 Tests:

Unit: mocks de subprocess para simular presencia/ausencia de GPU, distintos valores de RAM.
Integration: ejecuta puma preflight y verifica escritura correcta de runtime_profile.yaml.

Gate F1:

En una máquina sin GPU, ./start_puma.sh --smoke-only selecciona cpu-standard (si 16 GB) o cpu-lite (si 8 GB) y levanta Ollama correctamente.
En una máquina con GPU NVIDIA (≥6 GB VRAM), selecciona gpu-entry o superior y Ollama usa la GPU (verificable con docker exec puma_ollama nvidia-smi).
puma preflight imprime un informe de diagnóstico completo.


Fase 2 — Runtime Ollama y datasets
Objetivo. Cliente Ollama robusto con soporte completo de logprobs. Descarga funcional de Jira SR y TAWOS.

Tareas:

F2.1 Implementar puma.runtime.OllamaClient:

Basado en httpx.AsyncClient con pool y timeouts configurables.
Métodos: generate(model, prompt, *, temperature, seed, max_tokens, logprobs=False, top_logprobs=0, format=None) y chat(...) análogo.
Retorna dataclass GenerationResult con: response, logprobs (lista de TokenLogprob), timings (total_duration, load_duration, eval_count, eval_duration), raw.
Retries con backoff exponencial para errores 5xx y timeouts.
Validación de compatibilidad logprobs con el modelo (consulta al catálogo).

F2.2 Caché de inferencia (puma.runtime.cache):

Backend SQLite en data/cache/inferences.db.
Key: sha256(model + prompt + temperature + seed + logprobs_flag + format_schema).
Value: JSON de GenerationResult.
Decorator @cached_inference aplicable al método generate.
CLI: puma cache stats, puma cache clear.

F2.3 Implementar puma.datasets.jira_sr:

Descarga desde Zenodo (https://zenodo.org/record/5901893/files/<file>).
Verifica SHA256.
Descomprime si ZIP.
Carga en pandas.DataFrame con esquema documentado: issue_key, project_key, summary, description, priority, issue_type, created, resolved.
Función sample(n, seed, stratify_by='priority') para submuestras reproducibles.

F2.4 Implementar puma.datasets.tawos:

Descarga desde figshare resolviendo la API: https://api.figshare.com/v2/articles/21308124/files.
Coge el primer archivo ZIP (download_url), lo descarga a db/tawos.zip, descomprime en db/tawos/.
Genera db/tawos.csv unificado con columnas: story_id, project_key, title, description, story_points, created.
Si la descarga automática falla: imprime instrucciones claras para descarga manual y ubica en db/tawos.zip.

F2.5 Verificación de datasets (puma datasets verify):

Comprueba presencia de db/jira_sr.csv y db/tawos.csv.
Verifica hashes SHA256 vs. config/datasets_manifest.yaml.
Reporta número de filas, clases/distribución, rango de fechas.

F2.6 Tests:

Unit: OllamaClient con servidor mock (respx).
Integration: ejecución contra Ollama real con qwen2.5:1.5b (modelo pequeño para CI). Verifica que los logprobs se devuelven y parsean correctamente.
Integration: descarga de datasets con fixture que simula respuesta figshare/zenodo.

Gate F2:

puma datasets verify produce output positivo en una máquina limpia tras start_puma.sh.
Un test end-to-end envía un prompt a qwen2.5:1.5b con logprobs=true, top_logprobs=5 y recibe estructura parseada correctamente.
La caché acelera una segunda ejecución idéntica (medible: segunda ejecución <10 ms vs. primera).


Fase 3 — Escenarios, adaptación y perturbaciones
Objetivo. Cualquier combinación escenario × modelo × estrategia × perturbación se expresa como YAML y se ejecuta correctamente.

Tareas:

F3.1 Implementar puma.scenarios.base.Scenario (clase abstracta):

name, dataset, task_type (classification/regression/ranking), labels, sample(n, seed), parse_response(raw), gold_label(instance).

F3.2 Implementar escenarios core:

TriageJira (classification, priorities: Blocker/Critical/Major/Minor/Trivial)
EstimationTawos (regression, story points: 1/2/3/5/8/13/21/34/55/89)
PrioritizationJira (ranking pairwise)

F3.3 Definir YAML de escenarios en specs/scenarios/*.yaml con metadatos completos (descripción, métrica primaria, tamaño de muestra sugerido, referencias).

F3.4 Implementar puma.adaptation.Strategy (clase abstracta):

build_prompt(scenario, instance, examples=None) -> str
parse(raw_response) -> Prediction

F3.5 Implementar las 9 estrategias del INDEX.md §7 como subclases, cada una con su plantilla Jinja en specs/prompts/<scenario>/<strategy>.jinja.

F3.6 Selección de ejemplos para few-shot (puma.adaptation.examples):

Estratificada por clase.
Determinista con semilla.
Configurable (k, balance, ordering).

F3.7 Implementar puma.perturbations:

typos(text, rate=0.05, seed) — sustitución de caracteres con homólogos visuales.
case_change(text, mode='upper'|'lower'|'random', seed).
truncate(text, keep=0.5, from_='end'|'middle').
reorder_fields(instance, order) para instancias multi-campo.
tech_noise(text, terms=['TODO','FIXME','deprecated'], insertions=3, seed).

F3.8 Tests por estrategia y perturbación: snapshot tests de prompts generados, comprobaciones de idempotencia con seed fija.

Gate F3:

Una run-spec de ejemplo (specs/runs/smoke_triage.yaml) que combine triage_jira × qwen2.5:3b × few-shot-3 × typos_5pct se ejecuta con éxito sobre 20 instancias y produce predicciones parseadas.


Fase 4 — Motor de métricas multi-dimensional
Objetivo. Las siete familias de métricas descritas en INDEX.md §4 calculables y testeadas.

Tareas:

F4.1 puma.metrics.accuracy:

Classification: F1-macro, F1-weighted, accuracy, confusion matrix, per-class precision/recall.
Regression: MAE, MdAE, RMSE, MRE (Magnitude of Relative Error), MAE por bins de story points.
Ranking: NDCG@k, Kendall-τ, MRR.

F4.2 puma.metrics.calibration:

Extracción de confianza por clase desde logprobs: para cada instancia, suma de probabilidades (softmax estable sobre top_logprobs) de los tokens que componen la etiqueta.
Para modelos sin logprobs o cuando falle la extracción: fallback a confianza auto-declarada vía prompt estructurado JSON.
Funciones: expected_calibration_error(confs, corrects, n_bins=10), maximum_calibration_error, brier_score, reliability_diagram(path).

F4.3 puma.metrics.robustness:

robustness_score(metric_orig, metric_perturbed).
consistency_rate(preds_orig, preds_perturbed).
Reporte por tipo de perturbación.

F4.4 puma.metrics.fairness:

Input: predicciones + atributo de subgrupo.
Métricas: disparity(group), worst_group, fairness_gap, equalized_odds_gap (si binario).
Soporte para subgrupos: project_key, language_detected (con langdetect), length_bucket (short/medium/long).

F4.5 puma.metrics.efficiency:

Parser de total_duration, eval_duration, eval_count de Ollama.
Percentiles p50/p95/p99 de latencia.
Throughput (instancias/min).
Memoria pico: muestreo a 1 Hz de psutil.virtual_memory().used y nvidia-smi --query-gpu=memory.used durante la ejecución (hilo separado).

F4.6 puma.metrics.stability:

Acepta N ejecuciones con seeds distintas.
Calcula media, stddev, coeficiente de variación de cada métrica.

F4.7 puma.sustainability.codecarbon_wrapper:

Decorator @track_emissions(project_name, output_dir) que envuelve cualquier función.
Extrae kWh, gCO2eq, duración, energía por componente.
Métricas derivadas: gco2_per_f1_point(emissions, f1), gco2_per_mae_unit(emissions, mae).

F4.8 Tests numéricos: para cada métrica, comparación con referencia scikit-learn/numpy. ECE verificada contra ejemplos publicados (p. ej. el ejemplo de Guo et al. 2017 si se reconstruye).

Gate F4:

Informe automático de una run muestra las 7 dimensiones calculadas y coherentes.
ECE ≤ 0.15 en qwen2.5:3b en triaje (sanity check del cálculo, no del modelo).
CodeCarbon registra emisiones > 0 y coherentes con la duración del run.


Fase 5 — Orquestador, storage y run-specs
Objetivo. Ejecución declarativa completa desde YAML con persistencia total.

Tareas:

F5.1 Modelos SQLAlchemy en puma.storage.models según esquema de INDEX.md §8.1.

F5.2 Migraciones con Alembic. Script puma db migrate en la CLI.

F5.3 puma.orchestrator.Runner:

Input: RunSpec (Pydantic model).
Orquesta: carga dataset → muestra → para cada modelo × estrategia × perturbación → genera prompt → llama Ollama → parsea → persiste en predictions.
Calcula métricas al finalizar.
Envuelve todo en codecarbon.EmissionsTracker.
Progreso en consola con rich.

F5.4 Parser y validador de RunSpec:

Pydantic model con validaciones cruzadas (el perfil permite los modelos declarados; la estrategia es compatible con el escenario; las perturbaciones existen).

F5.5 puma run <spec.yaml>:

Calcula spec_hash, crea registro run.
Ejecuta el Runner.
Genera results/<run_id>/ con todos los artefactos (ver INDEX.md §8.3).

F5.6 puma compare:

Query SQL sobre metrics para dos+ run_ids.
Tabla markdown + JSON con las diferencias significativas.

F5.7 Tests: run-spec de 10 instancias × 1 modelo × 1 estrategia termina correctamente y deja DB + results consistentes.

Gate F5:

La run-spec completa de ejemplo specs/runs/triage_multi_model.yaml (3 modelos × 2 estrategias × 2 perturbaciones × 100 instancias) ejecuta end-to-end en <2h en cpu-standard.
Todos los artefactos de INDEX.md §8.3 se generan correctamente.
Una segunda ejecución de la misma spec con caché habilitada termina en <5 min.


Fase 6 — Dashboard Streamlit y Grafana opcional
Objetivo. UI de exploración completa según INDEX.md §9.

Tareas:

F6.1 App Streamlit puma.dashboard.app con las 7 vistas:

Overview (cards de runs)
Model comparison (heatmap interactivo)
Reliability (diagramas de fiabilidad)
Robustness (barplot degradación)
Fairness (fairness gaps)
Sustainability frontier (scatter eficiencia vs. calidad)
Instance drill-down

F6.2 Componentes reutilizables en puma.dashboard.components: metric_card, comparison_table, reliability_plot, pareto_scatter.

F6.3 Lectura solo-lectura de data/puma.db. Sin escrituras desde el dashboard.

F6.4 Filtros globales: perfil HW, rango de fechas, modelos seleccionados.

F6.5 Exportar figuras como PNG/SVG desde cada vista.

F6.6 Docker: servicio puma_dashboard en docker-compose.yml.

F6.7 Servicio opcional puma_grafana:

Overlay docker-compose.observability.yml.
Datasource frser-sqlite-datasource.
Dashboards provisionados en docker/grafana/dashboards/: throughput en tiempo real, uso de recursos, emisiones acumuladas por día.
Activación: ./start_puma.sh --observability.

F6.8 Smoke tests Streamlit con streamlit.testing.v1.AppTest.

Gate F6:

El dashboard arranca con puma dashboard y muestra al menos una run en la vista Overview.
Las 7 vistas renderizan sin errores con datos de una run completa.
La vista Instance drill-down permite inspeccionar el prompt crudo y los logprobs de cualquier predicción.


Fase 7 — Informes, documentación y cierre
Objetivo. Proyecto entregable, documentado y con informes auto-generables.

Tareas:

F7.1 puma report <run_id>:

Genera results/<run_id>/report.md con: resumen ejecutivo, tabla de métricas, figuras principales, tabla comparativa si hay ≥2 modelos, sección de emisiones.
Convertible a PDF opcional vía Pandoc si está instalado.

F7.2 Documentación extendida en docs/:

architecture.md — diagrama detallado de flujo.
metrics_reference.md — fórmula de cada métrica con referencia.
scenarios_reference.md — ficha por escenario.
adding_models.md — guía para añadir un modelo al catálogo.
adding_scenarios.md — guía para añadir un escenario.
troubleshooting.md — problemas frecuentes y su solución.

F7.3 CONTRIBUTING.md con convenciones de código, commits y PRs.

F7.4 Actualización final de README.md: badges, quickstart de 3 comandos, link a INDEX.md y a docs/.

F7.5 GitHub Actions:

Workflow lint-and-test.yml: ruff + mypy + pytest unit en cada PR.
Workflow smoke.yml: levanta Ollama con un modelo pequeño y ejecuta smoke test.
Workflow release.yml: al hacer tag v*, empaqueta y publica a GH Releases.

F7.6 Tag v2.0.0 al terminar.

Gate F7 (cierre del TFG técnico):

./start_puma.sh en máquina limpia completa el provisioning en <20 min con cpu-standard.
Un smoke test completo (triaje + estimación en 50 instancias con 2 modelos) termina en <30 min en cpu-standard.
puma report genera un informe legible y completo.
La documentación cubre los 6 módulos principales.


4. Convenciones técnicas detalladas
4.1. Cliente Ollama — contrato
@dataclass(frozen=True)

class TokenLogprob:

    token: str

    logprob: float

    top_logprobs: list["TokenLogprob"] = field(default_factory=list)

@dataclass(frozen=True)

class GenerationResult:

    model: str

    response: str

    logprobs: list[TokenLogprob]

    total_duration_ns: int

    load_duration_ns: int

    prompt_eval_count: int

    eval_count: int

    eval_duration_ns: int

    raw: dict  # Respuesta completa de Ollama

class OllamaClient:

    def __init__(self, base_url: str = "http://localhost:11434",

                 timeout_s: float = 120.0, retries: int = 3): ...

    async def generate(self, model: str, prompt: str, *,

                       temperature: float = 0.0, seed: int = 42,

                       max_tokens: int = 256,

                       logprobs: bool = False, top_logprobs: int = 0,

                       format: dict | str | None = None,

                       system: str | None = None) -> GenerationResult: ...

El cliente siempre pasa options: {"temperature", "seed", "num_predict"} en el payload a /api/generate. Si logprobs=True, añade logprobs: true, top_logprobs: N en el nivel raíz del payload.
4.2. Extracción de confianza para ECE
Para clasificación multi-clase con tokens de etiqueta conocidos:

def class_confidence_from_logprobs(

    logprobs: list[TokenLogprob],

    label_tokens: dict[str, list[str]],  # "Critical" -> ["Critical", " Critical", "critical", ...]

) -> dict[str, float]:

    """

    Aplica softmax estable sobre top_logprobs del primer token generado

    y suma las probabilidades de los tokens que representan cada etiqueta.

    Retorna un dict {label: prob} normalizado.

    """

    first = logprobs[0]

    candidates = [(first.token, first.logprob)] + [

        (tl.token, tl.logprob) for tl in first.top_logprobs

    ]

    max_lp = max(lp for _, lp in candidates)

    exps = [(tok, math.exp(lp - max_lp)) for tok, lp in candidates]

    total = sum(e for _, e in exps)

    probs = {tok: e / total for tok, e in exps}

    result = {}

    for label, tokens in label_tokens.items():

        result[label] = sum(probs.get(t, 0.0) for t in tokens)

    # Normalización final

    s = sum(result.values())

    return {k: v / s for k, v in result.items()} if s > 0 else result
4.3. CodeCarbon wrapper
Usar siempre EmissionsTracker(project_name=f"puma_{run_id}", output_dir=f"results/{run_id}/", log_level="error", save_to_file=True, tracking_mode="process"). El wrapper debe capturar excepciones y garantizar stop() aunque el run falle.
4.4. Formato de run-spec (Pydantic)
class RunSpec(BaseModel):

    id: str

    description: str

    scenario: Literal["triage_jira", "estimation_tawos", "prioritization_jira"]

    sample_size: int = Field(gt=0, le=10000)

    models: list[str]  # Validated against models_catalog.yaml

    adaptation: AdaptationConfig

    inference: InferenceConfig

    perturbations: list[str] = []

    metrics: list[str]

    sustainability: SustainabilityConfig = SustainabilityConfig()

    repeat: int = 1

    profile_required: str | None = None  # si None, usa el activo
4.5. Logging estructurado
Usar structlog con renderizador JSON. Eventos mínimos a emitir:

run.start       {run_id, spec_hash, profile}

run.end         {run_id, status, duration_s, n_predictions}

model.pull      {model, size_gb, duration_s}

inference.call  {model, prompt_hash, cached, duration_ms}

inference.error {model, error_type, message}

metric.computed {run_id, metric_name, scope, value}

emission.tick   {kwh, g_co2, since_start_s}
4.6. Tests — distribución objetivo
Tipo
Localización
Umbral cobertura
Notas
Unit
tests/unit/
≥80 % en metrics, runtime, preflight
Mock de Ollama
Integration
tests/integration/
≥60 %
Requieren Ollama con qwen2.5:1.5b
Smoke
tests/smoke/
—
End-to-end de un escenario mínimo



5. Gestión de riesgos — qué hacer si algo falla
Riesgo
Detección
Mitigación
TAWOS inaccesible
puma datasets verify falla en TAWOS
Fallback a instrucciones manuales; ZIP colocado manualmente en db/tawos.zip es detectado y descomprimido.
Modelo no disponible en Ollama
ollama pull retorna error
Catálogo marca available: false temporalmente; run-spec salta ese modelo con warning.
Logprobs no soportados por Ollama instalado
Primera llamada con logprobs=true devuelve campo vacío
Detectar en preflight la versión de Ollama (≥0.12.11 requerida); si menor, advertir y usar fallback de confianza auto-declarada.
GPU detectada pero Docker no la ve
docker run --gpus all falla
Warning claro con link a nvidia-container-toolkit; fallback a CPU con ajuste de perfil.
Disco insuficiente para modelos del perfil
shutil.disk_usage < requerido
Error bloqueante con sugerencia de usar perfil inferior o cambiar ubicación de OLLAMA_MODELS.
Timeout en inferencias largas (DeepSeek-R1)
httpx.TimeoutException
Timeouts configurables por modelo en catálogo (R1: 300s, otros: 120s).
Caché corrupta
sqlite3.DatabaseError al leer
puma cache clear y re-ejecución.



6. Qué no hacer (guardrails)
No añadir código que descargue, referencie o integre HELM. PUMA es independiente.
No usar temperature=0.0 con self-consistency (no tiene sentido). Validar en RunSpec.
No enviar telemetría. CodeCarbon offline-only (tracking_mode="process", nunca "machine" con report a cloud).
No hacer fine-tuning. PUMA evalúa, no entrena.
No invocar APIs externas en tiempo de run (OpenAI, Anthropic, etc.). Todo es Ollama local.
No reescribir la memoria académica ni los PEC; el trabajo es puramente sobre el código.
No hacer commits con secretos. .gitignore debe cubrir data/, results/, db/, logs/, .env.


7. Criterio de éxito global
Al cierre de la Fase 7, un usuario que clone el repositorio en una máquina con 16 GB RAM (con o sin GPU), Docker instalado y conexión a internet, debe poder:

Ejecutar ./start_puma.sh sin configurar nada más.
Esperar <20 min a que provisione (descarga de 2-3 modelos pequeños).
Ejecutar puma run specs/runs/smoke_triage.yaml y ver el progreso.
Abrir http://localhost:8501 y explorar los resultados en el dashboard.
Generar un informe con puma report <run_id>.
Comparar modelos con puma compare <run_id_1> <run_id_2>.

Todo lo anterior, 100 % en local, con trazabilidad completa y emisiones registradas.


8. Orden sugerido de ejecución por Claude Code
Claude Code debe trabajar en el orden estricto F0 → F7, creando un PR por fase (o un set de commits convencionales si trabaja en main directamente). No se adelantan tareas de fases posteriores sin cerrar el gate de la fase actual.

Para cada fase:

Lee la sección correspondiente de este documento y de INDEX.md.
Crea las specs bajo /specs/ de las funcionalidades a implementar.
Implementa tests antes del código en los módulos marcados (metrics, runtime, preflight, perturbations).
Implementa el código.
Ejecuta make lint && make test && make smoke.
Verifica el gate de la fase.
Hace commits atómicos y actualiza CHANGELOG.md.

Si una tarea de una fase se bloquea por una dependencia externa (ej. dataset inaccesible), Claude Code crea un mock temporal documentado (# FIXME F2.4: real TAWOS download blocked, using fixture), pasa el gate con el mock y abre un issue con etiqueta blocked-external. No se detiene la progresión por bloqueos externos no críticos.


9. Preguntas abiertas a resolver durante la implementación
Claude Code documenta en docs/open_questions.md cualquier decisión no trivial que tome sin consultar, para revisión posterior. Ejemplos esperables:

Política exacta de parseo de respuesta cuando el modelo no sigue el formato pedido (¿reintento?, ¿clase "unknown"?, ¿exclusión?).
Tamaño óptimo de muestra por escenario en cpu-standard (compromiso calidad estadística / tiempo de ejecución).
Estrategia de warm-up del modelo (¿primera llamada descartada?).
Criterio de corte para considerar un modelo "robusto" (¿robustness_score ≥ 0.95?).

Estas decisiones se consolidan en docs/design_decisions.md al cerrar cada fase.


