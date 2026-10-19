"""Database Seeder for DocChat Registries.

Loads initial Prompts, Tools, Agents, and Tool Mappings from an external
JSON fixture file (backend/db/seeds/registry_seed.json) into PostgreSQL idempotently.
Contains zero hardcoded agent configurations in Python code.
"""
import json
import os
from typing import Optional
from sqlalchemy.orm import Session

from backend.core.config import CONFIG
from backend.core.database import Base, SessionLocal, engine
from backend.core.logger import get_logger
from backend.db.models.registries import (
    PromptRegistry,
    ToolRegistry,
    AgentRegistry,
)

logger = get_logger("db.seed")

DEFAULT_SEED_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "seeds", "registry_seed.json")
)


def _expand_env_vars(text: str) -> str:
    """Expands ${VAR} and $VAR placeholders from environment variables cross-platform."""
    import re
    return re.sub(r"\$\{([^}]+)\}", lambda m: os.getenv(m.group(1), m.group(0)), text)


def seed_database(seed_file_path: Optional[str] = None) -> None:
    """Creates database tables and populates registry data from a JSON fixture idempotently."""
    file_path = seed_file_path or os.getenv("SEED_FILE_PATH", DEFAULT_SEED_FILE)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Registry seed fixture not found at: {file_path}")

    logger.info(f"Loading seed data from: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        raw_content = f.read()
    # Dynamically expand any environment variables (e.g. ${MODEL_NAME}) present in the fixture
    expanded_content = _expand_env_vars(raw_content)
    seed_data = json.loads(expanded_content)

    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified.")

    db: Session = SessionLocal()
    try:
        # ---------------------------------------------------------
        # 1. Seed Prompts (Keyed strictly by (name, version))
        # ---------------------------------------------------------
        prompt_records = {}
        for p in seed_data.get("prompts", []):
            p_name = p.get("name")
            p_version = p.get("version")
            if not p_name or not p_version:
                raise ValueError("Every prompt in the JSON fixture must have 'name' and 'version'.")

            prompt_key = (p_name, str(p_version))
            existing = (
                db.query(PromptRegistry)
                .filter(
                    PromptRegistry.name == p_name,
                    PromptRegistry.version == str(p_version)
                )
                .first()
            )
            if not existing:
                record = PromptRegistry(
                    name=p_name,
                    version=str(p_version),
                    description=p.get("description"),
                    template_text=p["template_text"],
                    input_variables=p.get("input_variables", []),
                    is_active=p.get("is_active", True)
                )
                db.add(record)
                db.flush()
                prompt_records[prompt_key] = record
                logger.info(f"Seeded Prompt: {p_name} (v{p_version})")
            else:
                prompt_records[prompt_key] = existing

        # ---------------------------------------------------------
        # 2. Seed Agents
        # ---------------------------------------------------------
        agent_records = {}
        for a in seed_data.get("agents", []):
            agent_name = a.get("name")
            if not agent_name:
                raise ValueError("Every agent in the JSON fixture must have a 'name'.")

            # 1. Require temperature in the JSON fixture (no hardcoded 0.0 fallback)
            if "temperature" not in a or a["temperature"] is None:
                raise ValueError(
                    f"Agent '{agent_name}' is missing required field 'temperature' in JSON fixture. "
                    "A numeric temperature between 0.0 and 2.0 must be explicitly configured."
                )
            try:
                temperature = float(a["temperature"])
            except (TypeError, ValueError) as err:
                raise ValueError(
                    f"Agent '{agent_name}' has invalid temperature '{a['temperature']}': {err}"
                )

            # 2. Resolve prompts deterministically using explicit prompt_name and prompt_version
            p_name = a.get("prompt_name")
            p_version = a.get("prompt_version")
            if not p_name or not p_version:
                raise ValueError(
                    f"Agent '{agent_name}' must explicitly specify both 'prompt_name' and 'prompt_version'."
                )

            prompt_key = (p_name, str(p_version))
            prompt_obj = prompt_records.get(prompt_key)
            if not prompt_obj:
                prompt_obj = (
                    db.query(PromptRegistry)
                    .filter(
                        PromptRegistry.name == p_name,
                        PromptRegistry.version == str(p_version)
                    )
                    .first()
                )
                if prompt_obj:
                    prompt_records[prompt_key] = prompt_obj

            # 3. Raise clear configuration error if required prompt is missing or invalid
            if not prompt_obj:
                raise ValueError(
                    f"Agent '{agent_name}' references missing or invalid prompt: "
                    f"name='{p_name}', version='{p_version}'. "
                    "Ensure the prompt is defined in the JSON fixture or existing database."
                )

            # Model resolution from fixture or active configuration
            model_name = a.get("model_name") or CONFIG.GROQ_MODEL_NAME
            if not model_name:
                raise ValueError(f"Agent '{agent_name}' must specify a 'model_name'.")

            existing = db.query(AgentRegistry).filter(AgentRegistry.name == agent_name).first()
            if not existing:
                record = AgentRegistry(
                    name=agent_name,
                    display_name=a["display_name"],
                    description=a["description"],
                    agent_type=a["agent_type"],
                    prompt_id=prompt_obj.id,
                    model_name=model_name,
                    temperature=temperature,
                    required_roles=a.get("required_roles"),
                    is_active=a.get("is_active", True)
                )
                db.add(record)
                db.flush()
                agent_records[agent_name] = record
                logger.info(f"Seeded Agent: {agent_name} ({a['agent_type']})")
            else:
                agent_records[agent_name] = existing

        # ---------------------------------------------------------
        # 3. Seed Tools (Linked directly to agent_id)
        # ---------------------------------------------------------
        tool_records = {}
        for t in seed_data.get("tools", []):
            t_name = t.get("name")
            agent_name = t.get("agent_name")
            if not t_name:
                raise ValueError("Every tool in the JSON fixture must have a 'name'.")
            if not agent_name:
                raise ValueError(f"Tool '{t_name}' must specify an 'agent_name' to link via foreign key.")

            agent_obj = agent_records.get(agent_name) or db.query(AgentRegistry).filter(AgentRegistry.name == agent_name).first()
            if not agent_obj:
                raise ValueError(f"Tool '{t_name}' references unknown agent '{agent_name}'.")

            existing = (
                db.query(ToolRegistry)
                .filter(ToolRegistry.agent_id == agent_obj.id, ToolRegistry.name == t_name)
                .first()
            )
            if not existing:
                record = ToolRegistry(
                    agent_id=agent_obj.id,
                    name=t_name,
                    description=t["description"],
                    handler_key=t["handler_key"],
                    parameters_schema=t.get("parameters_schema", {}),
                    is_active=t.get("is_active", True)
                )
                db.add(record)
                db.flush()
                tool_records[t_name] = record
                logger.info(f"Seeded Tool '{t_name}' for Agent '{agent_name}'")
            else:
                tool_records[t_name] = existing

        db.commit()
        logger.info("All registries seeded successfully from JSON fixture.")

    except Exception as e:
        db.rollback()
        logger.exception(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
