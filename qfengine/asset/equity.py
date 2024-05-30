from qfengine.asset.asset import Asset

class Equity(Asset):



    def __init__(
                 self,
                 symbol:str,
                 name:str = None,
                 sector:str = None,
                 industry:str = None,
                 figi:str = None,
    ):
        super().__init__(cash_like=False)
        self.symbol = symbol
        self.name = name
        self.sector = sector
        self.industry =industry
        self.figi = figi

    
    def __repr__(self):
        return (
            "Equity(symbol='%s', name='%s')" %(self.symbol, str(self.name))
               )
