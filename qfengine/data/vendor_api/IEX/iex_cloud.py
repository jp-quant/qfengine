import os, os.path
import pandas as pd
import numpy as np
import datetime
import logging
import time
import pyEX as api
from qfengine import settings
logger = logging.getLogger(__name__)



#--------------| <-IEX Cloud API-> Private Paid Key (keep private duh)
class IEX(object):
#------------------------#
    name = 'IEX'
    website_url = 'https://iexcloud.io/'
    api_endpoint_url = 'https://cloud.iexapis.com/'
    api_key = settings.API['IEX']['key']
    os.environ["IEX_TOKEN"] = api_key
    # api_key = open(os.path.join(os.path.dirname(os.path.realpath(__file__)),"api_key.txt")).read().split("\n")[0]
    
    def __init__(self):
        self._client = api.Client(self.api_key,version=('sandbox' if self.api_key.startswith("T") else 'v1'))
        self._availableDFs = [(f[:-2]) for f in dir(self._client) if f.endswith("DF")]
        self._availableLists = [(f[:-2]) for f in dir(self._client) if f.endswith("List")]
    
    def get_DF(self,df:str,iex_kwargs:dict=None):
        assert df in self._availableDFs
        if iex_kwargs is None:
            iex_kwargs = {}
        return getattr(self._client,(df+"DF"))(**iex_kwargs)
    

    def symbolsDF(self,
                    issue_type:list=None,
                    include_company_info:bool=False,
                    ):
        '''
        AD - ADR
        RE - REIT
        CE - Closed end fund
        SI - Secondary Issue
        LP - Limited Partnerships
        CS - Common Stock
        ET - ETF
        WT - Warrant
        OEF - Open Ended Fund
        CEF - Closed Ended Fund
        PS - Preferred Stock
        '''
        _syms = self._client.symbolsDF()
        _syms.index.name = 'symbol'
        if issue_type is not None:
            assert set(issue_type).issubset(set(_syms.type.unique())), str(_syms.type.unique())
            syms = pd.DataFrame()
            for i in issue_type:
                syms = syms.append(_syms[_syms['type'] == i])
        else:
            syms = _syms
        syms = syms.reset_index().reindex(syms.reset_index()['symbol'].drop_duplicates().index)
        syms = syms.set_index('symbol').reset_index()
        syms = syms[['symbol','name','region','exchange','currency','type','figi']]
        return syms


    def exchangesDF(self,include_international:bool=True):
        us = self._client.exchangesDF()
        us = us[['refId','longName']]
        us.columns = ['ref_id','name']
        result = us
        if include_international:
            international = self._client.internationalExchangesDF()
            international = international[['exchange','description']]
            international.columns = ['ref_id','name']
            result = result.append(international)
        result = result.set_index("ref_id")
        result = result.reset_index().reindex(result.reset_index()['ref_id'].drop_duplicates().index)
        result = result.set_index("ref_id").reset_index()
        return result
    
    def get_barset(self,symbols,
                        timeframe=None,
                        start_date=None,
                        end_date=None
    ):
        if isinstance(symbols,str):
            symbols = [symbols]
        end_ = IEX._prepare_date_format(end_date)
        start_ = IEX._prepare_date_format(start_date)
        assert start_ is not None
        range_ = None
        if start_ is not None:
            for r in ['30d','90d','180d','1y','2y','5y']:
                if (pd.Timestamp.now() - pd.Timestamp(start_)) < pd.Timedelta(r):
                    range_ = r
                    break
        
        if range_ is None:
            range_ = 'max'
        elif range_ == '30d':
            range_ = '1m'
        elif range_ == '90d':
            range_ = '3m'
        elif range_ == '180d':
            range_ = '6m'

        barsets = []
        for s in symbols:
            _df = self._client.chartDF(s,range_)[['open','high','low','close','volume']]
            _df.index = pd.DatetimeIndex(_df.index)
            barsets.append(_df)
        multi_cols = [[],[]]
        for s,_df in zip(symbols,barsets):
            multi_cols[0] += [s for _ in range(_df.shape[1])]
            multi_cols[1] += list(_df.columns)
        _concat = pd.concat(barsets,axis=1)
        
        final_df = pd.DataFrame(
            data=_concat.values,
            index = _concat.index,
            columns = multi_cols
        )
        final_df.columns.names = ('symbols','columns')
        return final_df
        
#----------------------------------| static functions (parallelizable)

    @staticmethod
    def _prepare_date_format(datestamp): #need to be in datetime.date
        try:
            d = pd.Timestamp(datestamp).date() # Works most cases
            return d
        except:
            try:
                d = datestamp.date()
                return d
            except:
                return None
            


class IEXSandbox(IEX):
    name = 'IEXSandbox'
    website_url = 'https://iexcloud.io/'
    api_endpoint_url = 'https://sandbox.iexapis.com'
    api_key = settings.API['IEXSandbox']['key']
    # api_key = open(os.path.join(os.path.dirname(os.path.realpath(__file__)),"api_key.txt")).read().split("\n")[0]
    
    def __init__(self):
        super().__init__()
    
