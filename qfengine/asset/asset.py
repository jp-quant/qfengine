from abc import ABCMeta


class Asset(object):
    '''
    Meta asset class storing data about asset being traded    
    '''
    __metaclass__ = ABCMeta

    def __init__(self, cash_like:bool):
        self.cash_like = cash_like

class AssetWeight(object):
    '''
    Meta asset class storing data about 'weight' of asset being traded    
    '''
    __metaclass__ = ABCMeta

    def __init__(self,
                 asset,
                 **kwargs
    ):
        assert Asset in asset.__class__.mro(), (
                                "Cannot initialize weight for asset '%s'. " 
                                "Make sure designed asset class (or its superclasses)"
                                "inherits 'Asset' metaclass." %asset
                                )
        