"""Versioned prompt management."""

class PromptRegistry:
    def __init__(self):
        self.prompts = {}

    def register(self, name, version, content):
        self.prompts[(name, version)] = content
