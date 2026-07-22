# Mermaid Diagrams

These render natively in GitHub's markdown preview.

## 1. High-level system flow

```mermaid
flowchart TD
    A[Documents: PDFs, scans, CSVs] --> B[OCR Service]
    B --> C[Text Chunking]
    C --> D[Vector Store - Chroma]
    B --> E[Knowledge Graph Agent]
    E --> F[(Neo4j Knowledge Graph)]
    D --> G[RAG Copilot Agent]
    F --> H[Contradiction and Drift Agent]
    F --> I[Maintenance and RCA Agent]
    F --> J[Compliance Agent]
    G --> K[FastAPI Backend]
    H --> K
    I --> K
    J --> K
    K --> L[Streamlit Dashboard]
```

## 2. Proactive multi-agent scan sequence

```mermaid
sequenceDiagram
    participant U as User (Dashboard)
    participant API as FastAPI /alerts/scan
    participant O as LangGraph scan_graph
    participant CA as Contradiction Agent
    participant MA as Maintenance/RCA Agent
    participant CO as Compliance Agent
    participant G as Neo4j

    U->>API: POST /alerts/scan
    API->>O: run_full_scan()
    O->>CA: run(state)
    CA->>G: Cypher: procedure-practice drift
    CA->>G: Cypher: version drift
    CA->>G: Cypher: silent recurrence candidates
    CA-->>O: findings[]
    O->>MA: run(state)
    MA->>G: aggregate incident co-occurrence
    MA-->>O: findings[]
    O->>CO: run(state)
    CO->>G: reclassify + unmapped procedure check
    CO-->>O: findings[]
    O-->>API: merged findings[]
    API-->>U: AlertsResponse (cited, confidence-scored)
```

## 3. Knowledge graph schema (entity-relationship view)

```mermaid
erDiagram
    PROCEDURE ||--o{ EQUIPMENT : GOVERNS
    PROCEDURE ||--o| PROCEDURE : SUPERSEDES
    WORKORDER ||--o{ EQUIPMENT : PERFORMED_ON
    INCIDENT ||--o{ EQUIPMENT : OCCURRED_ON
    PERSONNEL ||--o{ PROCEDURE : TRAINED_ON
    PROCEDURE ||--o{ REGULATORYCLAUSE : COMPLIES_WITH
    INCIDENT ||--o{ INCIDENT : SIMILAR_FAILURE_MODE

    EQUIPMENT {
        string id
        string tag
        string name
        string area
        string criticality
    }
    PROCEDURE {
        string id
        string title
        string version
        string effective_date
        int required_inspection_interval_days
    }
    WORKORDER {
        string id
        string wo_number
        string performed_on
        string status
    }
    INCIDENT {
        string id
        string title
        string occurred_on
        list symptoms
    }
    PERSONNEL {
        string id
        string name
        string role
    }
    REGULATORYCLAUSE {
        string id
        string code
        string source
    }
```

## 4. Copilot query flow

```mermaid
flowchart LR
    Q[User question] --> R[Vector similarity search - Chroma]
    R --> C{Confidence >= threshold?}
    C -- No --> ESC[Escalate to human - no answer generated]
    C -- Yes --> G[Gemini generates answer from evidence only]
    G --> RESP[Cited answer + confidence + reasoning trace]
    ESC --> RESP
```
