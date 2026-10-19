
"""Database-driven registry repository.

Responsibilities:
- Load active agent configurations.
- Load and validate prompt configuration.
- Resolve configured tool metadata through agent-tool mappings.
- Persist execution audit records.

RBAC and agent execution are intentionally out of scope.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError

from backend.db.models.registries import (
    AgentRegistry,
    ExecutionAuditLog,
    ToolRegistry,
)
from backend.core.logger import get_logger

logger = get_logger("db.repositories.registry")


class RegistryConfigurationError(Exception):
    """Raised when a registry entry is incomplete or invalid."""


class RegistryRepository:
    """Validated database access for agent, prompt, and tool registries."""

    def __init__(self, db: Session):
        self.db = db

    def get_active_agents(
        self,
        agent_type: Optional[str] = None,
    ) -> List[AgentRegistry]:
        """Return active agents, optionally filtered by a DB-defined type."""
        logger.debug(f"Querying active agents from registry (filter agent_type={agent_type})...")

        query = (
            self.db.query(AgentRegistry)
            .options(joinedload(AgentRegistry.prompt))
            .filter(AgentRegistry.is_active.is_(True))
        )

        if agent_type is not None:
            query = query.filter(
                AgentRegistry.agent_type == agent_type
            )

        agents = query.order_by(AgentRegistry.name.asc()).all()
        logger.debug(f"Found {len(agents)} active agent(s) in registry.")
        return agents

    def get_agent_with_tools(
        self,
        agent_name: str,
    ) -> Optional[Dict[str, Any]]:
        """Load one active agent with its prompt and enabled tool mappings."""

        if not agent_name or not agent_name.strip():
            raise ValueError("agent_name must not be empty.")

        logger.info(f"Loading agent configuration from registry for: '{agent_name}'")

        agent = (
            self.db.query(AgentRegistry)
            .options(
                joinedload(AgentRegistry.prompt),
                joinedload(AgentRegistry.tools),
            )
            .filter(
                AgentRegistry.name == agent_name,
                AgentRegistry.is_active.is_(True),
            )
            .one_or_none()
        )

        if agent is None:
            logger.warning(f"Agent '{agent_name}' not found or inactive in registry.")
            return None

        prompt = agent.prompt

        if prompt is None or not prompt.template_text:
            raise RegistryConfigurationError(
                f"Active agent '{agent.name}' has no valid prompt."
            )

        if prompt.version is None:
            raise RegistryConfigurationError(
                f"Agent '{agent.name}' has no prompt version."
            )

        if not agent.model_name:
            raise RegistryConfigurationError(
                f"Agent '{agent.name}' has no configured model."
            )

        if agent.temperature is None:
            raise RegistryConfigurationError(
                f"Agent '{agent.name}' has no configured temperature."
            )

        tools = []

        for tool in agent.tools:
            if not tool.is_active:
                continue

            if not tool.handler_key:
                raise RegistryConfigurationError(
                    f"Active tool '{tool.name}' has no handler key."
                )

            if not tool.parameters_schema:
                raise RegistryConfigurationError(
                    f"Active tool '{tool.name}' has no parameter schema."
                )

            tools.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "handler_key": tool.handler_key,
                    "parameters_schema": tool.parameters_schema,
                }
            )

        logger.info(
            f"Successfully loaded agent '{agent.name}' from registry "
            f"[type={agent.agent_type}, model={agent.model_name}, temp={agent.temperature}, tools={len(tools)}]"
        )

        return {
            "name": agent.name,
            "display_name": agent.display_name,
            "description": agent.description,
            "agent_type": agent.agent_type,
            "model_name": agent.model_name,
            "temperature": agent.temperature,
            "system_prompt": prompt.template_text,
            "prompt_version": prompt.version,
            "tools": tools,
        }

    def log_execution(
        self,
        request_id: str,
        agent_name: str,
        input_query: str,
        status: str,
        output_response: Optional[str] = None,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        latency_ms: float = 0.0,
        error_message: Optional[str] = None,
    ) -> ExecutionAuditLog:
        """Persist an explicitly supplied execution outcome."""

        if not request_id or not agent_name or not status:
            raise ValueError(
                "request_id, agent_name, and status are required."
            )

        if latency_ms < 0:
            raise ValueError("latency_ms cannot be negative.")

        audit_entry = ExecutionAuditLog(
            request_id=request_id,
            user_id=user_id,
            user_role=user_role,
            agent_name=agent_name,
            input_query=input_query,
            output_response=output_response,
            tool_calls=tool_calls or [],
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
        )

        try:
            self.db.add(audit_entry)
            self.db.commit()
            self.db.refresh(audit_entry)
            logger.info(
                f"Execution audit persisted: request_id={request_id}, agent={agent_name}, "
                f"status={status}, latency={latency_ms:.1f}ms"
            )
            return audit_entry

        except SQLAlchemyError:
            self.db.rollback()
            logger.exception(
                "Failed to persist execution audit record."
            )
            raise
