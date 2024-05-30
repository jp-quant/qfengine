import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import APIError
import os, os.path
import pandas as pd
import numpy as np
import datetime
from tqdm.auto import tqdm
from copy import deepcopy
import concurrent.futures
from qfengine import settings

#--------------| <-ALPACA API-> |
class Alpaca(object):
    name = 'Alpaca'
    website_url = 'https://alpaca.markets/'
    api_endpoint_url = 'https://paper-api.alpaca.markets'
    api_key_id = settings.API['Alpaca']['id']
    api_key = settings.API['Alpaca']['key']
    (os.environ["ALPACA_ID"],
    os.environ["ALPACA_KEY"]) = api_key_id,api_key
    def __init__(self):
        #-----FIXED----#
        self._path = os.path.dirname(os.path.realpath(__file__))
        self._dbPath = {
                        "1D":os.path.join(self._path,"1D"),
                        "1Min":os.path.join(self._path,"1Min")
                        }
        base_url = Alpaca.api_endpoint_url if Alpaca.api_key_id.startswith("PK") else 'https://api.alpaca.markets'
        self._REST = tradeapi.REST(Alpaca.api_key_id,Alpaca.api_key,base_url)
        self._StreamConn = tradeapi.StreamConn(Alpaca.api_key_id,Alpaca.api_key,base_url)
    
    def get_barset(self,symbols,timeframe,start_date=None,end_date=None):
        if start_date is not None:
            start_ = str(pd.Timestamp(start_date).date())+"T00:00:00.000Z"
        else:
            start_ = (
                        "2001-01-01T00:00:00.000Z" if (timeframe == '1D') 
                            else (
                                str(pd.Timestamp.now(tz='America/New_York').floor('1min').year)+"-01-01T00:00:00.000Z"
                            )
                        )
        if end_date is not None:
            try:
                end_ = str(pd.Timestamp(end_date).date()) + "T00:00:00.000Z"
            except:
                end_ = None
        else:
            end_ = None

        df = self._REST.get_barset(symbols,timeframe,start=start_,end=end_).df
        df.index = pd.DatetimeIndex(df.index.date)
        df.columns.names = ('symbols','columns')
        
        return df
        
        ''' Archived Method
        def _get_barset(symbol:str,
                        timeframe:str,
                        start_date=None,
                        end_date=None,
                        bars_ago:int=None
        ): # < live data output>--> DataFrame>
            conn = tradeapi.REST(Alpaca.api_key_id,
                                Alpaca.api_key,
                                ("https://paper-api.alpaca.markets" if Alpaca.api_key_id.startswith("PK") else None)
                                )
            if start_date is not None:
                start_ = str(pd.Timestamp(start_date).date())+"T00:00:00.000Z"
            else:
                start_ = (
                            "2001-01-01T00:00:00.000Z" if (timeframe == '1D') 
                                else (
                                    str(pd.Timestamp.now(tz='America/New_York').floor('1min').year)+"-01-01T00:00:00.000Z"
                                )
                            )
            if end_date is not None:
                try:
                    end_ = str(pd.Timestamp(end_date).date()) + "T00:00:00.000Z"
                except:
                    end_ = None
            else:
                end_ = None

            new_data = conn.get_barset(symbol,timeframe,start=start_)[symbol]
            stamps = []
            opens  = []
            closes = []
            highs = []
            lows = []
            volumes = []
            for bar in new_data:
                stamps.append(str(datetime.datetime.strftime(bar.t,'%Y-%m-%d %H:%M:%S')))
                opens.append(bar.o)
                closes.append(bar.c)
                highs.append(bar.h)
                lows.append(bar.l)
                volumes.append(bar.v)
            stamps = np.array(stamps)
            opens = np.array(opens,dtype=np.float64)
            closes = np.array(closes,dtype=np.float64)
            highs = np.array(highs,dtype=np.float64)
            lows = np.array(lows,dtype=np.float64)
            volumes = np.array(volumes,dtype=np.float64)

            result = pd.DataFrame()
            result['open'] = pd.Series(data = opens,index=stamps)
            result['high'] = pd.Series(data=highs,index=stamps)
            result['low'] = pd.Series(data=lows,index=stamps)
            result['close'] = pd.Series(data=closes,index=stamps)
            result['volume'] = pd.Series(data=volumes,index=stamps)

            result.index = pd.DatetimeIndex(result.index)
            if start_date is not None:
                result = result[result.index >= pd.Timestamp(start_date)]
            if end_date is not None:
                result = result[result.index <= pd.Timestamp(end_)]

            return result

        if isinstance(symbols,str):
            result = _get_barset(symbols,timeframe,start_date,end_date)
        else: #---| parallelizing staticmethod calls and concat to return multiIndexed Dataframe
            pool = concurrent.futures.ProcessPoolExecutor()
            iterables = ((s, timeframe, start_date, end_date,None)
                        for s in symbols)
            iterables = zip(*iterables)
            barsets = pool.map(_get_barset, *iterables)
            #_raw = list(barsets)
            #_concat = pd.concat(_raw,axis=1)
            _toConcat = []
            multi_cols = [[],[]]
            for s,df in zip(symbols,list(barsets)):
                multi_cols[0] += [s for _ in range(df.shape[1])]
                multi_cols[1] += list(df.columns)
                _toConcat.append(df)
            multi_cols = [np.array(c) for c in multi_cols]
            _concat = pd.concat(_toConcat,axis=1)
            result = pd.DataFrame(
                                data = _concat.values,
                                index = _concat.index,
                                columns = multi_cols
                                )
        return result
        '''
            

        
    
    def get_account(self):
        return self._REST.get_account()

    def companyInfomation(self,symbol):
        return self._REST.polygon.company(symbol)
    
    def list_positions(self):
        return self._REST.list_positions()

    def list_orders(self,status=None):
        return self._REST.list_orders() if status is None else [o for o in self._REST.list_orders() if o.status == status]
    
    def get_position(self,symbol):
        try:
            return self._REST.get_position(symbol)
        except Exception:
            return None
   
    def submit_order(self, symbol, qty, side, order_type, time_in_force,
                     limit_price=None, stop_price=None, client_order_id=None,
                     extended_hours=None):
        try:
            return self._REST.submit_order(symbol,qty,side,order_type,time_in_force)
        except APIError as e:
            return e
    
    def cancel_order(self,order_id):
        self._REST.cancel_order(order_id)
    
    def cancel_all_orders(self):
        self._REST.cancel_all_orders()
    
    def ts(self,string=False):
        ts = pd.Timestamp.now(tz='America/New_York').floor('1min')
        return ts if not string else str(ts)

    def marketOpen(self):
        now = self.ts()
        return ((now >= now.replace(hour=9, minute=30)) and (now <= now.replace(hour=15,minute=59)))
    
    def last_daily_close(self,symbol):
        return self.get_barset(symbol,"1D",5).iloc[-1].close

    #------OTHERS
    def get_account_configurations(self):
        return self._REST.get_account_configurations()
    
    def get_clock(self):
        return self._REST.get_clock()
    

