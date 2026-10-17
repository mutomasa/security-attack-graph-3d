"""JSON Schemas for guided decoding: node names can only be chosen, never written freely."""

from backend.models.schemas import AttackPath, IntentType, Scenario

EVENT_MAX_LENGTH = 80
ROOT_CAUSE_MAX_LENGTH = 160


def intent_schema(scenario: Scenario) -> dict:
    labels = sorted({n.label for n in scenario.graph.nodes})
    endpoint = {"enum": [*labels, None]}
    return {
        "type": "object",
        "properties": {
            "intent": {"enum": [t.value for t in IntentType]},
            "source": endpoint,
            "target": endpoint,
        },
        "required": ["intent", "source", "target"],
        "additionalProperties": False,
    }


def explanation_schema(path: AttackPath) -> dict:
    """One step per path node, in path order (`prefixItems` + `const`); the fix is one of the path's nodes."""
    return {
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "prefixItems": [_step_schema(n.label) for n in path.nodes],
                "items": False,
                "minItems": len(path.nodes),
            },
            "root_cause": {"type": "string", "maxLength": ROOT_CAUSE_MAX_LENGTH},
            "priority_fix": {"enum": sorted({n.label for n in path.nodes})},
        },
        "required": ["steps", "root_cause", "priority_fix"],
        "additionalProperties": False,
    }


def _step_schema(label: str) -> dict:
    return {
        "type": "object",
        "properties": {"node": {"const": label}, "event": {"type": "string", "maxLength": EVENT_MAX_LENGTH}},
        "required": ["node", "event"],
        "additionalProperties": False,
    }
