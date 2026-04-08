<h1 align="center">PUMA</h1>
<h2 align="center">(PUMA Understanding & Management w Agents)</h2>

<p align="center">
  <a href="https://github.com/pumacp/puma" alt="_blank">
    <img src="https://img.shields.io/github/stars/pumacp/puma?style=social" />
  </a>
  <a href="https://github.com/pumacp/puma#reproducibility" alt="_blank">
    <img src="https://img.shields.io/badge/Reproducible-Yes-brightgreen" />
  </a>
  <a href="https://github.com/codecarbon/codecarbon" alt="_blank">
    <img src="https://img.shields.io/badge/Tracks%20CO₂-CodeCarbon-teal" />
  </a>
  <a href="LICENSE" alt="_blank">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" />
  </a>
</p>

<p align="center">
  <a href="https://www.python.org" alt="_blank">
    <img src="https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white" />
  </a>
  <a href="https://ollama.com" alt="_blank">
    <img src="https://img.shields.io/badge/Ollama-Local%20LLM-green?logo=ollama" />
  </a>
  <a href="https://www.docker.com" alt="_blank">
    <img src="https://img.shields.io/badge/Docker-Ready-blue?logo=docker&logoColor=white" />
  </a>
  <a href="https://github.com/pumacp/puma-vault">
    <img src="https://img.shields.io/badge/PUMA%20Vault-Repository-black?logo=github"/>
  </a>
</p>

<p align="center">
  <a href="https://github.com/pumacp/puma/actions" alt="_blank">
    <img src="https://img.shields.io/github/actions/workflow/status/pumacp/puma/ci.yml?branch=main" />
  </a>
  <a href="https://github.com/pumacp/puma/releases" alt="_blank">
    <img src="https://img.shields.io/github/v/release/pumacp/puma" />
  </a>
  <a href="https://github.com/pumacp/puma-vault/issues" alt="_blank">
    <img src="https://img.shields.io/github/issues-raw/pumacp/puma-vault" />
  </a>
  <a href="https://github.com/pumacp/puma/pulls" alt="_blank">
    <img src="https://img.shields.io/github/issues-pr-raw/pumacp/puma" />
  </a>
</p>

<br>
<p align="center">
  <a href="https://pumacp.github.io/puma-vault/" rel="noopener noreferrer">
    <img alt="PUMA Vault Docs"
         src="https://img.shields.io/badge/Explore%20PUMA%20Vault-Click%20Here-00bfff?style=for-the-badge&logo=github&cacheSeconds=1"
         style="display:inline-block; vertical-align:middle; margin:0 8px;" height="60" width="420" />
  </a>
  </p>

<p align="center">
  <img src="assets/img/PUMA.png" alt="PUMA 307" width="307" />
</p>

<h2 align="center">Benchmark - Local LLM Evaluation Framework</h2>

---

<p align="center">
  <a href="https://github.com/pumacp/puma-vault" rel="noopener noreferrer">
    <img alt="PUMA Vault Repo"
         src="https://img.shields.io/badge/Explore%20PUMA%20Vault%20Repo-Click%20Here-00bfff?style=for-the-badge&logo=github&cacheSeconds=1"
         style="display:inline-block; vertical-align:middle; margin:0 8px;" />
  </a>
  </p>

---

**F**ollowing empirical evidence, ICT project management faces triage, estimation, and learning inefficiencies.<br>
**O**bserved widely, these persist despite abundant historical data.<br>
**L**aying a rigorous foundation requires reproducible benchmarking.<br>
**L**everaging labeled datasets enables systematic evaluation of LLM performance.<br>
**O**utcomes are compared using quantitative metrics and statistical analysis.<br>
**W**ith an incremental design, a minimal viable benchmark is defined.<br>

**T**hrough open-source release, results become reproducible and verifiable.<br>
**H**ence, the framework supports extensibility across models and tasks.<br>
**E**ventually, it enables integration into real organizational settings.<br>

**W**ithin ICT environments, recurring inefficiencies hinder effective decision-making.<br>
**H**eterogeneous data sources complicate prioritization and estimation processes.<br>
**I**n response, this work builds a reproducible LLM-based benchmark.<br>
**T**he focus is on issue triage and story-point estimation tasks.<br>
**E**valuation follows controlled experiments with statistical validation.<br>

**P**rotocols ensure reproducibility through fixed parameters and configurations.<br>
**U**sing carbon tracking, the framework measures energy impact.<br>
**M**oreover, the MVP delivers a valid and original contribution.<br>
**A**ll artefacts are released as open source for replication and extension.<br>

---

A deterministic framework for evaluating local Large Language Models (LLMs) via Ollama for software engineering tasks: **Issue Triage** and **Effort Estimation (Story Points)**.

This project implements a rigorous evaluation methodology based on:

* **olmes** (Allen AI) - Evaluation framework for language models
* **ollama-benchmark** - Benchmarking methodology
* **output-drift-financial-llms** (IBM) - Output Drift pattern
* **ai_sprint_estimator** - Estimation methodology
* **LLM_Tool** - Triage patterns

---

# 📌 0. PUMA Project Description

## 0.1 Purpose and Objectives

**PUMA Benchmark** is a framework designed to evaluate local language models (LLMs) in software engineering tasks. The project automates benchmarking using **Ollama** as a local runtime.

### 🎯 Main Objectives

| Objective             | Description                                                                  |
| --------------------- | ---------------------------------------------------------------------------- |
| **Issue Triage**      | Classify Jira issues into 4 priority levels: Critical, Major, Minor, Trivial |
| **Effort Estimation** | Estimate story points using the Fibonacci series                             |
| **Carbon Tracking**   | Measure carbon footprint using CodeCarbon                                    |
| **Reproducibility**   | Deterministic results (temperature=0, fixed seed)                            |
| **History**           | Track all executions for historical comparison                               |

---

## 0.2 Metrics and Targets

### 🧠 Issue Triage

| Metric       | Target  | Description                           |
| ------------ | ------- | ------------------------------------- |
| **F1-Macro** | >= 0.55 | Harmonic mean of precision and recall |

**Priority Classes:**

* **Critical**: System down, data loss, security breach
* **Major**: Core functionality broken
* **Minor**: Minor bug, workaround available
* **Trivial**: Cosmetic or documentation issue

---

### 📊 Effort Estimation

| Metric   | Target | Description             |
| -------- | ------ | ----------------------- |
| **MAE**  | <= 3.0 | Mean Absolute Error     |
| **MdAE** | -      | Median Absolute Error   |
| **RMSE** | -      | Root Mean Squared Error |

**Story Points Scale:** Fibonacci (1, 2, 3, 5, 8, 13...)

---

## 0.3 Reference Configuration

### 💻 Host Hardware

| Component | Specification          |
| --------- | ---------------------- |
| CPU       | Intel Core i7-10750H   |
| RAM       | 32 GB DDR4             |
| GPU       | NVIDIA RTX 2060 Mobile |
| VRAM      | 6 GB                   |
| OS        | Ubuntu 24.04           |

---

### ⚡ Observed Performance

| Mode | Time/Inference | Speedup | Memory    |
| ---- | -------------- | ------- | --------- |
| GPU  | ~1-2s          | ~5-7x   | ~4GB VRAM |
| CPU  | ~10-15s        | 1x      | ~8GB RAM  |

---

### 🤖 Supported Models

| Model        | VRAM  | Use Case      | Accuracy  |
| ------------ | ----- | ------------- | --------- |
| qwen2.5:0.5b | 0.6GB | Testing       | Low       |
| qwen2.5:1.8b | 1.9GB | 8GB RAM       | Medium    |
| qwen2.5:3b   | 3.9GB | ✅ Recommended | High      |
| qwen2.5:7b   | 7.4GB | 16GB+         | Very High |
| mistral:7b   | 4.1GB | 16GB+         | High      |
| llama3:8b    | 4.9GB | 16GB+         | High      |

---

### ⚙️ Environment Configuration (.env)

```bash
GPU_MODE=true
LLM_MODEL=qwen2.5:3b
OLLAMA_NUM_PARALLEL=1
ESTIMATION_NUM_ITEMS=10
EVALUATION_TIMEOUT=0
TRIAGE_TARGET_F1=0.55
ESTIMATION_TARGET_MAE=3.0
USE_CACHE=1
```

---

## 0.4 Data Sources

### 📁 Triage Dataset

| File                  | Records | Description      |
| --------------------- | ------- | ---------------- |
| jira_balanced_200.csv | 200     | Balanced dataset |

---

### 📁 Estimation Dataset (TAWOS)

| Project | Records |
| ------- | ------- |
| MESOS   | 1,513   |
| APSTUD  | 476     |
| XD      | 811     |
| Total   | 31,294  |

---

## 0.5 Expected Results

### ✅ Triage

```
F1-Macro >= 0.55
Critical: ~0.75-0.80
Major: ~0.60-0.65
Minor: ~0.65-0.72
Trivial: ~0.30-0.50
```

---

### ✅ Estimation

```
MAE <= 3.0
MdAE ~2.0-3.0
Valid predictions >80%
```

---

# 🛠️ 1. Command Guide

## 1.1 Installation

### Requirements

```bash
docker --version
docker-compose version
nvidia-smi
docker info | grep nvidia
```

---

### NVIDIA Toolkit Installation

```bash
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

---

### Start PUMA

```bash
cd ../puma
chmod +x start_puma.sh
./start_puma.sh
docker ps | grep puma
```

---

### Check Models

```bash
docker exec puma_ollama ollama list
```

---

### Download Model

```bash
docker exec puma_ollama ollama pull qwen2.5:3b
```

---

## 1.2 Evaluation Commands

### ⚡ Quick Test

```bash
docker exec -e TRIAGE_NUM_ISSUES=10 puma_evaluator python src/evaluate_triage.py
```

---

### 🧪 Full Evaluation

```bash
docker exec puma_evaluator python src/evaluate_triage.py
```

---

## 1.3 Results Visualization

```bash
docker exec puma_evaluator cat results/triage_metrics.json
```

---

## 1.4 Cleanup

```bash
docker exec puma_evaluator rm -f /app/results/*.json
```

---

## 1.5 Testing

```bash
docker exec puma_evaluator pytest tests/
```

---

# 🏗️ Architecture

```
puma_network
 ├── ollama (LLM runtime)
 └── evaluator (Python)
```

---

# 📁 Project Structure

```
puma/
├── docker-compose.yml
├── src/
├── data/
├── results/
├── reports/
```

---

# ⚡ Quick Start

```bash
chmod +x start_puma.sh
./start_puma.sh
```

---

# 📊 Metrics

## F1-Macro

```
F1 = 2 * (Precision * Recall) / (Precision + Recall)
```

---

## MAE

```
MAE = (1/n) * Σ |predicted - actual|
```

---

# ⚙️ Configuration

```bash
cp .env.example .env
nano .env
```

---

# 📈 Benchmark History

```bash
docker exec puma_evaluator python src/history.py
```

---

# 🐳 Docker Commands

```bash
docker compose up -d
docker compose down
```

---

# 🧪 Evaluation Workflow

```bash
docker exec puma_evaluator python src/evaluate_triage.py
docker exec puma_evaluator python src/evaluate_estimation.py MESOS
```

---

# 🧠 How It Works

### Triage Flow

```
Dataset → LLM → Prediction → Metrics
```

---

### Estimation Flow

```
Dataset → LLM → Fibonacci Mapping → Metrics
```

---

# ⚠️ Troubleshooting

### GPU Not Detected

```bash
nvidia-smi
docker info | grep nvidia
```

---

# 🔧 Advanced Features

* Deterministic inference (temperature=0)
* Cache system
* Carbon tracking
* Statistical testing (Wilcoxon)

---

# 🧩 Development Methodology

* **Spec-First Development (SDD)**
* **Agentic Coding**
* **Context Engineering**

---

# 🤖 Agents

```
agents/
├── orchestrator.py
├── triage_agent.py
├── estimation_agent.py
```

---

# 🔄 Reproducibility

* Temperature = 0
* Seed = 42
* Deterministic outputs

---

# 🧪 Agent Execution

```bash
docker exec puma_evaluator python agents/orchestrator.py triage
```

---

# 📌 TODO Roadmap

### Phase 2

* Multi-project support
* Batch benchmarking
* Model comparison

### Phase 3

* Web UI
* CI/CD
* Observability

---

# 📜 License

MIT License

---

<p align="center">
  Part of the <a href="https://github.com/pumacp/puma-vault"><b>PUMA Capstone Project</b></a>
</p>

