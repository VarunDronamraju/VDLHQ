class LHQException(Exception):
    """Base exception for LocationHQ"""

    pass


class LeadNotFound(LHQException):
    def __init__(self, lead_id):
        self.lead_id = lead_id
        super().__init__(f"Lead not found: {lead_id}")


class InvalidTransition(LHQException):
    def __init__(self, current: str, target: str):
        self.current = current
        self.target = target
        super().__init__(f"Invalid transition: {current} → {target}")


class LLMFailure(LHQException):
    def __init__(self, message="LLM call failed"):
        super().__init__(message)


class IntakeParseFailure(LHQException):
    def __init__(self, message="Failed to parse inquiry data"):
        super().__init__(message)


class ReadinessFailure(LHQException):
    def __init__(self, message="Lead readiness check failed"):
        super().__init__(message)


class MatchingFailure(LHQException):
    def __init__(self, message="Location matching failed"):
        super().__init__(message)


class CommunicationFailure(LHQException):
    def __init__(self, message="Communication delivery failed"):
        super().__init__(message)


class SchedulerError(LHQException):
    def __init__(self, message="Scheduler job failed"):
        super().__init__(message)
