"""Safe provider failures; never expose upstream bodies or credentials."""


class AIError(ValueError):
    pass


class AICancelled(AIError):
    def __init__(self):
        super().__init__("AI interpretation cancelled.")


class TransportError(AIError):
    def __init__(self, code="network", transient=False):
        self.code = code
        self.transient = transient
        super().__init__(f"AI provider request failed ({code}).")
