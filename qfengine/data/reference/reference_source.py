from abc import ABCMeta, abstractmethod
import pandas as pd



class SymbolReferenceDataSource(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def symbolsList(self):
        raise NotImplementedError("Implement symbolsList()")
    
    @abstractmethod
    def symbolsDF(self):
        raise NotImplementedError("Implement symbolsDF()")


class DataVendorReferenceDataSource(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def vendorsList(self):
        raise NotImplementedError("Implement vendorsList()")
    
    @abstractmethod
    def vendorsDF(self):
        raise NotImplementedError("Implement vendorsDF()")



class ExchangeReferenceDataSource(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def vendorsList(self):
        raise NotImplementedError("Implement exchangesList()")
    
    @abstractmethod
    def vendorsDF(self):
        raise NotImplementedError("Implement exchangesDF()")

