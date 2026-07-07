"""Standard AI agent execution contract."""

from abc import ABC, abstractmethod

class Agent(ABC):
    @abstractmethod
    def execute(self, context):
        pass
