"""
AI PMO Copilot AI Core - Prompt Manager
"""

class PromptManager:
    def __init__(self):
        self.prompts = {}

    def register(self, name, content):
        self.prompts[name] = content

    def get(self, name):
        return self.prompts.get(name)
