from abc import ABCMeta, abstractmethod

class Universe(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def get_assets(self, dt):
        raise NotImplementedError("Universe needs to implement get_assets()")