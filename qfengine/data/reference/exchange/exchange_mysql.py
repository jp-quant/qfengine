from qfengine.data.reference.reference_source import SymbolReferenceDataSource
from qfengine.data.database import CSVDatabase, MySQLDatabase
from abc import ABCMeta, abstractmethod
import pandas as pd
import os





class SymbolReferenceCSV(SymbolReferenceDataSource, CSVDatabase):

    def __init__(self,
                 csv_dir,
                 csv_file,
                 symbols_list=None,
    ):
        super().__init__(csv_dir)
        assert csv_file in self._csv_files_in_dir
        self.csv_file = csv_file
        self.symbols_list = symbols_list
        self._DF = self._init_referenceDF()

    def _init_referenceDF(self):
        df = pd.read_csv(os.path.join(self.csv_dir, self.csv_file),
                         header = 0, index_col = 0,
        )
        if self.symbols_list is None:
            return df
        symbols = [s for s in self.symbols_list if s in df.index]
        self.symbols_list = symbols
        return df.reindex(symbols)
    
    def symbolsList(self):
        return self.symbols_list.copy()
    
    def symbolsDF(self):
        return self._DF.copy()
    



