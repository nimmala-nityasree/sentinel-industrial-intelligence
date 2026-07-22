"""
Knowledge graph domain model.

This module is the single source of truth for the Neo4j schema: node labels,
relationship types, and the properties each carries. `graph_service.py`
imports these constants rather than hard-coding label strings, so the schema
can evolve in one place.

Schema overview
----------------
Nodes:
    Equipment(id, tag, name, area, criticality)
    Procedure(id, title, version, effective_date, document_id)
    WorkOrder(id, wo_number, description, performed_on, status, document_id)
    Incident(id, title, description, occurred_on, symptoms, document_id)
    Personnel(id, name, role)
    RegulatoryClause(id, code, description, source)

Relationships:
    (Procedure)-[:GOVERNS]->(Equipment)
    (Procedure)-[:SUPERSEDES]->(Procedure)          # version lineage
    (WorkOrder)-[:PERFORMED_ON]->(Equipment)
    (Incident)-[:OCCURRED_ON]->(Equipment)
    (Incident)-[:SIMILAR_FAILURE_MODE]->(Incident)  # inferred by the agent, not raw data
    (Personnel)-[:TRAINED_ON]->(Procedure)
    (Procedure)-[:COMPLIES_WITH]->(RegulatoryClause)
"""
from dataclasses import dataclass, field


class NodeLabel:
    EQUIPMENT = "Equipment"
    PROCEDURE = "Procedure"
    WORK_ORDER = "WorkOrder"
    INCIDENT = "Incident"
    PERSONNEL = "Personnel"
    REGULATORY_CLAUSE = "RegulatoryClause"


class RelationshipType:
    GOVERNS = "GOVERNS"                          # Procedure -> Equipment
    SUPERSEDES = "SUPERSEDES"                     # Procedure -> Procedure
    PERFORMED_ON = "PERFORMED_ON"                 # WorkOrder -> Equipment
    OCCURRED_ON = "OCCURRED_ON"                   # Incident -> Equipment
    SIMILAR_FAILURE_MODE = "SIMILAR_FAILURE_MODE" # Incident -> Incident
    TRAINED_ON = "TRAINED_ON"                     # Personnel -> Procedure
    COMPLIES_WITH = "COMPLIES_WITH"               # Procedure -> RegulatoryClause


@dataclass
class EquipmentNode:
    id: str
    tag: str
    name: str
    area: str = "unspecified"
    criticality: str = "medium"


@dataclass
class ProcedureNode:
    id: str
    title: str
    version: str
    effective_date: str  # ISO date string
    document_id: str
    required_inspection_interval_days: int | None = None


@dataclass
class WorkOrderNode:
    id: str
    wo_number: str
    description: str
    performed_on: str  # ISO date string
    status: str
    document_id: str
    equipment_tag: str | None = None


@dataclass
class IncidentNode:
    id: str
    title: str
    description: str
    occurred_on: str  # ISO date string
    symptoms: list[str] = field(default_factory=list)
    document_id: str = ""
    equipment_tag: str | None = None


@dataclass
class PersonnelNode:
    id: str
    name: str
    role: str = "technician"


@dataclass
class RegulatoryClauseNode:
    id: str
    code: str
    description: str
    source: str  # e.g. "OISD", "Factory Act", "DGMS"
