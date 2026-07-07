"""Production persistence layer abstraction."""

class Repository:
    def save(self, entity):
        return entity
