from qfengine.portfolio.optimizer.optimizer import PortfolioOptimiser
import pandas as pd
import numpy as np
from scipy.optimize import minimize
from typing import List, Union, Dict
from abc import ABCMeta




class AssetAllocationOptimizer(PortfolioOptimiser):

    __metaclass__ = ABCMeta

    """ [Abstract] Modern Portfolio Theory ~ Assets Allocation

        Parameters
        ----------
        universe : `Universe`
            The Assets to make signal forecasts for.
        data_handler : `DataHandler`
            A DataHandler used to preserve interface across AlphaModels.
        log_ret : `bool`
            [Optional] Whether or not we should compute returns data in logarithmic format.

        gross_exposure: `float` [Default to 1.0]
            [Optional] Optimizing summation constraint for the absolute values of allocation weights.
                        NOTE: Default to 1.0 | Basically leverage --> 1.0 = No leverage
                                -> 1.0 = 100% of 'capital' =>> ('invested' + 'owed') ~ abs('long') + abs('short')
                                -> Induce flexibility in defining aa subgroups by `gross_leverage` ratio for considering factors such as cash_buffer, current weights, etc...
        
        net_exposure: `float` [Default to None]
            [Optional] Optimizing summation constraint for the values with signs (-/+ ~ short/long) of allocation weights.
                        NOTE: 'market expectation', Default to None ~ No constraint variable ~ No 'expectation considered' for the optimized weights result
                                        = 0.0 = market_neutral ~ efficient market
                                        > 0.0 = bullish
                                        < 0.0 = bearish
                                        = long_exposure + short_exposure
        long_exposure: `float` [Default to None]
        short_exposure: `float` [Default to None]
        
        optimizing_function: `function`
            [Optional] Function taking in ret & allocation weights array to compute metric for optimization. Defaults to sharpe
    """
    def __init__(self,
                 data_handler = None,
                    gross_exposure:float = 1.0,
                    net_exposure:float = None,
                    long_exposure:float = None,
                    short_exposure:float = None,
                            bounds_op = None,
                            init_guess_op = None,
                            additional_constraints_op = None,
                                optimizing_function = None,
                                    **kwargs
    ): 
        self.data_handler = data_handler

        self.gross_exposure = gross_exposure
        self.net_exposure = net_exposure
        self.long_exposure = long_exposure
        self.short_exposure = short_exposure
        
        self.bounds_op = bounds_op
        self.init_guess_op = init_guess_op
        self.additional_constraints_op = additional_constraints_op

        self.optimizing_function = optimizing_function

        self._init_params()

    def __repr__(self):
        return self.__class__.__name__ 

    def _init_params(self):
        assert self.gross_exposure >= 0.0 #must
        if self.long_exposure:
            assert self.long_exposure >= 0.0
        if self.short_exposure:
            assert self.short_exposure <= 0.0
        try:
            self.net_exposure = self.long_exposure + self.short_exposure
        except:
            pass
        
        optimizing_function = None
        if self.optimizing_function:
            optimizing_function = self.optimizing_function
        if isinstance(optimizing_function, str):
            for f in [_ for _ in dir(self) if '_optimizing_function' in _]:
                if optimizing_function in f:
                    optimizing_function = getattr(self,f)
                    break
        if optimizing_function is None:
            optimizing_function = AssetAllocationOptimizer._mean_variance_optimizing_function
        #---| Finished init & set it as out optimizing function
        self.optimizing_function = optimizing_function


    @staticmethod
    def _returns_optimizing_function(allocations, ret_mu, ret_cov)->float:
        return ret_mu.dot(np.array(allocations))
    @staticmethod
    def _volatility_optimizing_function(allocations, ret_mu, ret_cov)->float:
        return np.sqrt(np.dot(allocations.T,np.dot(ret_cov,allocations)))
    @staticmethod
    def _sharpe_optimizing_function(allocations, ret_mu, ret_cov)->float:
        return (
                AssetAllocationOptimizer._returns_optimizing_function(allocations, ret_mu = ret_mu, ret_cov = ret_cov)
                        /
                AssetAllocationOptimizer._volatility_optimizing_function(allocations, ret_mu = ret_mu, ret_cov = ret_cov)
                )
    @staticmethod
    def _mean_variance_optimizing_function(allocations, ret_mu, ret_cov)->float:
        return (
                AssetAllocationOptimizer._returns_optimizing_function(allocations, ret_mu = ret_mu, ret_cov = ret_cov)
                        -
                AssetAllocationOptimizer._volatility_optimizing_function(allocations, ret_mu = ret_mu, ret_cov = ret_cov)
                )


    def _check_model_signals(self,
                            alpha_weights:Union[Dict, pd.Series],
                            risk_factors_matrix: pd.DataFrame,
    ):
        assert not risk_factors_matrix.empty, "Empty Risk Factors Matrix %s" %(str(risk_factors_matrix))
        assert len(alpha_weights) == risk_factors_matrix.shape[1]
        assert set(pd.Series(alpha_weights).index).issubset(set(risk_factors_matrix.columns))


    def _bounds(self, 
                alpha_weights:Union[Dict, pd.Series],
                risk_factors_matrix:pd.DataFrame,
                **kwargs
    ):
        if self.bounds_op is None:
            return [(None, None) for _ in risk_factors_matrix.columns]
        else:
            return list(self.bounds_op(alpha_weights, risk_factors_matrix, **kwargs))

    def _init_guess(self, 
                    alpha_weights:Union[Dict, pd.Series],
                    risk_factors_matrix:pd.DataFrame,
                    **kwargs
    ):
        if self.init_guess_op is None:
            return [(1/risk_factors_matrix.shape[1]) for _ in risk_factors_matrix.columns]
        else:
            return list(self.init_guess_op(alpha_weights, risk_factors_matrix, **kwargs))

    def _constraints(self,
                     alpha_weights:Union[Dict, pd.Series],
                     risk_factors_matrix:pd.DataFrame,
                     **kwargs
    ):
        
        constraints = []
        if self.gross_exposure:
            constraints.append({
                                'type' : 'eq',
                                'fun' : lambda allocations:(
                                        sum(np.abs(w) for w in allocations) - self.gross_exposure
                                                            )
                                })
        
        if self.net_exposure:
            constraints.append({
                                'type' : 'eq',
                                'fun' : lambda allocations:(
                                        sum(allocations) - self.net_exposure
                                                            )
                                })
        if self.short_exposure:
            constraints.append({
                                'type' : 'eq',
                                'fun' : lambda allocations:(
                                        sum(w for w in allocations if w < 0.0) - self.short_exposure
                                                            )
                                })
        if self.long_exposure:
            constraints.append({
                                'type' : 'eq',
                                'fun' : lambda allocations:(
                                        sum(w for w in allocations if w > 0.0) - self.long_exposure
                                                            )
                                })
        # TODO: Add more specific constraints if needed
        if self.additional_constraints_op:
            additional_constraints = list(self.additional_constraints_op(alpha_weights, risk_factors_matrix, **kwargs))
            assert (isinstance(c,dict) for c in additional_constraints)
            constraints += additional_constraints
        return tuple(constraints)

    def _to_optimize(self, 
                    alpha_weights:Union[Dict, pd.Series] = None,
                    risk_factors_matrix:pd.DataFrame = None,
                    **kwargs
    ):
        #-| NOTE: optimizing direction--> Minimize negative = Maximizing positive
        
        optimizing_direction = None 
        if self.optimizing_function == self._volatility_optimizing_function:
            assert risk_factors_matrix is not None, "Optimizing for volatility (minimization) requires a covariance matrix/risk factors matrix"
            optimizing_direction = 1
        else:
            assert alpha_weights is not None, "Optimization requires alpha weights"
            if self.optimizing_function != self._returns_optimizing_function:
                assert risk_factors_matrix is not None, "Optimization requires a covariance matrix/risk factors matrix"
            optimizing_direction = -1
        
        assert optimizing_direction is not None

        def to_optimize(allocations):
            return (
                self.optimizing_function(
                                        allocations = allocations,
                                        ret_mu = pd.Series(alpha_weights),
                                        ret_cov = pd.DataFrame(risk_factors_matrix)
                                        ) * optimizing_direction      
                   )
        return to_optimize

    def _run_optimization(self, 
                    alpha_weights:Union[Dict, pd.Series] = None,
                    risk_factors_matrix:pd.DataFrame = None,
                    **kwargs
    ):
        return pd.Series(
                data = minimize(
                            fun = self._to_optimize(alpha_weights = alpha_weights,
                                                    risk_factors_matrix= risk_factors_matrix,
                                                    **kwargs
                                                    ),
                            x0 = self._init_guess(alpha_weights = alpha_weights,
                                                    risk_factors_matrix= risk_factors_matrix,
                                                    **kwargs
                                                    ),
                            bounds = self._bounds(alpha_weights = alpha_weights,
                                                    risk_factors_matrix= risk_factors_matrix,
                                                    **kwargs
                                                    ),
                            constraints = self._constraints(alpha_weights = alpha_weights,
                                                    risk_factors_matrix= risk_factors_matrix,
                                                    **kwargs
                                                    ),
                            method='SLSQP'
                              ).x,
                index = list(risk_factors_matrix.columns)
                    ).astype(float)

    def __call__(self,
                 alpha_weights:Union[Dict, pd.Series],
                 risk_factors_matrix: pd.DataFrame,
                **kwargs
    ):
        self._check_model_signals(alpha_weights, risk_factors_matrix)
        alpha = pd.Series(alpha_weights).reindex(risk_factors_matrix.columns)
        risk = risk_factors_matrix
        return dict(
                self._run_optimization(alpha_weights = alpha,
                                      risk_factors_matrix = risk,
                                      **kwargs
                                      )
                )
        
