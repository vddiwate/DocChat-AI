"""SQLAlchemy Database Models for Prompt, Tool, and Agent Registries, RBAC, and Audit Logging."""
import datetime
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint
)
from sqlalchemy.orm import relationship, validates
from backend.core.database import Base


class PromptRegistry(Base):
    """Registry storing versioned system prompts and prompt templates for agents."""
    __tablename__ = "prompt_registry"

    id = Column(Integer, primary_key=True, index=True)
    # Name is not globally unique on its own to allow multiple versions of the same prompt template
    name = Column(String(100), nullable=False, index=True)
    version = Column(String(20), nullable=False)
    description = Column(String(255), nullable=True)
    template_text = Column(Text, nullable=False)
    input_variables = Column(JSON, default=list, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_prompt_name_version"),
    )

    # Relationships
    agents = relationship("AgentRegistry", back_populates="prompt")

    def __repr__(self) -> str:
        return f"<PromptRegistry(name='{self.name}', version='{self.version}', is_active={self.is_active})>"


class ToolRegistry(Base):
    """
    Registry cataloging authorized tools and their executable Python handlers.
    Each tool directly links to an agent via agent_id Foreign Key (1 Agent -> Many Tools).
    handler_key resolves via a trusted in-code Python dispatcher registry.
    Arbitrary code provided by the database is never dynamically evaluated.
    """
    __tablename__ = "tool_registry"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agent_registry.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    handler_key = Column(String(100), nullable=False)  # Key mapped to trusted Python handler catalog
    parameters_schema = Column(JSON, default=dict, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("agent_id", "name", name="uq_agent_tool_name"),
    )

    # Relationships
    agent = relationship("AgentRegistry", back_populates="tools")

    def __repr__(self) -> str:
        return f"<ToolRegistry(name='{self.name}', agent_id={self.agent_id}, handler_key='{self.handler_key}')>"


class AgentRegistry(Base):
    """
    Registry cataloging all agents (Supervisor and Worker agents) with RBAC and model parameters.
    All attributes (agent_type, model_name, temperature, required_roles, prompt_id) are strictly database-driven.
    """
    __tablename__ = "agent_registry"

    SUPPORTED_AGENT_TYPES = frozenset({"SUPERVISOR", "WORKER"})

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)  # Detailed purpose used by Supervisor for routing
    agent_type = Column(String(50), nullable=False)  # Database-driven: 'SUPERVISOR' or 'WORKER'

    # Foreign Key to PromptRegistry
    prompt_id = Column(Integer, ForeignKey("prompt_registry.id", ondelete="SET NULL"), nullable=True)

    # Model and inference parameters (Strictly database-driven)
    model_name = Column(String(100), nullable=False)
    temperature = Column(Float, nullable=False)

    # Optional role tags (nullable, RBAC enforcement disabled)
    required_roles = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint("temperature >= 0.0 AND temperature <= 2.0", name="chk_agent_temperature"),
    )

    # Relationships
    prompt = relationship("PromptRegistry", back_populates="agents")
    tools = relationship("ToolRegistry", back_populates="agent", cascade="all, delete-orphan")

    @validates("temperature")
    def validate_temperature(self, key, value):
        """Validates that agent temperature falls within the supported 0.0-2.0 range."""
        if value is None:
            raise ValueError("Agent temperature is required and cannot be None.")
        try:
            val_float = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Agent temperature must be a valid float, got {value!r}")
        if not (0.0 <= val_float <= 2.0):
            raise ValueError(f"Agent temperature must be within [0.0, 2.0], got {val_float}")
        return val_float

    @validates("agent_type")
    def validate_agent_type(self, key, value):
        """Validates agent_type against supported types (e.g. SUPERVISOR, WORKER)."""
        if not value or not isinstance(value, str):
            raise ValueError("Agent agent_type is required and must be a non-empty string.")
        normalized = value.strip().upper()
        if normalized not in self.SUPPORTED_AGENT_TYPES:
            raise ValueError(
                f"Unsupported agent_type '{value}'. Must be one of: {sorted(self.SUPPORTED_AGENT_TYPES)}"
            )
        return normalized

    def __repr__(self) -> str:
        return f"<AgentRegistry(name='{self.name}', type='{self.agent_type}', active={self.is_active})>"


class ExecutionAuditLog(Base):
    """Audit table logging execution traces, tool calls, RBAC decisions, latency, and outcomes."""
    __tablename__ = "execution_audit_log"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(100), index=True, nullable=False)
    user_id = Column(String(100), nullable=True)
    user_role = Column(String(50), nullable=True)
    agent_name = Column(String(100), index=True, nullable=False)
    input_query = Column(Text, nullable=False)
    output_response = Column(Text, nullable=True)
    tool_calls = Column(JSON, default=list, nullable=False)
    latency_ms = Column(Float, default=0.0, nullable=False)
    status = Column(String(50), nullable=False)  # Explicit outcome: e.g. 'SUCCESS', 'FAILED', 'ACCESS_DENIED'
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

    @validates("latency_ms")
    def validate_latency(self, key, value):
        """Ensures latency_ms records valid, non-negative execution durations."""
        if value is not None and float(value) < 0.0:
            raise ValueError(f"latency_ms cannot be negative, got {value}")
        return float(value) if value is not None else 0.0

    def __repr__(self) -> str:
        return f"<ExecutionAuditLog(req='{self.request_id}', agent='{self.agent_name}', status='{self.status}')>"
