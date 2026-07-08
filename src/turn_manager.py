from typing import List, Dict, Any

class TurnManager:
    def __init__(self):
        self.history: List[Dict[str, str]] = []

    def add_turn(self, user_msg: str, assistant_msg: str):
        self.history.append({"role": "user", "content": user_msg})
        self.history.append({"role": "assistant", "content": assistant_msg})

    def get_full_context(self) -> str:
        """
        Returns the concatenated conversation history as a string.
        """
        context = ""
        for turn in self.history:
            role = turn["role"].upper()
            content = turn["content"]
            context += f"{role}: {content}\n\n"
        return context

    def clear(self):
        self.history = []

    def simulate_turns(self, turns: List[Dict[str, str]]):
        """
        Turns should be a list of pairs: [{'user': '...', 'assistant': '...'}, ...]
        """
        for t in turns:
            self.add_turn(t['user'], t['assistant'])
