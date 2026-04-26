from dataclasses import dataclass


@dataclass
class RoutingDecision:
    action: str
    target_state: str


class RoutingService:
    """
    Pure logic (C2). No LLM. No DB. No side effects.
    Receives ReadinessResult, returns RoutingDecision.
    """

    def route(self, readiness_status: str) -> RoutingDecision:
        """
        Decision matrix for moving leads to the next state.
        Aligns with FIles/lead_State_machine.md.
        """
        if readiness_status == "ready":
            # Moving from 'new' (or 'needs_info') to 'ready'
            return RoutingDecision(
                action="mark_ready",
                target_state="ready",
            )
        return RoutingDecision(
            action="trigger_followup",
            target_state="needs_info",
        )


# Singleton instance
routing_service = RoutingService()
