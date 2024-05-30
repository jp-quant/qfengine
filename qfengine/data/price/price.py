from qfengine.data.data import TimeSeriesData
from qfengine.asset import assetClasses
from abc import ABCMeta, abstractmethod
import pandas as pd



class Price(TimeSeriesData):

    def __init__(self,
                 asset:assetClasses,
                 dt:pd.Timestamp,
                    openPrice:float = None,
                    highPrice:float = None,
                    lowPrice:float = None,
                    closePrice:float = None,
                    volume:int = None,

    ):
        super().__init__(dt)
        self.asset = asset
        self.openPrice = openPrice
        self.highPrice = highPrice
        self.lowPrice = lowPrice
        self.closePrice = closePrice
        self.volume = volume
    
