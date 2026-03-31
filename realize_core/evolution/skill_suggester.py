"""
Skill Suggestion Engine: Auto-generate skill proposals from detected gaps.

When gap detection finds repeated patterns or unhandled requests,
this module uses Claude to draft a v2 skill YAML that could address the gap.
The suggestion is presented to the user for approval before being installed.
"""

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Valid identifier pattern for skill names
_VALID_SKILL_NAME = re.compile(r"^[a-z][a-z0-9_]{1,50}$")


def _validate_skill_yaml(parsed: object) -> bool:
    """Validate that parsed YAML is a well-formed skill definition."""
    if not isinstance(parsed, dict):
        return False
    # Required fields
    if "name" not in parsed or "version" not in parsed:
        return False
    # Name must be a valid identifier
    if not isinstance(parsed["name"], str) or not _VALID_SKILL_NAME.match(parsed["name"]):
        logger.warning(f"Invalid skill name: {parsed.get('name')}")
        return False
    # Steps must be a non-empty list
    steps = parsed.get("steps")
    if not isinstance(steps, list) or len(steps) == 0:
        logger.warning("Skill must have at least one step")
        return False
    # Each step must have id and type
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            return False
        if "id" not in step or "type" not in step:
            logger.warning(f"Step {i} missing 'id' or 'type'")
            return False
    return True

SKILL_DRAFT_PROMPT = """You are a skill designer for an AI operations system.

Based on the detected pattern below, draft a YAML skill definition (v2 format).
The skill should use available tools (web_search, web_fetch, browser_navigate, etc.)
and agents from the target system.

Pattern detected:
{pattern_description}

Sample user messages:
{samples}

Target system: {system_key}
Available agents: {agents}

Write ONLY the YAML content (no markdown fences). Follow this format:
name: skill_name_here
version: "2.0"
description: "One-line description"
system: {system_key}
task_type: relevant_type
triggers:
  - trigger phrase 1
  - trigger phrase 2
  - trigger phrase 3
tools_required:
  - web_search
pipeline: [agent1, agent2]
steps:
  - id: step1
    type: tool
    action: web_search
    label: What this step does
    params:
      query: "{{user_message}}"
  - id: step2
    type: agent
    agent: agent_name
    label: What this step does
    inject_context: [step1]
    prompt: |
      Process the results for: "{{user_message}}"
output_format: text
"""


async def suggest_skill_from_gap(suggestion: dict, system_config: dict = None) -> str | None:
    """
    Generate a skill YAML draft from a gap detection suggestion.

    Returns YAML string for the proposed skill, or None if generation fails.
    """
    action_data = suggestion.get("action_data", "{}")
    if isinstance(action_data, str):
        action_data = json.loads(action_data)
    samples = action_data.get("samples", [])
    system_key = action_data.get("system_key", "default")

    agents = list((system_config or {}).get("agents", {}).keys())

    prompt = SKILL_DRAFT_PROMPT.format(
        pattern_description=suggestion.get("description", ""),
        samples="\n".join(f"- {s}" for s in samples[:5]),
        system_key=system_key,
        agents=", ".join(agents) if agents else "orchestrator, writer, analyst",
    )

    try:
        # Route through LLM router (provider-agnostic)
        try:
            from realize_core.llm.router import route_to_llm
            response = await route_to_llm(
                system_prompt=prompt,
                messages=[{"role": "user", "content": "Generate the skill YAML."}],
                task_type="content",
                max_tokens=800,
            )
        except (ImportError, Exception) as router_err:
            logger.debug(f"Router unavailable, falling back to claude: {router_err}")
            from realize_core.llm.claude_client import call_claude
            response = await call_claude(
                system_prompt=prompt,
                messages=[{"role": "user", "content": "Generate the skill YAML."}],
                max_tokens=800,
            )

        yaml_text = response.strip()
        if yaml_text.startswith("```"):
            yaml_text = yaml_text.split("\n", 1)[1] if "\n" in yaml_text else yaml_text[3:]
            if yaml_text.endswith("```"):
                yaml_text = yaml_text[:-3]
            yaml_text = yaml_text.strip()

        try:
            import yaml

            parsed = yaml.safe_load(yaml_text)
            if not _validate_skill_yaml(parsed):
                return None
        except Exception:
            return None

        logger.info(f"Generated skill suggestion: {parsed.get('name', '?')}")
        return yaml_text

    except Exception as e:
        logger.error(f"Skill suggestion generation failed: {e}")
        return None


async def install_suggested_skill(yaml_text: str, skills_dir: str = None) -> str:
    """
    Install a suggested skill by writing it to the skills directory.

    Returns status message.
    """
    try:
        import yaml

        parsed = yaml.safe_load(yaml_text)
    except Exception as e:
        return f"Failed to parse skill YAML: {e}"

    skill_name = parsed.get("name", "unknown_skill")
    system_key = parsed.get("system", "shared")

    if skills_dir:
        target_dir = Path(skills_dir) / system_key
    else:
        try:
            from realize_core.config import KB_PATH
            target_dir = KB_PATH / "systems" / system_key / "R-routines" / "skills"
        except (ImportError, AttributeError):
            target_dir = Path("skills") / system_key
    target_dir.mkdir(parents=True, exist_ok=True)

    skill_file = target_dir / f"{skill_name}.yaml"
    if skill_file.exists():
        return f"Skill '{skill_name}' already exists at {skill_file}"

    with open(skill_file, "w") as f:
        f.write(yaml_text)

    return f"Skill '{skill_name}' installed at {skill_file}"


def format_skill_preview(yaml_text: str) -> str:
    """Format a skill suggestion for display."""
    try:
        import yaml

        parsed = yaml.safe_load(yaml_text)
    except Exception:
        return f"```\n{yaml_text[:500]}\n```"

    name = parsed.get("name", "?")
    desc = parsed.get("description", "")
    triggers = parsed.get("triggers", [])[:3]
    steps = parsed.get("steps", [])

    lines = [f"**Suggested Skill: {name}**", f"_{desc}_\n", f"Triggers: {', '.join(triggers)}", f"Steps: {len(steps)}"]
    for i, step in enumerate(steps, 1):
        step_type = step.get("type", step.get("action", "?"))
        label = step.get("label", step.get("id", f"Step {i}"))
        lines.append(f"  {i}. [{step_type}] {label}")

    lines.append(f"\n```\n{yaml_text[:600]}\n```")
    return "\n".join(lines)
