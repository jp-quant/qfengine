from qfengine.execution.execution_handler import (
    ExecutionHandler
)
from qfengine.execution.algo.market_order import (
    MarketOrderNaiveExecution
)
from qfengine.portfolio.construction.construction_model import (
    PortfolioConstructionModel
)

from qfengine.portfolio.construction.order_sizer import (
                                LongOnlyMoneyWeightedOrderSizer,
                                LongShortLeveragedOrderSizer
)
from qfengine.system.rebalance.rebalance_handler import RebalanceHandler
from qfengine import settings

#--| For Default Alpha & Optimizer 
#       : Straight forward fixed allocation, primarily for benchmark purpose 
#               (e.g.: buy & hold rebalancing on SPY)
from qfengine.alpha import SingleFixedWeightsAlpha
from qfengine.portfolio.optimizer import FixedWeightPortfolioOptimiser


import pandas as pd




class QuantTradingSystem(object):
    """
    Encapsulates all components associated with the quantitative
    trading system for a trading session to happens. 
    This includes:
     - Alpha Model
     - Risk Model
     - Transaction Cost Model
     - Fee Model
     - etc...

    for Portfolio construction & Execution mechanism.
    Parameters
    ----------
    universe : `Universe`
        The Asset Universe.
    broker : `Broker`
        The Broker to execute orders against.
    broker_portfolio_id : `str`
        The specific broker portfolio to send orders to.
    data_handler : `DataHandler`
        The data handler instance used for all market/fundamental data.
    alpha_model : `AlphaModel`
        The alpha model used within the portfolio construction.
    risk_model : `AlphaModel`, optional
        An optional risk model used within the portfolio construction.
    long_only : `Boolean`, optional
        Whether to invoke the long only order sizer or allow
        long/short leveraged portfolios. Defaults to long/short leveraged.
    submit_orders : `Boolean`, optional
        Whether to actually submit generated orders. Defaults to no submission.
    """

    def __init__(
        self,
        universe,
        broker,
        broker_portfolio_id,
        data_handler,
            long_only:bool = False,
            submit_orders:bool = False,
            **kwargs
    ):
        #!--| INTERACTIVE COMPONENTS - ESSENTIAL INHERITANCES FOR A QUANT SYSTEM
        self.data_handler = data_handler
        self.universe = universe # Strategy Universe
        self.broker = broker # Broker has its own universe -> can be the same as Strategy's
        self.broker_portfolio_id = broker_portfolio_id

        #!---| BUILDING PORTFOLIO CONSTRUCTION MODEL w/ QUANT MODELS (alpha, risk, optimizer, cost, etc...)
        """
        Initialize the various models for the quantitative trading strategy.
        TODO: Add TransactionCostModel
        """
        self.long_only = long_only # True = Able to manage cash | False = Harder to manage Cash -> leverageable
        self.order_sizer = self._init_order_sizer(**kwargs)
        self.optimizer = self._init_optimizer(**kwargs)
        self.alpha_model = self._init_alpha_model(**kwargs)
        self.risk_model = self._init_risk_model(**kwargs)
        self.portfolio_construction_model = PortfolioConstructionModel(
                                                    order_sizer = self.order_sizer,
                                                    optimizer = self.optimizer,
                                                    alpha_model = self.alpha_model,
                                                    risk_model = self.risk_model,
                                                        **self._interactive_components
                                                                )

        #!---| ORDERS EXECUTION MODEL
        self.submit_orders = submit_orders
        self.execution_algo = self._init_execution_algo(**kwargs)
        self.execution_handler = ExecutionHandler(
                                    submit_orders = self.submit_orders,
                                    execution_algo = self.execution_algo,
                                        **self._interactive_components
                                                )
        
        #!---| REBALANCING SCHEDULE
        self.rebalance_schedule = self._init_rebalance_event_times(**kwargs)
    
    @property
    def _interactive_components(self):
        return {
            'data_handler' : self.data_handler,
            'universe' : self.universe,
            'broker' : self.broker,
            'broker_portfolio_id': self.broker_portfolio_id
        }

    # TODO: Add more event classifcations from dt for more QTS actions (__call__)
    def _is_rebalance_event(self, dt):
        """
        Checks if the provided timestamp is part of the rebalance
        schedule of the backtest.
        Parameters
        ----------
        dt : `pd.Timestamp`
            The timestamp to check the rebalance schedule for.
        Returns
        -------
        `Boolean`
            Whether the timestamp is part of the rebalance schedule.
        """
        return dt in self.rebalance_schedule
    
    #!---| QTS Initializations
    def _init_execution_algo(self,**kwargs):
        execution = None
        if 'execution_algo' in kwargs:
            try:
                assert callable(execution_algo)
                execution = kwargs['execution_algo']
            except:
                print("execution_algo needs to be callable when assigning to QTS. Defaulted to NaiveMarketOrderExecution")
        if execution is None:
            execution = MarketOrderNaiveExecution()
        return execution

    def _init_order_sizer(self, **kwargs):
        """
        Depending upon whether the quant trading system has been
        set to be long only, determine the appropriate order sizing
        mechanism.
        Returns
        -------
        `OrderSizer`
            The order sizing mechanism for the portfolio construction.
        """
        input_kwargs = {}

        if self.long_only:
            if 'cash_buffer_percentage' not in kwargs:
                if settings.PRINT_EVENTS:
                    print(
                    'Long only portfolio specified for Quant Trading System '
                    'but no cash buffer percentage supplied. Default to 0.1.'
                        )
                buffer_pct = 0.1
            else:
                buffer_pct = kwargs['cash_buffer_percentage']
            order_sizer = LongOnlyMoneyWeightedOrderSizer
            input_kwargs['cash_buffer_percentage'] = buffer_pct
        
        else:
            if 'gross_leverage' not in kwargs:
                if settings.PRINT_EVENTS:
                    print(
                    'Long/short leveraged portfolio specified for Quant '
                    'Trading System but no gross leverage percentage supplied. Default to 1.0.'
                    )
                gross_leverage = 1.0
            else:
                gross_leverage = kwargs['gross_leverage']

            order_sizer = LongShortLeveragedOrderSizer
            input_kwargs['gross_leverage'] = gross_leverage
        
        return order_sizer(
                    broker = self.broker,
                    broker_portfolio_id = self.broker_portfolio_id,
                    data_handler = self.data_handler,
                    **input_kwargs
                        )
     
    def _init_optimizer(self, **kwargs):
        optimizer = (
            kwargs['optimizer'] if 'optimizer' in kwargs
                 else FixedWeightPortfolioOptimiser
                 )
        if optimizer and optimizer.__class__ == type: #--| not yet initialized and not None
            optimizer = optimizer(
                        **{
                            **self._interactive_components,
                            **({} if 'optimizer_init' not in kwargs else kwargs['optimizer_init'].copy())
                          }
                                )
        return optimizer

    def _init_alpha_model(self, **kwargs):
        alpha_model = (
            kwargs['alpha_model'] if 'alpha_model' in kwargs
                 else SingleFixedWeightsAlpha
                 )
        
        if alpha_model and alpha_model.__class__ == type: #--| not yet initialized and not None
            alpha_model = alpha_model(
                        **{
                            **self._interactive_components,
                            **({} if 'alpha_model_init' not in kwargs else kwargs['alpha_model_init'].copy())
                          }
                                )   
        return alpha_model

    def _init_risk_model(self, **kwargs):
        risk_model = (
            kwargs['risk_model'] if 'risk_model' in kwargs
                 else None
                 )
        
        if risk_model and risk_model.__class__ == type: #--| not yet initialized and not None
            risk_model = risk_model(
                        **{
                            **self._interactive_components,
                            **({} if 'risk_model_init' not in kwargs else kwargs['risk_model_init'].copy())
                          }
                                )   
        return risk_model

    def _init_rebalance_event_times(self,**kwargs):
        """
        Creates the list of rebalance timestamps used to determine when
        to execute the quant trading strategy throughout the backtest.
        Returns
        -------
        `List[pd.Timestamp]`
            The list of rebalance timestamps.
        """
        if 'rebalance' not in kwargs:
            if settings.PRINT_EVENTS:
                print("No specified rebalance. Defaulting rebalancing to 'end_of_month'")
            kwargs['rebalance'] = 'end_of_month'
        
        if kwargs['rebalance'] == 'weekly':
            if 'weekday' not in kwargs:
                if 'rebalance_weekday' not in kwargs:
                    raise Exception("Missing 'rebalance_weekday'/'weekday' to initialize QTS. Need to be assigned for 'weekly' rebalancing.")
    
        rebalancer = RebalanceHandler(**kwargs)
        return rebalancer.output_rebalances()

    def __call__(self, dt, stats=None):
        """
        Construct the portfolio and (optionally) execute the orders
        with the broker.
        Parameters
        ----------
        dt : `pd.Timestamp`
            The current time.
        stats : `dict`, optional
            An optional statistics dictionary to append values to
            throughout the simulation lifetime.
        Returns
        -------
        `None`
        """
        if self._is_rebalance_event(dt):
            if settings.PRINT_EVENTS:
                print("(%s) - trading logic and rebalance" % dt)
            # Construct the target portfolio
            rebalance_orders = self.portfolio_construction_model(dt, stats=stats)
            # Execute the orders
            self.execution_handler(dt, rebalance_orders)