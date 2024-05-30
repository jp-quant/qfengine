from qfengine.data.price.price_handler import PriceHandler
from qfengine.asset.universe.static import StaticUniverse
import functools
from qfengine import settings
import numpy as np
import pandas as pd
import pytz
from typing import List


class BacktestPriceHandler(PriceHandler):

    def __init__(
        self,
        price_data_sources:List,
        universe = None,
        **kwargs
    ):
        super().__init__(price_data_sources = price_data_sources,
                         universe = universe,
                         **kwargs
                         )
        self._assets_bid_ask_frames = {}
        if self.universe is None:
            self.universe = StaticUniverse(self.assetsList(**kwargs))
            if settings.PRINT_EVENTS:
                print(
                    'PriceHandler Defaulted Universe: %s' %self.universe
                    )

        if 'preload_bid_ask_data' in kwargs:
            if kwargs['preload_bid_ask_data']:
                if settings.PRINT_EVENTS:
                    print("Preloading bid_ask data of assets in universe")
                (self._get_bid_ask_df(s) for s in universe.get_assets())

    def assetsDF(self, **kwargs):
        df = pd.DataFrame()
        for ds in self.price_data_sources:
            new_df = ds.assetsDF(**kwargs)
            df = df.append(new_df.reindex([i for i in new_df.index if i not in df.index]))
        if self.universe:
            df = df.reindex([i for i in df.index if i in self.universe.get_assets()])
        return df

    def assetsList(self, **kwargs):
        return list(self.assetsDF(**kwargs).index.values)

    def sectorsList(self):
        result = []
        for ds in self.price_data_sources:
            result = result + [s for s in ds.sectorsList if s not in result]
        return result        

    def get_assets_earliest_available_dt(self, asset_symbols:List[str]):
        dt_range_df = self._get_dt_range_df(asset_symbols)
        return self._format_dt(max(dt_range_df.start_dt.values))

    def get_assets_latest_available_dt(self, asset_symbols:List[str]):
        dt_range_df = self._get_dt_range_df(asset_symbols)
        return self._format_dt(min(dt_range_df.end_dt.values))


    #!---| Bid & Ask Functions |---!#
    @functools.lru_cache(maxsize = 1024 * 1024)
    def get_asset_latest_bid_price(self, dt, asset_symbol):
        # TODO: Check for asset in Universe
        bid_ask_df = self._get_bid_ask_df(asset_symbol)
        bid = np.NaN
        try:
            bid = bid_ask_df.iloc[bid_ask_df.index.get_loc(dt, method='pad')]['bid']
        except KeyError:  # Before start date
            pass
        return bid

    @functools.lru_cache(maxsize = 1024 * 1024)
    def get_asset_latest_ask_price(self, dt, asset_symbol):
        """
        """
        # TODO: Check for asset in Universe
        bid_ask_df = self._get_bid_ask_df(asset_symbol)
        ask = np.NaN
        try:
            ask = bid_ask_df.iloc[bid_ask_df.index.get_loc(dt, method='pad')]['ask']
        except KeyError:  # Before start date
            pass
        return ask

    def get_asset_latest_bid_ask_price(self, dt, asset_symbol):
        """
        """
        # TODO: For the moment this is sufficient for OHLCV
        # data, which only usually provides mid prices
        # This will need to be revisited when handling intraday
        # bid/ask time series.
        # It has been added as an optimisation mechanism for
        # interday backtests.
        bid = self.get_asset_latest_bid_price(dt, asset_symbol)
        return (bid, bid)

    def get_asset_latest_mid_price(self, dt, asset_symbol):
        """
        """
        bid_ask = self.get_asset_latest_bid_ask_price(dt, asset_symbol)
        try:
            mid = (bid_ask[0] + bid_ask[1]) / 2.0
        except Exception:
            # TODO: Log this
            mid = np.NaN
        return mid

    #!---| Daily Price (OHLCV) Functions |---!#
    def get_assets_historical_closes(self,
                                     asset_symbols:List[str],
                                     start_dt = None,
                                     end_dt = None,
                                     adjusted=False
    ):
        """
        """
        prices_df = None

        for ds in self.price_data_sources:
            try:
                prices_df = ds.get_assets_historical_price_dfs(
                    *asset_symbols,
                    start_dt=start_dt,
                    end_dt = end_dt,
                    price = 'close',
                    adjusted=adjusted
                ).sort_index()
                if not prices_df.empty:
                    break
            except Exception:
                raise

        
        if prices_df is None:
            return pd.DataFrame(columns = asset_symbols)
        else:
            assert len(asset_symbols) == prices_df.shape[1]
            if start_dt is not None:
                prices_df = prices_df[prices_df.index >= self._format_dt(start_dt)]
            if end_dt is not None:
                prices_df = prices_df[prices_df.index <= self._format_dt(end_dt)]
                market_close_dt = self._convert_dt_to_date(end_dt) + pd.Timedelta(hours=16, minutes=00)
                if self._format_dt(end_dt) < market_close_dt: #---| rid of last index if market is not close yet
                    prices_df = prices_df.iloc[:-1]
            return prices_df
    
    def get_assets_historical_opens(self,
                                     asset_symbols:List[str],
                                     start_dt = None,
                                     end_dt = None,
                                     adjusted=False
    ):
        """
        """
        prices_df = None
        for ds in self.price_data_sources:
            try:
                prices_df = ds.get_assets_historical_price_dfs(
                    *asset_symbols,
                    start_dt = start_dt,
                    end_dt = end_dt,
                    price = 'open',
                    adjusted=adjusted
                ).sort_index()
                if not prices_df.empty:
                   break
            except Exception:
                raise
        if prices_df is None:
            return pd.DataFrame(columns = asset_symbols)
        else:
            assert len(asset_symbols) == prices_df.shape[1]
            if start_dt is not None:
                prices_df = prices_df[prices_df.index >= self._format_dt(start_dt)]
            if end_dt is not None:
                prices_df = prices_df[prices_df.index <= self._format_dt(end_dt)]
                market_open_dt = self._convert_dt_to_date(end_dt) + pd.Timedelta(hours=9, minutes=30)
                if self._format_dt(end_dt) < market_open_dt:
                    prices_df = prices_df.iloc[:-1]
            return prices_df
    
    def get_assets_historical_highs(self,
                                     asset_symbols:List[str],
                                     start_dt = None,
                                     end_dt = None,
                                     adjusted=False
    ):
        """
        """
        prices_df = None
        for ds in self.price_data_sources:
            try:
                prices_df = ds.get_assets_historical_price_dfs(
                    *asset_symbols,
                    start_dt=start_dt,
                    end_dt = end_dt,
                    price = 'high',
                    adjusted=adjusted
                ).sort_index()
                if not prices_df.empty:
                   break
            except Exception:
                raise
        if prices_df is None:
            return pd.DataFrame(columns = asset_symbols)
        else:
            assert len(asset_symbols) == prices_df.shape[1]
            if start_dt is not None:
                prices_df = prices_df[prices_df.index >= self._format_dt(start_dt)]
            if end_dt is not None:
                prices_df = prices_df[prices_df.index <= self._format_dt(end_dt)]
                market_close_dt = self._convert_dt_to_date(end_dt) + pd.Timedelta(hours=16, minutes=00)
                if self._format_dt(end_dt) < market_close_dt: #---| rid of last index if market is not close yet
                    prices_df = prices_df.iloc[:-1]
            return prices_df
    
    def get_assets_historical_lows(self,
                                     asset_symbols:List[str],
                                     start_dt = None,
                                     end_dt = None,
                                     adjusted=False
    ):
        """
        """
        prices_df = None
        for ds in self.price_data_sources:
            try:
                prices_df = ds.get_assets_historical_price_dfs(
                    *asset_symbols,
                    start_dt=start_dt,
                    end_dt = end_dt,
                    price = 'low',
                    adjusted=adjusted
                ).sort_index()
                if not prices_df.empty:
                   break
            except Exception:
                raise
        if prices_df is None:
            return pd.DataFrame(columns = asset_symbols)
        else:
            assert len(asset_symbols) == prices_df.shape[1]
            if start_dt is not None:
                prices_df = prices_df[prices_df.index >= self._format_dt(start_dt)]
            if end_dt is not None:
                prices_df = prices_df[prices_df.index <= self._format_dt(end_dt)]
                market_close_dt = self._convert_dt_to_date(end_dt) + pd.Timedelta(hours=16, minutes=00)
                if self._format_dt(end_dt) < market_close_dt: #---| rid of last index if market is not close yet
                    prices_df = prices_df.iloc[:-1]
            return prices_df
    
    def get_assets_historical_volumes(self,
                                     asset_symbols:List[str],
                                     start_dt = None,
                                     end_dt = None,
                                     adjusted=False
    ):
        """
        """
        prices_df = None
        for ds in self.price_data_sources:
            try:
                prices_df = ds.get_assets_historical_price_dfs(
                    *asset_symbols,
                    start_dt=start_dt,
                    end_dt = end_dt,
                    price = 'volume',
                    adjusted=adjusted
                ).sort_index()
                if not prices_df.empty:
                   break
            except Exception:
                raise
        if prices_df is None:
            return pd.DataFrame(columns = asset_symbols)
        else:
            assert len(asset_symbols) == prices_df.shape[1]
            if start_dt is not None:
                prices_df = prices_df[prices_df.index >= self._format_dt(start_dt)]
            if end_dt is not None:
                prices_df = prices_df[prices_df.index <= self._format_dt(end_dt)]
                market_close_dt = self._convert_dt_to_date(end_dt) + pd.Timedelta(hours=16, minutes=00)
                if self._format_dt(end_dt) < market_close_dt: #---| rid of last index if market is not close yet
                    prices_df = prices_df.iloc[:-1]
            return prices_df


    #!---| BACKEND FUNCS
    def _reset_cached_frames(self):
        self._assets_bid_ask_frames = {}

    def _convert_dt_to_date(self, dt):
        return pd.Timestamp(
                self._format_dt(dt).date(),
                tz = settings.TIMEZONE
                        )

    def _format_dt(self, dt):
      try:
        return pd.Timestamp(dt).tz_convert(settings.TIMEZONE)
      except TypeError:
        try:
          return pd.Timestamp(dt).tz_localize(settings.TIMEZONE)
        except:
          raise

    def _get_bid_ask_df(self, asset_symbol):
        if asset_symbol not in self._assets_bid_ask_frames:
            for ds in self.price_data_sources:
                try:
                    self._assets_bid_ask_frames[
                                        asset_symbol
                                               ] = ds.get_assets_bid_ask_dfs(
                                                                    asset_symbol
                                                                            )[asset_symbol]
                    break
                except:
                    pass
            assert asset_symbol in self._assets_bid_ask_frames
        return self._assets_bid_ask_frames[asset_symbol]

    def _get_dt_range_df(self, asset_symbols:List[str]):
        symbols = asset_symbols
        result_df = pd.DataFrame()
        for ds in self.price_data_sources:
            df = ds.get_assets_price_date_ranges_df(*symbols)
            result_df = result_df.append(
                                    df.where(pd.notna(df), np.nan).dropna()
                                            )
            symbols = [s for s in symbols if s not in result_df.index]
            if len(symbols) == 0:
                break

        return result_df
