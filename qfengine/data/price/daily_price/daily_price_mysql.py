
from qfengine.data.price.price_source import MySQLPriceDataSource as SQLTable
from qfengine.asset import assetClasses

import pandas as pd
from typing import Union, List, Dict
import os
import numpy as np
import logging
import functools
from qfengine import settings
import concurrent.futures

logger = logging.getLogger(__name__)

# todo: MOVE THESE TO RESPECTIVE DIR MODULE
class DataVendorMySQL(SQLTable):
    create_schema = (
      '''
      CREATE TABLE `%s` (
        `id` int NOT NULL AUTO_INCREMENT,
        `name` varchar(64) NOT NULL,
        `website_url` varchar(255) NULL,
        `api_endpoint_url` varchar(255) NULL,
        `api_key_id` varchar(255) NULL,
        `api_key` varchar(255) NULL,
        `created_date` datetime NULL DEFAULT CURRENT_TIMESTAMP(),
        `last_updated_date` datetime NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP(),
        PRIMARY KEY (`id`)
      ) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8
      '''
    )
    def __init__(
                 self,
                 db_credentials:Dict=None,
                 name:str = 'data_vendor',
                 **kwargs
    ):
      super().__init__(
              (db_credentials if db_credentials is not None
              else settings.MYSQL_CREDENTIALS),
                  name,
                  (DataVendorMySQL.create_schema %name),
                  **kwargs
                       )
    


      from qfengine.data import vendor_api
      import pandas as pd
      #---| init all availables
      _vendorAPIs = {api:getattr(vendor_api,api) for api in vendor_api.__all__}
      currentInfo = []
      _to_pop = []
      for api_name, API in _vendorAPIs.items():
        _i = {'name':api_name}
        for f in self.all_accepted_columns:
            try:
              f_dat = getattr(API,f)
            except:
              pass
            else:
              if callable(f_dat):
                f_dat = f_dat()
              _i[f] = f_dat
        missing_required = [c for c in self.required_columns if c not in _i]
        if len(missing_required) != 0:
          _to_pop.append(api_name)
        else:
          currentInfo.append(_i)  
      currentInfo = pd.DataFrame.from_dict(currentInfo)
      currentInfo = currentInfo.where(pd.notnull(currentInfo),None)
      upserted = self.upsertDF(currentInfo,["name"])
      for p in _to_pop:
        _vendorAPIs.pop(p)
      
      self._APIs = {API.name: API for _,API in _vendorAPIs.items()}
    
      #---| check all init for essential funcs

    def get_vendor_API(self,vendor:str):
      assert vendor in self.List
      return self._APIs[vendor]()

    @property
    def DF(self):
      return self._fullDF().set_index("name").reindex(list(self._APIs.keys()))

    @property
    def List(self):
      return list(self._APIs.keys())


class ExchangeMySQL(SQLTable):
    create_schema = (
      '''
      CREATE TABLE `%s` (
        `id` int NOT NULL AUTO_INCREMENT,
        `ref_id` varchar(32) NOT NULL,
        `name` varchar(255) NOT NULL,
        `currency` varchar(64) NULL,
        `region` varchar(255) NULL,
        `created_date` datetime NULL DEFAULT CURRENT_TIMESTAMP(),
        `last_updated_date` datetime NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP(),
        PRIMARY KEY (`id`)
      ) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8
      '''
    )
    def __init__(
                 self,
                 db_credentials:Dict = None,
                 vendors:DataVendorMySQL = None,
                 name:str = 'exchange',
                 **kwargs
    ):
      super().__init__(
              (db_credentials if db_credentials is not None
              else settings.MYSQL_CREDENTIALS),
                  name,
                    (ExchangeMySQL.create_schema %name),
                    **kwargs
                       )

      self.vendors = vendors or DataVendorMySQL(db_credentials,mdb_conn = self._conn)

    def UPDATE(self, vendor:str = 'IEX', DF:pd.DataFrame=None):
      if DF is None:
        DF = self.vendors.get_vendor_API(vendor).exchangesDF()
      upserted = self.upsertDF(DF,['ref_id'])
      for i,_count in upserted.items():
        if _count > 0:
          logger.warning("%s %s Exchanges" %(str(i).upper(), str(_count)))


    @property
    def DF(self):
      return self._fullDF().set_index("ref_id")

    @property
    def List(self):
      return [e[0] for e in self.executeSQL("select ref_id from %s" %self._name)]

class SecurityMySQL(SQLTable):
    create_schema = (
      '''
      CREATE TABLE `%s` (
        `id` int NOT NULL AUTO_INCREMENT,
        `exchange_id` int NOT NULL,
        `symbol` varchar(10) NOT NULL,
        `type` varchar(10) NULL,
        `name` varchar(255) NULL,
        `sector` varchar(255) NULL,
        `industry` varchar(255) NULL,
        `currency` varchar(32) NULL,
        `region` varchar(32) NULL,
        `figi` varchar(255) NULL,
        `created_date` datetime NULL DEFAULT CURRENT_TIMESTAMP(),
        `last_updated_date` datetime NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP(),
        PRIMARY KEY (`id`),
        KEY `exchange_id` (`exchange_id` ASC),
        KEY `symbol`  (`symbol` ASC),
        CONSTRAINT `fk_exchange_id`
          FOREIGN KEY (`exchange_id`)
          REFERENCES `exchange` (`id`)
          ON DELETE NO ACTION
          ON UPDATE NO ACTION
      ) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8        
      '''
    )  
    def __init__(
                 self,
                 db_credentials:Dict = None,
                 exchanges:ExchangeMySQL=None,
                 vendors:DataVendorMySQL=None,
                 name:str = 'security',
                 **kwargs
    ):
      super().__init__(
              (db_credentials if db_credentials is not None
              else settings.MYSQL_CREDENTIALS),
              name,
              (SecurityMySQL.create_schema %name),
              **kwargs
                       )

      self.exchanges = exchanges or ExchangeMySQL(db_credentials, mdb_conn = self._conn)
      self.vendors = vendors or self.exchanges.vendors


    def UPDATE(self, vendor:str = 'IEX', DF:pd.DataFrame = None,):
      if DF is None:
        DF = self.vendors.get_vendor_API(vendor).symbolsDF()
      if 'exchange_id' not in DF.columns:
        potential_exch_cols = [c for c in DF.columns if 'exchange' in c.lower()]
        db_exch_id = self.exchanges.DF['id']
        for c in potential_exch_cols:
          db_exch = db_exch_id.reindex(DF[c].unique())
          if len(db_exch.dropna()) == len(db_exch):
            db_exch = db_exch.where(pd.notnull(db_exch),None)
            DF['exchange_id'] = [db_exch[i] for i in DF[c].values]
            break
        assert 'exchange_id' in DF.columns, ("unidentified exchange(s) in DF")
        DF = DF.drop(columns=potential_exch_cols)
      if not isinstance(DF.index, pd.RangeIndex):
        DF.reset_index(inplace=True)
      
      assert set(DF.columns).issubset(set(self.all_accepted_columns)), "Unrecognized column(s): %s" %str([c for c in DF.columns if c not in self.all_accepted_columns])
      upserted = self.upsertDF(DF,['symbol','exchange_id'])
      for i,_count in upserted.items():
        if _count > 0:
          logger.warning("%s %s Security Symbols" %(str(i).upper(), str(_count)))

    @property
    def DF(self):
      return self._fullDF().set_index("symbol")

    @property
    def List(self):
      return [e[0] for e in self.executeSQL("select symbol from %s" %self._name)]



class DailyPriceMySQL(SQLTable):
    create_schema = (
      '''
      CREATE TABLE `%s` (
        `id` int NOT NULL AUTO_INCREMENT,
        `data_vendor_id` int NOT NULL,
        `symbol_id` int NOT NULL,
        `price_date` date NOT NULL,
        `open` decimal(19,4) NULL,
        `high` decimal(19,4) NULL,
        `low` decimal(19,4) NULL,
        `close` decimal(19,4) NULL,
        `volume` bigint NULL,
        `created_date` datetime NULL DEFAULT CURRENT_TIMESTAMP(),
        `last_updated_date` datetime NULL DEFAULT CURRENT_TIMESTAMP() ON UPDATE CURRENT_TIMESTAMP(),
        PRIMARY KEY (`id`),
        KEY `price_date` (`price_date` ASC),
        KEY `data_vendor_id` (`data_vendor_id`),
        KEY `symbol_id` (`symbol_id`),
        CONSTRAINT `fk_symbol_id `
          FOREIGN KEY (`symbol_id`)
          REFERENCES `security` (`id`)
          ON DELETE NO ACTION
          ON UPDATE NO ACTION,
        CONSTRAINT `fk_data_vendor_id`
          FOREIGN KEY (`data_vendor_id`)
          REFERENCES `data_vendor` (`id`)
          ON DELETE NO ACTION
          ON UPDATE NO ACTION
      ) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8
      '''
                    )
    
    def __init__(
                 self,
                 asset_type:assetClasses,
                  db_credentials:Dict=None,
                  symbols:SecurityMySQL=None,
                  vendors:DataVendorMySQL=None,
                  name:str = 'daily_price',
                      by_vendor:str = None,
                      symbols_list:List[str] = None,
                      **kwargs
    ):
      super().__init__(
              db_credentials = (db_credentials if db_credentials is not None
                                else settings.MYSQL_CREDENTIALS),
                  price_table_name = name,
                    price_table_schema = (DailyPriceMySQL.create_schema %name),
                    **kwargs
                       )
      self.symbols = symbols or SecurityMySQL(db_credentials, mdb_conn = self._conn)
      self.vendors = vendors or self.symbols.vendors

      self.asset_type = asset_type
      self.symbols_list = symbols_list
      self.by_vendor = by_vendor

      if self.by_vendor:
        assert self.by_vendor in self.vendors.List
        self.symbols_list = self._query_available_symbols_in_database_by_vendor(self.by_vendor)
        if settings.PRINT_EVENTS:
          print("Initialized DailyPriceMySQL DataSource From Vendor '%s' | Available Symbols Count = %s" %(str(self.by_vendor), str(len(self.symbols_list))))
      self._cached_copies = []


   #!----------| ABSTRACTED METHODS OF A PRICE DATA SOURCE |------------#
    #---| Self-Copy
    def create_price_source_copy(self,
                                 cache_copy:bool = False,
    ):
      copy = DailyPriceMySQL(
                        asset_type = self.asset_type,
                        db_credentials = self._db_credentials.copy(),
                        name = self._full_credentials['table_name'],
                        by_vendor = None,
                            )
      copy.by_vendor = self.by_vendor #--| skip SQL vetting
      copy.symbols_list = (self.symbols_list.copy() if self.symbols_list else self.symbols_list)
      if cache_copy:
        self._cached_copies.append(copy)
      return copy
    #---------------------------|


    #------| Assets/Universe
    def assetsDF(self,
                 **kwargs
    )->pd.DataFrame:
        df = self.symbols.DF.astype(str)
        if self.symbols_list:
          df = df.reindex(self.symbols_list)
        
        if 'sector' in kwargs:
          assert isinstance(kwargs['sector'],str)

          df = df[df.sector == kwargs['sector']]

        return df

    def assetsList(self,
                   **kwargs
    )->list:
      return list(self.assetsDF(**kwargs).index.values)
    
    @property
    def sectorsList(self)->list:
      return self.symbols.DF.sector.dropna().unique()  
    #---------------------------|



    #-----------| Price
    def get_assets_bid_ask_dfs(self,
                               asset:str,
                               *assets:str,
                                  start_dt=None,   
                                  end_dt=None,
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
        #--| parallelizing queries for performance
        symbols = [asset] + [s for s in assets]
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
    #---------------------------|



    #----| Price Date Ranges
    @functools.lru_cache(maxsize = 1024 * 1024)
    def get_assets_price_date_ranges_df(self,
                                        asset:str,
                                        *assets:str,
    )->pd.DataFrame:

        symbols = [asset] + [s for s in assets]
        if self.symbols_list:
          assert set(symbols).issubset(self.symbols_list)
        
        def _get_result(source, symbol, vendor):
          return {
              'symbol': symbol,
              'start_dt': self._format_dt(source._asset_symbol_min_price_date_by_vendor(symbol, vendor)),
              'end_dt': self._format_dt(source._asset_symbol_max_price_date_by_vendor(symbol,vendor)),
                }
        final_df = pd.DataFrame()
        for vendor in self.vendorsList:
          result = pd.DataFrame.from_dict(
                                list(
                                  concurrent.futures.ThreadPoolExecutor().map(
                                                                          _get_result, 
                                                                          *zip(*(
                                                                            (
                                                                              self.create_price_source_copy(cache_copy = True),
                                                                              symbol,
                                                                              vendor,
                                                                            ) for symbol in symbols
                                                                                ))
                                                                              )
                                    )
                                          ).set_index('symbol').dropna()
          self._close_cached_copies()
          final_df = final_df.append(result)
          symbols = [s for s in symbols if s not in final_df.index]
          if len(symbols) == 0:
            break
        return final_df

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
    #---------------------------|

   #!----------------------------------------------------------------#

    def update_assets_daily_price(self,
              vendor:str,
              batch_size:int=100,
              symbols_to_update:List[str] = None,
              skip_empty_update:bool = True,
              DF:pd.DataFrame=None,                           
    ):
      assert vendor in self.vendors.List
      vendor_id = self.vendors.DF.id[vendor]
      symbols_id = self.symbols.DF['id'] 

      inserted_count = 0
      updated_count = 0
      t0 = pd.Timestamp.now()

      if DF is not None: #---| UPSERT ONCE WITH GIVEN DATAFRAME (NO API CALLS WILL BE MADE)
        self._upsert_daily_price_DF(DF,['price_date', 'symbol_id', 'data_vendor_id'])

      else: #---| PERFORM UPSERT IN BATCHES OF SYMBOLS BY MAKING API CALLS
        if symbols_to_update is not None:
          omitted = [s for s in symbols_to_update if s not in symbols_id.index]
          if len(omitted) > 0:
            logger.warning("Omitting %s given symbols that are not in database universe" %str(len(omitted)))
            logger.warning(str(omitted))
          symbols_id = symbols_id.reindex([s for s in symbols_to_update if s not in omitted])
        symbols_id = dict(symbols_id)
        assert len(symbols_id) != 0, "No symbols in Symbol table, code out schematic or manually prepare it (symbol.csv)"
        
        logger.warning("----------------------------------------------------------------")
        logger.warning("---------------| Updating Equities Daily Prices |---------------")
        logger.warning("----------------------------------------------------------------")


        logger.warning("Checking database for latest available price_date from '%s' of %s symbols..." %(vendor,str(len(symbols_id))))
        #!---| Query for all symbols to get their max price_dates from SQL Database
        symbols_by_max_dates = {}
        for s in symbols_id:
          d = self._asset_symbol_max_price_date_by_vendor(s,vendor)
          if d not in symbols_by_max_dates:
            symbols_by_max_dates[d] = []
          if s not in symbols_by_max_dates[d]:
            symbols_by_max_dates[d].append(s)
        
        #!---| Download latest daily price for symbols with their respective start dates & process for upsert to Database
        logger.warning("Performing Update in batches of %s" %str(batch_size))
        for start_date,symbols in symbols_by_max_dates.items():
          logger.warning("For %s symbols with '%s' as start_date:" %(str(len(symbols)),str(start_date)))
          
          i = 0
          batch_number = 1
          while True:
            symbols_batch = symbols[i:i+batch_size]
            batch_data = self.vendors.get_vendor_API(vendor).get_barset(symbols_batch,"1D",start_date)
            try:
              batch_data = self._transform_DF_for_daily_price_upsert(batch_data, vendor = vendor, start_date=start_date)
            except Exception:
              logger.warning("Cannot transform, skipping this batch of symbols: %s" %str(symbols_batch))
              pass
            else:
              upserted = self.upsertDF(batch_data,no_filter=True)
              for a,_count in upserted.items():
                if _count > 0:
                  if a == 'inserted':
                    logger.warning("  Batch #%s : %s New Data Points Inserted" %(str(batch_number),_count))
                    inserted_count += _count
                  elif a == 'updated':
                    logger.warning("  Batch #%s : %s Existing Data Points Updated" %(str(batch_number),_count))
                    updated_count += _count
              if (upserted['inserted'] == upserted['updated'] == 0) and skip_empty_update:
                logger.warning("  No New Data Upserted. Skipping remaining symbols (set skip_empty_update=False for otherwise)")
                break
          
            #---| Loop Breaker
            if symbols_batch[-1] == symbols[-1]:
              break
            else:
              i += batch_size
              batch_number += 1

      print("Update Completed:")
      print("--Total Data Points Inserted: %s" %(str(inserted_count)))
      print("--Total Data Points Updated: %s" %(str(updated_count)))
      print("--Total Time Elapsed: %s" %(str(pd.Timestamp.now() - t0)))

    @property
    def vendorsDF(self,)->pd.DataFrame:
      return self.vendors.DF.reindex(self.vendorsList)
    
    @property
    def vendorsList(self,)->list:
      return self.vendors.List if self.by_vendor is None else [self.by_vendor]




   #!---| BACKEND
    def _transform_DF_for_daily_price_upsert(self,
                                    upsert_df:pd.DataFrame,
                                    **kwargs
    ):
        df = upsert_df.copy()
        #---| Case I: Basic DF with no MultiIndex columns
        if not isinstance(df.columns,pd.MultiIndex):
          assert 'symbol_id' in df.columns
          if 'price_date' not in df.columns:
            assert not isinstance(df.index, pd.RangeIndex)
            df.index = pd.DatetimeIndex(df.index)
            df['price_date'] = df.index.values
            df.index = range(len(df))
          if 'data_vendor_id' not in df.columns:
            vendor_id = int(self.vendors.DF.id[kwargs['vendor']]) if 'vendor' in kwargs else (
                                        int(kwargs['vendor_id']) if 'vendor_id' in kwargs else None
                                  )
            assert isinstance(vendor_id, int)
            df['data_vendor_id'] = vendor_id
          return df.where(pd.notnull(df), None)
        
        #---| Case II: MultiIndex Columns of (symbols, columns)
        else:
          assert not isinstance(df.index, pd.RangeIndex)
          df.index = pd.DatetimeIndex(df.index) 
          symbols_id = dict(kwargs['symbols_id']) if 'symbols_id' in kwargs else dict(self.symbols.DF['id'])
          vendor_id = int(self.vendors.DF.id[kwargs['vendor']]) if 'vendor' in kwargs else (
                            int(kwargs['vendor_id']) if 'vendor_id' in kwargs else None
                                          )
          assert isinstance(vendor_id, int)
          assert isinstance(symbols_id, dict)

          try:
            df_symbols = list(df.columns.get_level_values('symbols').unique())
          except KeyError:
            if settings.PRINT_EVENTS:
              print("Daily Price columns does not contain 'symbols' as name. " 
                    "Attempting to grab the first index locations..."
                    )
            df_symbols = list(pd.Series([i[0] for i in df.columns]).unique())

          assert set(df_symbols).issubset(set(symbols_id.keys())), (
                          "Daily Price data contains unidentified symbol(s) without id(s): %s" %(
                                                                        str([
                                                                                s for s in df_symbols if s not in symbols_id
                                                                                  ])
                                                                                                                )
                                                              )
          
          start_date = pd.Timestamp(kwargs['start_date']) if ('start_date' in kwargs) else None
          transformed_df = pd.DataFrame()
          for s in df_symbols:
            _df = df[s]
            _df.index = pd.DatetimeIndex(_df.index)
            if start_date:
              _df = _df[_df.index > start_date]
            _df['symbol_id'] = symbols_id[s]
            _df['price_date'] = _df.index.values
            _df.index = range(len(_df))
            transformed_df = transformed_df.append(_df)
          transformed_df['data_vendor_id'] = vendor_id
          transformed_df.index = range(len(transformed_df))
          transformed_df = transformed_df.where(pd.notnull(transformed_df), None)
          return transformed_df      

    def _upsert_daily_price_DF(self,
                            DF:pd.DataFrame,
                            filter_columns:List[str] = None,
                            **kwargs
    ):
      if settings.PRINT_EVENTS:
        print("Upserting Equities Daily Price with given DF.")
      upserted = self.upsertDF(self._transform_DF_for_daily_price_upsert(DF, **kwargs), filter_columns)
      for a,_count in upserted.items():
        if _count > 0:
          if a == 'inserted':
            logger.warning("%s New Data Points Inserted" %(str(_count)))
          elif a == 'updated':
            logger.warning("%s Existing Data Points Updated" %(str(_count)))
      if (upserted['inserted'] == upserted['updated'] == 0):
        logger.warning("No New Data Upserted from DF given.")

    @functools.lru_cache(maxsize = 1024 * 1024)
    def _assets_daily_price_DF(self,
                                asset:str,
                                *assets:str
    ):
        symbols = [asset] + [s for s in assets]
        if self.symbols_list:
          assert set(symbols).issubset(self.symbols_list)
        result = pd.DataFrame()
        for vendor in self.vendorsList:
          all_dfs = concurrent.futures.ThreadPoolExecutor().map(
                                          self.__class__._query_asset_symbol_daily_price_DF, 
                                          *zip(*(
                                            (
                                              self.create_price_source_copy(cache_copy = True),
                                              symbol,
                                              vendor,
                                            ) for symbol in symbols
                                                ))
                                                          )
          final_df = pd.concat([
                  d.where(pd.notna(d), np.nan) for d in all_dfs if (
                                                  not d.where(pd.notna(d), np.nan).dropna().empty
                                                                  )
                                ], axis=1)
          self._close_cached_copies()
          final_df.columns.names = ('symbols','columns')
          final_df = final_df.set_index(final_df.index.tz_localize(settings.TIMEZONE))
          result = pd.concat([result,final_df], axis=1)
          symbols = [s for s in symbols if s not in result.columns.get_level_values('symbols')]
          if len(symbols) == 0:
            break 
        
        if len(symbols) > 0:
          if settings.PRINT_EVENTS:
            print("Warning: Queried Daily Prices DataFrame is missing %s symbols:" %len(symbols))
            print(symbols)
        
        return result
    
    @functools.lru_cache(maxsize = 1024 * 1024)
    def _asset_symbol_max_price_date_by_vendor(self,
                                               asset:str,
                                               vendor:str
    ):
      dat = self.executeSQL(
        '''
        SELECT max(price_date)
        FROM %s dp
        INNER JOIN %s sym
        INNER JOIN %s vendor
        ON
          dp.symbol_id = sym.id AND
          dp.data_vendor_id = vendor.id
        WHERE
          sym.symbol = '%s' AND
          vendor.name = '%s' AND
          dp.close IS NOT NULL AND
          dp.open IS NOT NULL
        ''' %(
              self._name,
              self.symbols._name,
              self.vendors._name,
              asset,
              vendor
            )
      )
      return None if len(dat) == 0 else dat[0][0]

    @functools.lru_cache(maxsize = 1024 * 1024)
    def _asset_symbol_min_price_date_by_vendor(self,
                                               asset:str,
                                               vendor:str
    ):
      dat = self.executeSQL(
        '''
        SELECT min(price_date)
        FROM %s dp
        INNER JOIN %s sym
        INNER JOIN %s vendor
        ON
          dp.symbol_id = sym.id AND
          dp.data_vendor_id = vendor.id
        WHERE
          sym.symbol = '%s' AND
          vendor.name = '%s' AND
          dp.close IS NOT NULL AND
          dp.open IS NOT NULL
        ''' %(
              self._name,
              self.symbols._name,
              self.vendors._name,
              asset,
              vendor
            )
      )
      return None if len(dat) == 0 else dat[0][0]

    @functools.lru_cache(maxsize = 1024 * 1024)
    def _query_available_symbols_in_database_by_vendor(self, vendor:str):
      assert vendor in self.vendors.List
      sqlDF = self.assetsDF().reset_index().set_index('id')
      sqlDF.index = sqlDF.index.astype(int)
      df = sqlDF.reindex(
            [
            int(i[0]) for i in self.executeSQL(
              'select distinct symbol_id from %s where data_vendor_id = %s' %(
                                                                              self._name,
                                                                              self.vendors.DF.id[vendor]
                                                                             )
                                              )
            ]
                        )
      df = df.reindex(df[['symbol']].dropna().index)
      return [] if df.empty else list(df.set_index('symbol').sort_index().index.values)

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

    def _close_cached_copies(self):
      for source in self._cached_copies:
        source._conn.close()
      self._cached_copies = []
 
    def _query_asset_symbol_daily_price_DF(self,
                                      asset:str,
                                      vendor:str,
    )->pd.DataFrame:
      df_cols = [
        "open", "high", "low",
                "close","volume"
                          ]
      select_str = "dp.price_date, " + str(
                                    [
                                      ".".join(["dp",p]) for p in df_cols
                                    ]
                                          )[1:-1].replace("'","") 
      
      cond_str = "vendor.name = '%s' AND sym.symbol = '%s'" %(vendor, asset)
      sql = (
            '''
            SELECT %s
            FROM %s as sym
            INNER JOIN %s AS dp
            INNER JOIN %s AS vendor
            ON
                dp.symbol_id = sym.id AND
                dp.data_vendor_id = vendor.id
            WHERE
                %s
            ORDER BY
                dp.price_date ASC
            '''%(
                select_str,
                self.symbols._name,
                self._name,
                self.vendors._name,
                cond_str
                )
              )
      dat = np.array(self.executeSQL(sql))

      cols = [
              np.array([asset for _ in df_cols]),
              np.array(df_cols)
             ]

      if len(dat) == 0:
        return pd.DataFrame(columns = cols)
      else:
        df = pd.DataFrame(
                      data = dat[:,1:],
                      index = pd.DatetimeIndex(dat[:,0]),
                      columns = cols
                        )
        for c in df.columns:
          df[c] = pd.to_numeric(df[c])
        return df

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

    
