
# Integrated Execution Engine
class ExecutionEngine:
    def __init__(self):
        self.positions = []

    def process_signals(self, signals):
        created=[]
        for s in signals:
            if s.get("action")=="enter":
                pos={
                    "symbol":s.get("symbol"),
                    "entry":s.get("entry"),
                    "status":"open"
                }
                self.positions.append(pos)
                created.append(pos)
        return created

    def get_positions(self):
        return self.positions
