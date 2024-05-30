from abc import ABCMeta, abstractmethod
from typing import List, Union
import MySQLdb as mdb
import logging
import os
import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)



#!----| CSV Data Source(s) 
class CSVDataDirectory(object):

    __metaclass__ = ABCMeta

    def __init__(self, csv_dir:str):
        if not os.path.exists(csv_dir):
            try:
                os.makedirs(csv_dir)
            except:
                raise
        self.csv_dir = csv_dir

    @property
    def _csv_files_in_dir(self):
        return [f for f in os.listdir(self.csv_dir) if f.endswith('.csv')]

class CSVDataSource(CSVDataDirectory):

    __metaclass__ = ABCMeta

    def __init__(self, csv_dir:str):
        super().__init__(csv_dir,)





#!----| MySQL Data Source(s) ~ MySQL Table (within a relational database)
class MySQLConnection(object):

    __metaclass__ = ABCMeta

    def __init__(self,
                 user:str,
                 passwd:str,
                 host:str,
                 db:str,
                 **kwargs,
    ):
        self._credentials = {
                            'user': user,
                            'passwd':passwd,
                            'host':host,
                            'db':db,
                            }
        self._conn = None
        for v in kwargs.values():
            if isinstance(v, mdb.connections.Connection):
                self._conn = v
                break
        if self._conn is None:
            self._conn = MySQLConnection._new_connection(**self._credentials)
        self._db_name = self._credentials['db']
    
    def _refresh_connection(self):
        self._conn = MySQLConnection._new_connection(**self._credentials)

    def executeSQL(self,
                    query:str,
                    query_args:List[tuple] = None,
                    return_rows_affected:bool = False,
                    conn = None,
                    **kwargs
    ):
        if conn is None:
            conn = self._conn
        if '%s' in query:
            assert query_args is not None
            return MySQLConnection._executemany(conn, query, query_args, return_rows_affected)
        else:
            return MySQLConnection._execute(conn, query, return_rows_affected)
    
    @staticmethod
    def _executemany(con,
                    insert_str:str,
                    insert_data:List[tuple],
                    return_rows_affected:bool=False,
    ):
        con.autocommit(False)
        cur = con.cursor()
        exc = cur.executemany(insert_str,insert_data)
        resp = cur.fetchall()
        con.commit()

        return resp if not return_rows_affected else exc

    
    @staticmethod
    def _execute(con,
                cmd:str,
                return_rows_affected:bool=False,
    ):
        con.autocommit(False)
        cur = con.cursor()
        exc = cur.execute(cmd)
        resp = cur.fetchall()
        if cmd.lower().startswith("select"):  
            while len(resp) != exc:
                print("Fetched Data does not match executed result. Retrying.")
                exc = cur.execute(cmd)
                resp = cur.fetchall()
        con.commit()
        return resp if not return_rows_affected else exc

    @staticmethod
    def _new_connection(user:str,
                        passwd:str,
                        host:str,
                        db:str,
    ):
        
        credentials = {'user':user, 'passwd':passwd, 'host':host}
        try:
            conn = mdb.connect(**credentials)
        except:
            raise Exception("Failed to connect to SQL server from credentials given. Fix (user,psswd,host) in sql_crendentials.yaml")
        
        if db not in [d[0] for d in MySQLConnection._execute(conn,"show databases")]:
            logger.warning("Database '%s' doesn't exist in SQL Server given." %db)
            if credentials['user'] == 'root':
                logger.warning("Root Access Detected, Attempting to Create New Database Named '%s'..."%db)
                MySQLConnection._execute(conn,"CREATE DATABASE %s" %db)
        
        full_credentials = credentials.copy()
        full_credentials['db'] = db
        try:
            conn = mdb.connect(**full_credentials)
        except:
            try:
                MySQLConnection._execute(conn, "set global max_connections = 1000000")
            except:
                raise Exception("Given User Credentials Cannot Access Database %s (but sees it?), even after adjusting max_connection to 1mil." %db)
        return conn


    def _available_sql_tables(self):
        return [t[0] for t in self.executeSQL('SHOW TABLES')]

class MySQLDataSource(MySQLConnection):

    __metaclass__ = ABCMeta

    def __init__(self,
                 user:str,
                 passwd:str,
                 host:str,
                 db:str,
                 table_name:str,
                 schema:str = None,
                 **kwargs,
    ):
        super().__init__(user, passwd, host, db, **kwargs)

        if table_name not in [t[0] for t in self.executeSQL("show tables")]:
            assert isinstance(schema,str)
            logger.warning("No Table '%s' Found in SQL Database '%s'...Attempting to create new one..." %(table_name,self._credentials['db']))
            self.executeSQL(schema)
        self._schema = pd.DataFrame(
                            data = (np.array(self.executeSQL("show columns from %s" %table_name)))[:,:4],
                            columns = ['column_name','data_type','null_okay','key'],
                            ).set_index('column_name').drop(
                                                        index=['id']
                                                            ).astype(str)

        if 'column_name' not in self._schema.columns:
            assert self._schema.index.name == 'column_name'
        else:
            self._schema = self._schema.set_index("column_name")
        assert 'data_type' in self._schema.columns
        assert 'null_okay' in self._schema.columns

        self._name = table_name

    @property
    def required_columns(self):
        return list(self._schema[self._schema['null_okay'] == 'NO'].index.values)
        
    @property
    def all_accepted_columns(self):
        return list(self._schema.index.values)

    def _fullDF(self, columns:Union[List[str],str] = None):
        table_cols = self.all_accepted_columns + ['id']
        if columns is not None:
            if isinstance(columns,str):
                columns = [columns]
            assert set(columns).issubset(set(table_cols))
            assert len(columns) > 0
        else:
            columns = table_cols
        cols_str = str(columns)[1:-1].replace("'","")
        exc_str = "select %s from %s" %(cols_str,self._name)

        sql_dat = self.executeSQL(exc_str)
        if len(sql_dat) > 0:
            return pd.DataFrame(
                            data = sql_dat,
                            columns = columns, 
                            )
        else:
            return pd.DataFrame(columns=columns)

    def column_data_type(self,column:str):
        assert column in self.all_accepted_columns
        dat_type = self._schema['data_type'][column].lower()
        if 'int' in dat_type:
            return int
        elif 'decimal' in dat_type:
            return float
        elif 'varchar' in dat_type: 
            return str
        elif 'date' in dat_type:
            return np.datetime64
        
    def insertableDF(self,input_data:pd.DataFrame):
        try:
            # 1) Check columns
            assert set(self.required_columns).issubset(set(input_data.columns)),(
                                        "Input data is missing required column(s): %s" %str([c for c in self.required_columns if c not in input_data.columns])
                                                                                            )
            assert set(input_data.columns).issubset(set(self.all_accepted_columns)), (
                                        "Input data contains invalid column(s): %s" %str([c for c in input_data.columns if c not in self.all_accepted_columns])
                                                                                        )
            assert not input_data.empty
            return True
        except AssertionError: # raise message in warning
            return False
        
    def _prepare_insertDF(self,data_to_insert:pd.DataFrame):
        insert_cols = list(data_to_insert.columns)
        column_str = str(insert_cols)[1:-1].replace("'","")

        insert_str = "INSERT INTO %s (%s) VALUES (%s)" %(self._name,
                                                            column_str,
                                                            ("%s, " * len(insert_cols))[:-2]
                                                            )
        insert_data = [
                tuple(d) for d in data_to_insert.values
                    ]
        
        return insert_str,insert_data

    def _prepare_updateDF(self,data_to_update:pd.DataFrame):
        assert "id" in data_to_update.columns
        update_cols = list(data_to_update.set_index("id").columns)
        update_str = (
            '''
            UPDATE %s
            SET %s
            WHERE %s
            ''' %(
                    self._name,
                    ((" = %s, ").join(update_cols) + " = %s"),
                    "id = %s",
                )
                    )
        update_data = []
        for _id in data_to_update.set_index("id").index:
            dat = data_to_update.set_index("id").loc[_id].values
            update_data.append(tuple(list(dat) + [_id]))
        return update_str, update_data
        
    def _upsert_filter(self,
                        input_data:pd.DataFrame,
                        by_columns:list = None,
        ):
        if by_columns is None:
            by_columns = list(input_data.columns)
        assert set(by_columns).issubset(set(input_data.columns))
        df_to_filter = input_data[by_columns]


        new = []
        existed = []
        existed_id = []
        for i in df_to_filter.index:
            dat = df_to_filter.loc[i].values
            cond = " AND ".join(
                                    [
                                    ("%s = '%s'" %(str(c), str(v))) if v is not None
                                            else ('%s IS NULL' %str(c))
                                        for c,v in zip(by_columns,dat)
                                    ]
                                    )
            resp = self.executeSQL(
                '''
                SELECT id FROM %s
                WHERE %s
                '''% (self._name,cond)
                            )
            if len(resp) == 0:
                new.append(i)
            else:
                all_dat = input_data.loc[i].values
                for j in resp:
                    existed.append([j[0]] + list(all_dat))

        new = input_data.reindex(new).reset_index(drop=True)
        existed = pd.DataFrame(existed, columns= (['id'] + list(input_data.columns)))

        return {'insert':new, 'update':existed}

    def upsertDF(self,
                    df:pd.DataFrame,
                    filter_by_columns:List[str]=None,
                    no_filter:bool=False,
        ):
        if df.empty:
            return {'inserted': 0, 'updated': 0}
        if not self.insertableDF(df):
            raise Exception("df to be upserted did not pass table upsert check.")
        
        inserted = 0
        updated = 0
        if no_filter:
            upsert_data = {'insert':df, 'update':pd.DataFrame()}
        else:
            upsert_data = self._upsert_filter(df,filter_by_columns)

        
        if not upsert_data['insert'].empty:
            insert_str, insert_data = self._prepare_insertDF(upsert_data['insert'])
            rows_affected = self.executeSQL(insert_str,insert_data, return_rows_affected=True)
            inserted += rows_affected
        if not upsert_data['update'].empty:
            update_str, update_data = self._prepare_updateDF(upsert_data['update'])
            rows_affected = self.executeSQL(update_str, update_data, return_rows_affected=True)
            updated += rows_affected
        
        return {'inserted': inserted, 'updated': updated}
    
    def delete_duplicates(self,
                            by_columns:List[str] =None,
                            ):
        if by_columns is None:
            by_columns = self.required_columns
        assert set(by_columns).issubset(self.all_accepted_columns)
        cols_str = str(by_columns)[1:-1].replace("'","")
        sql = (
            '''
            delete T
            from %s T
            inner join (
            select row_number() over(
                    partition by %s
                                order by id
                        ) rn, id
            from %s
                ) dupl_T
            on T.id = dupl_T.id
            where dupl_T.rn > 1;
            ''' %(
                self._name,
                cols_str,
                self._name
            )
        )
        return self.executeSQL(sql,return_rows_affected=True)

    def _print_engine_status(self):
        print(self.executeSQL("show engine innodb status")[0][-1])
    