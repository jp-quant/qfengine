from qfengine.alpha.alpha_model import AlphaModel
from abc import ABCMeta, abstractmethod



class ExpectedReturnsAlpha(AlphaModel):
    __metaclass__ = ABCMeta

    """
    AlphaModel that returns weights of all assets in given universe, base on their
    expected returns calculated from historical price data grabbed from data_handler given.
    Parameters
    ----------
    signal_weights : `dict{str: float}`
        The signal weights per asset symbol.
    universe : `Universe`, optional
        The Assets to make signal forecasts for.
    data_handler : `DataHandler`, optional
        An optional DataHandler used to preserve interface across AlphaModels.
    """

    def __init__(
        self,
        universe,
        data_handler,
        **kwargs
    ):
        self.universe = universe
        self.data_handler = data_handler


    @abstractmethod
    def calculate_assets_expected_returns(self, dt, **kwargs):
        raise NotImplementedError("Implement calculate_assets_expected_returns()")

    
    def _expected_returns_weights(self, expected_returns):
        return {
            str(s):float(w) for s,w in dict(expected_returns).items()
               }

    def __call__(self, dt, **kwargs):
        """
        Produce the dictionary of fixed scalar signals for
        each of the Asset instances within the Universe.
        Parameters
        ----------
        dt : `pd.Timestamp`
            The time 'now' used to obtain appropriate data and universe
            for the the signals.
        Returns
        -------
        `dict{str: float}`
            The Asset symbol keyed scalar-valued signals.
        """
        return self._expected_returns_weights(
                            self.calculate_assets_expected_returns(dt, **kwargs)
                                        )