from qfengine.data.price.price_source import PriceDataSource
from qfengine.data.data_handler import DataHandler
from qfengine.asset.universe.universe import Universe
from abc import ABCMeta, abstractmethod
import pandas as pd


class PriceHandler(DataHandler):

    __metaclass__ = ABCMeta

    def __init__(self,
                 price_data_sources,
                 universe = None,
                 **kwargs
                ):
        try:
            iter(price_data_sources)
        except TypeError:
            price_data_sources = [price_data_sources]
        assert (PriceDataSource in d.__class__.mro() for d in price_data_sources)
        if universe:
            assert Universe in universe.__class__.mro()
        self.universe = universe
        self.price_data_sources = list(price_data_sources)
        # TODO: Add preference source or ordered of calls until fit cond.
    

    @abstractmethod
    def assetsDF(self,*kwargs):
        raise NotImplementedError("Implement assetsDF()")
    
    @abstractmethod
    def assetsList(self, **kwargs):
        raise NotImplementedError("Implement assetsList()")

    #!---| Bid & Ask Functions |---!#
    @abstractmethod
    def get_asset_latest_bid_price(self, dt, asset_symbol)->float:
        raise NotImplementedError("Implement get_asset_latest_bid_price()")

    @abstractmethod
    def get_asset_latest_ask_price(self, dt, asset_symbol)->float:
        raise NotImplementedError("Implement get_asset_latest_ask price()")

    @abstractmethod
    def get_asset_latest_bid_ask_price(self, dt, asset_symbol)->tuple:
        raise NotImplementedError("Implement get_asset_latest_bid_ask_price()")

    @abstractmethod
    def get_asset_latest_mid_price(self, dt, asset_symbol)->float:
        raise NotImplementedError("Implement get_asset_latest_mid_price()")



    #!---| Daily Price (OHLCV) Functions |---!#
    @abstractmethod
    def get_assets_historical_opens(self, start_dt, end_dt, asset_symbols, adjusted=False)->pd.DataFrame:
        raise NotImplementedError("Implement get_assets_historical_prices()")

    @abstractmethod
    def get_assets_historical_closes(self, start_dt, end_dt, asset_symbols, adjusted=False)->pd.DataFrame:
        raise NotImplementedError("Implement get_assets_historical_prices()")

    @abstractmethod
    def get_assets_historical_highs(self, start_dt, end_dt, asset_symbols, adjusted=False)->pd.DataFrame:
        raise NotImplementedError("Implement get_assets_historical_prices()")

    @abstractmethod
    def get_assets_historical_lows(self, start_dt, end_dt, asset_symbols, adjusted=False)->pd.DataFrame:
        raise NotImplementedError("Implement get_assets_historical_prices()")

    @abstractmethod
    def get_assets_historical_volumes(self, start_dt, end_dt, asset_symbols, adjusted=False)->pd.DataFrame:
        raise NotImplementedError("Implement get_assets_historical_prices()")
