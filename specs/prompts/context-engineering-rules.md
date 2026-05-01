# Context Engineering Rules (RAG)

## Objective
Optimise context for LLM agents using relevant information retrieval (RAG).

## Retrieval Rules

### 1. Top-K Documents
- Always retrieve the **5 most relevant documents**
- Use similarity score ≥ 0.7 as threshold
- If not enough documents are available, use all available ones

### 2. Summaries (Summarization)
- Generate a summary of **200 tokens maximum** per document
- Include: title, purpose, data structure
- Prioritise recent information (modifications in the last 24h)

### 3. Avoid Context Contamination
- **Clean context between experiments**: remove previous conversation history
- **Separate runs**: each benchmark is independent
- **Do not mix train/test data**: maintain strict separation

### 4. Prompt Construction
Recommended order:
1. System prompt (global rules)
2. Retrieved context (RAG)
3. Few-shot examples (if applicable)
4. User query (current input)

### 5. Context Metrics
- Track tokens used per prompt
- Alert if > 4000 tokens
- Consider truncating less relevant context

## RAG Implementation

### Indexed Sources
- `/data/*.csv` - Datasets (jira_balanced_200.csv, tawos_clean.csv)
- `/specs/*.md` - SDD specifications
- `/specs/*.spec.md` - Agent specs
- `/specs/prompts/*.md` - Optimised prompts

### Chunks
- Size: 500 tokens per chunk
- Overlap: 50 tokens between chunks
- Embedding model: sentence-transformers (local)

## Best Practices

1. **Embedding cache**: Do not recalculate if data has not changed
2. **Fallback**: If RAG fails, use default prompts
3. **Logging**: Record which documents were retrieved
4. **A/B Testing**: Compare performance with/without RAG

## Agent Integration
- Triage Agent: retrieve triage specs + classification examples
- Estimation Agent: retrieve estimation specs + similar project examples
- Code Generator: retrieve specs for the feature to implement
