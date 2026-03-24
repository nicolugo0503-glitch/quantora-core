
# Trade Lifecycle Engine
class TradeLifecycle:
    def __init__(self):
        self.positions=[]

    def open_position(self, pos):
        pos["pnl"]=0
        pos["status"]="open"
        self.positions.append(pos)

    def update_position(self, pos, price):
        entry=pos.get("entry",0)
        pos["pnl"]=price-entry

    def close_position(self, pos):
        pos["status"]="closed"

    def get_positions(self):
        return self.positions
