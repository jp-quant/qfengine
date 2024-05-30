from abc import ABCMeta, abstractmethod
from qfengine.data.data_source import CSVDataSource, MySQLDataSource
from qfengine import settings
from typing import List,Dict
import pandas as pd
import os


class PriceDataSource(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def get_assets_historical_price_dfs(self, assets, start_dt=None, end_dt=None, price=None)->pd.DataFrame:
        raise NotImplementedError("Should implement get_assets_historical_price_dfs()")

    @abstractmethod
    def get_assets_bid_ask_dfs(self, assets, start_dt=None, end_dt=None, price=None)->pd.DataFrame:
        raise NotImplementedError("Should implement get_assets_bid_ask_dfs()")

    @abstractmethod
    def assetsDF(self, **kwargs)->pd.DataFrame:
        raise NotImplementedError("Should implement assetsDF()")
    
    @abstractmethod
    def assetsList(self, **kwargs)->list:
        raise NotImplementedError("Should implement assetsList()")
    
    @abstractmethod
    def create_price_source_copy(self):
        raise NotImplementedError("Should implement create_price_source_copy()")




class CSVPriceDataSource(CSVDataSource,PriceDataSource):

    __metaclass__ = ABCMeta

    def __init__(self,
                 csv_dir:str,
                 csv_symbols:List[str] = None,
    ):       
        super().__init__(csv_dir)
        available_csv_symbols = [self._symbol_from_csv_file(f) for f in self._csv_files_in_dir]
        if csv_symbols is not None:
            available_csv_symbols = [s for s in available_csv_symbols if s in csv_symbols]
            if len(csv_symbols) > len(available_csv_symbols) > 0:
                print("Omitting following symbols that do not exist in csv_dir:")
                print([s for s in csv_symbols if s not in available_csv_symbols])
        assert len(available_csv_symbols) > 0, "No symbols (assigned or not) is available in csv_dir: %s" %self.csv_dir
        self.symbols_list = available_csv_symbols
    
    def _symbol_from_csv_file(self, csv_file:str):
        assert csv_file.endswith('.csv')
        return csv_file.replace('.csv', '')
    
    def _csv_file_from_symbol(self, symbol:str):
        assert not symbol.endswith('.csv')
        return symbol +'.csv'  

class MySQLPriceDataSource(MySQLDataSource, PriceDataSource):

    __metaclass__ = ABCMeta

    def __init__(self,
                 db_credentials:Dict,
                 price_table_name:str,
                 price_table_schema = None,
                 **kwargs,
    ):
        assert set(db_credentials.keys()).issubset(set(['user','passwd','host','db']))
        self._db_credentials = db_credentials
        self._full_credentials = db_credentials.copy()
        self._full_credentials['table_name'] = price_table_name
        self._full_credentials['schema'] = price_table_schema

        init_params = self._full_credentials.copy()
        for p,v in kwargs.items():
            init_params[p] = v
        super().__init__(**init_params)
