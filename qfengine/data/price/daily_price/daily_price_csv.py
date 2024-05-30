from qfengine.data.price.price_source import CSVPriceDataSource
from qfengine.asset import assetClasses
from qfengine import settings
from typing import Union, List

import pandas as pd
import numpy as np
import os
import functools
import concurrent.futures


class DailyPriceCSV(CSVPriceDataSource):

    def __init__(
                 self,
                 asset_type:assetClasses,
                 csv_dir:str = None,
                 symbols_list:List[str] = None,
                    min_start_date = None,
                    init_to_latest:bool = True,
                    adjust_prices:bool = False,
    ):
        csv_dir = csv_dir or settings.CSV_DIRECTORIES['PRICE']['DAILY']
        super().__init__(csv_dir, symbols_list)
        self.asset_type = asset_type
        self.adjust_prices = adjust_prices
        self.min_start_date = min_start_date

    def create_price_source_copy(self):
        copy = DailyPriceCSV(
                        asset_type = self.asset_type,
                        csv_dir = self.csv_dir,
        )
        copy.symbols_list = self.symbols_list #---| skip symbols vetting for CSV data
        return copy
        
   #!--| MAIN FUNCS (ABSTRACT)
    def assetsDF(self,**kwargs):
        return pd.DataFrame(
          {
            'symbol':pd.Series(data=self.symbols_list)
          }
                  ).set_index('symbol')

    def assetsList(self,**kwargs):
        return self.symbols_list.copy()

    @property
    def sectorsList(self):
      return []


    def get_assets_bid_ask_dfs(self,
                               asset:str,
                               *assets:str,
                                  start_dt=None,   
                                  end_dt=None,
                                  **kwargs
    )->pd.DataFrame:
      return self._price_dfs_to_bid_ask_dfs(
                      self.get_assets_historical_price_dfs(asset,
                                                            *assets,
                                                            start_dt = start_dt,
                                                            end_dt = end_dt
                                                        )
      )

    def get_assets_historical_price_dfs(self,
                                        asset:str,
                                        *assets:str,
                                            price:str = None,
                                            start_dt = None,
                                            end_dt = None,
                                              adjusted = None,
                                              **kwargs
    )->pd.DataFrame:
        if price:
            assert price in [
                  "open", "high", "low",
                  "close","volume"
                          ]
        symbols = [asset] + [s for s in assets]
        #--| parallelizing csv readings for performance
        result = self._assets_daily_price_DF(*symbols)

        if price:
          result = result[
                  [col for col in result.columns if price in col]
                      ]
          result.columns = result.columns.get_level_values('symbols')
        
        if start_dt:
          result = result[result.index >= self._format_dt(start_dt)]
        if end_dt:
          result = result[result.index <= self._format_dt(end_dt)]

        return result
    


    #----| Price Date Ranges
    def get_assets_minimum_start_dt(self,
                                        asset:str,
                                        *assets:str,
    )->pd.Timestamp:
        return self._format_dt(max(
          self.get_assets_price_date_ranges_df(
                            asset, *assets
                                            ).start_dt.values
                 ))

    def get_assets_maximum_end_dt(self,
                                      asset:str,
                                      *assets:str,
    )->pd.Timestamp:
        return self._format_dt(min(
          self.get_assets_price_date_ranges_df(
                            asset, *assets
                                            ).end_dt.values
                 ))
                
    @functools.lru_cache(maxsize = 1024 * 1024)
    def get_assets_price_date_ranges_df(self,
                                        asset:str,
                                        *assets:str,
    )->pd.DataFrame:

        symbols = [asset] + [s for s in assets]
        if self.symbols_list:
          assert set(symbols).issubset(self.symbols_list)
        
        def _get_result(source, symbol):
          return {
              'symbol': symbol,
              'start_dt': self._format_dt(source._asset_symbol_min_price_date(symbol)),
              'end_dt': self._format_dt(source._asset_symbol_max_price_date(symbol)),
                }
        final_df = pd.DataFrame.from_dict(
                                list(
                                  concurrent.futures.ThreadPoolExecutor().map(
                                                                          _get_result, 
                                                                          *zip(*(
                                                                            (
                                                                              self.create_price_source_copy(),
                                                                              symbol,
                                                                            ) for symbol in symbols
                                                                                ))
                                                                              )
                                    )
                                          ).set_index('symbol').dropna()
        return final_df
    #---------------------------|


   #!---------------------------------|



   #!----| BACKEND FUNCTIONS 
    @functools.lru_cache(maxsize = 1024 * 1024) 
    def _assets_daily_price_DF(self,
                                asset:str,
                                *assets:str
    ):
        symbols = [asset] + [s for s in assets]
        if self.symbols_list:
          assert set(symbols).issubset(self.symbols_list)
        all_dfs = concurrent.futures.ThreadPoolExecutor().map(
                                        self.__class__._csv_to_df, 
                                        *zip(*(
                                        (
                                            self.create_price_source_copy(),
                                            self._csv_file_from_symbol(symbol),
                                        ) for symbol in symbols
                                            ))
                                                        )
        final_df = pd.concat([
                d.where(pd.notna(d), np.nan) for d in all_dfs if (
                                                not d.where(pd.notna(d), np.nan).dropna().empty
                                                                )
                            ], axis=1)
        final_df.columns.names = ('symbols','columns')
        final_df = final_df.set_index(final_df.index.tz_localize(settings.TIMEZONE))
        final_df = final_df.sort_index()

        missing_symbols = [s for s in symbols if s not in final_df.columns.get_level_values('symbols')]
        if len(missing_symbols) > 0:
          if settings.PRINT_EVENTS:
            print("Warning: Queried Daily Prices DataFrame is missing %s symbols:" %len(missing_symbols))
            print(missing_symbols)
        return final_df

    def _csv_to_df(self, csv_file:str):
        assert csv_file.endswith('.csv')
        df = pd.io.parsers.read_csv(
                                    os.path.join(self.csv_dir, csv_file),
                                    header=0, index_col=0, 
                                    names=['datetime','open','low','high','close','volume']
                                   )
        df.index = pd.DatetimeIndex(df.index)
        for c in df.columns:
            df[c] = pd.to_numeric(df[c])
        asset = self._symbol_from_csv_file(csv_file)
        df.columns = [
              np.array([asset for _ in df.columns]),
              np.array(df.columns)
             ]
        return df
        
    def _format_dt(self, dt):
      try:
        return pd.Timestamp(dt).tz_convert(settings.TIMEZONE)
      except TypeError:
        try:
          return pd.Timestamp(dt).tz_localize(settings.TIMEZONE)
        except:
          raise

    def _price_dfs_to_bid_ask_dfs(self, 
                                  price_df:pd.DataFrame
    ):
        def _symbol_price_to_bid_ask(bar_df, symbol):
          cols = [
                np.array([symbol, symbol]),
                np.array(['bid', 'ask'])
                ]
          if bar_df.dropna().empty:
            return pd.DataFrame(columns = cols)
          bar_df = bar_df.sort_index()
          oc_df = bar_df.loc[:, ['open', 'close']]
          oc_df['pre_market'] = oc_df['close'].shift(1)
          oc_df['post_market'] = oc_df['close']
          oc_df = oc_df.dropna()
          # Convert bars into separate rows for open/close prices
          # appropriately timestamped
          seq_oc_df = oc_df.T.unstack(level=0).reset_index()
          seq_oc_df.columns = ['datetime', 'market', 'price']

          seq_oc_df.loc[seq_oc_df['market'] == 'open', 'datetime'] += pd.Timedelta(hours=9, minutes=30)
          seq_oc_df.loc[seq_oc_df['market'] == 'close', 'datetime'] += pd.Timedelta(hours=16, minutes=00)
          seq_oc_df.loc[seq_oc_df['market'] == 'pre_market', 'datetime'] += pd.Timedelta(hours=0, minutes=00)
          seq_oc_df.loc[seq_oc_df['market'] == 'post_market', 'datetime'] += pd.Timedelta(hours=23, minutes=59)

          # TODO: Unable to distinguish between Bid/Ask, implement later
          dp_df = seq_oc_df[['datetime', 'price']]
          dp_df['bid'] = dp_df['price']
          dp_df['ask'] = dp_df['price']
          dp_df = dp_df.loc[:, ['datetime', 'bid', 'ask']].fillna(method='ffill').set_index('datetime').sort_index()
          dp_df.columns = cols
          return dp_df 
        
        bid_ask_df = pd.concat(
                      [
                        _symbol_price_to_bid_ask(price_df[symbol], symbol) 
                          for symbol in price_df.columns.get_level_values('symbols').unique()
                      ], axis = 1
                    )
        bid_ask_df.columns.names = ('symbols', 'columns') 

        return bid_ask_df

    def _asset_symbol_min_price_date(self, symbol):
        df = self._csv_to_df(self._csv_file_from_symbol(symbol))
        return df.dropna().sort_index().index[1]
    
    def _asset_symbol_max_price_date(self, symbol):
        df = self._csv_to_df(self._csv_file_from_symbol(symbol))
        return df.dropna().sort_index().index[-1]
