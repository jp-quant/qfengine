from abc import ABCMeta, abstractmethod


class RiskModel(object):
    """
    Abstract interface for an RiskModel callable.

    A derived-class instance of RiskModel takes in an Asset
    Universe and an optional DataHandler instance in order
    to compute the risk model signal, aka cost of risk factors matrix

    The risk model's signal, combined with alpha signals are used
    within the PortfolioConstructionModel for final optimization
    to generate target weights for the portfolio.

    Implementing __call__ produces a dictionary keyed by
    Asset and with a scalar value as the signal.
    """

    __metaclass__ = ABCMeta


    def __repr__(self):
        return self.__class__.__name__

    @abstractmethod
    def __call__(self, dt, **kwargs):
        raise NotImplementedError(
            "Should implement __call__()"
        )