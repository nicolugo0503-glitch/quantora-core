
# QNT30484 - Fund Stack + Sleeve System

from typing import List, Dict

class Fund:
    def __init__(self, id, name, base_currency="USD"):
        self.id = id
        self.name = name
        self.base_currency = base_currency

class Sleeve:
    def __init__(self, id, fund_id, name, target_pct):
        self.id = id
        self.fund_id = fund_id
        self.name = name
        self.target_pct = target_pct

class SleeveStrategy:
    def __init__(self, sleeve_id, strategy_id, weight):
        self.sleeve_id = sleeve_id
        self.strategy_id = strategy_id
        self.weight = weight

class FundEngine:

    def __init__(self):
        self.funds: Dict[str, Fund] = {}
        self.sleeves: List[Sleeve] = []
        self.mappings: List[SleeveStrategy] = []

    def create_fund(self, id, name):
        self.funds[id] = Fund(id, name)

    def add_sleeve(self, sleeve: Sleeve):
        self.sleeves.append(sleeve)

    def map_strategy(self, mapping: SleeveStrategy):
        self.mappings.append(mapping)

    def allocate(self, fund_id, capital):
        result = {}
        sleeves = [s for s in self.sleeves if s.fund_id == fund_id]
        for s in sleeves:
            result[s.name] = capital * (s.target_pct / 100)
        return result
