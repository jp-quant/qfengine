from qfengine.asset.universe.universe import Universe
import pandas as pd

class DynamicUniverse(Universe):


    def __init__(self,
                 assetDictByStamp: dict,
    ):
        "assetDictByStamp : `dict{str: pd.Timestamp}`"

        self.assetDictByStamp = assetDictByStamp
    
    def get_assets(self,dt:pd.Timestamp):
        '''
        Parameters
        ----------
        dt : `pd.Timestamp`
            The timestamp at which to retrieve the Asset list.
        Returns
        -------
        `list[str]`
            The list of Asset symbols in the static Universe.
        """
        '''

        return [a for a,a_dt in self.assetDictByStamp.items()
                if a_dt is not None and dt >= a_dt]