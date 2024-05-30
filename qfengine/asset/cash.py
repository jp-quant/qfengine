from qfengine.asset.asset import Asset

class Cash(Asset):
    '''
    Cash is King
    '''
    def __init__(
                 self,
                 currency:str = 'USD',
    ):
        super().__init__(cash_like=True)
        self.currency = currency

    
    def __repr__(self):
        return (
            "Cash(currency='%s')" %(self.currency)
               )
