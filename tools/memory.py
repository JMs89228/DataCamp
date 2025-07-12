# tools/memory.py
class SimpleMemory:
    def __init__(self):
        self.history = []
        self.context = {}

    def append(self, role, content):
        self.history.append({"role": role, "content": content})

    def update_context(self, key, content):
        self.context[key] = content

    def messages(self):
        messages = []
        for key, content in self.context.items():
            messages.append({"role": "system", "content": f"[{key}]\n{content}"})
        messages.extend(self.history)
        return messages

    def clear(self):
        self.history.clear()
        self.context.clear()
