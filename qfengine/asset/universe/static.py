from qfengine.asset.universe.universe import Universe
from typing import List
import pandas as pd

class StaticUniverse(Universe):


    def __init__(self,
                 assetList:List[str],
                 **kwargs
    ):
        self.assetList = assetList
        
        self.sector = None
        if 'sector' in kwargs:
            self.sector = str(kwargs['sector'])
    
    def get_assets(self, dt:pd.Timestamp=None):
        return self.assetList.copy()
    

    def __repr__(self):
        _str = "StaticUniverse(n_symbols = %s)"%len(self.assetList)
        if self.sector:
            _str = _str[:-1] + ", sector = %s)" %self.sector
        return _str
