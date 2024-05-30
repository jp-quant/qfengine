import os

import pandas as pd

from qfengine import settings
from qfengine.asset.equity import Equity

from qfengine.asset.universe.static import StaticUniverse
from qfengine.broker.simulated import SimulatedBroker
from qfengine.broker.fee_model.zero_fee_model import ZeroFeeModel
from qfengine.data.backtest_data_handler import BacktestDataHandler
from qfengine.data.price.daily_price.daily_price_mysql import DailyPriceMySQL
from qfengine.exchange.simulated import SimulatedExchange
from qfengine.simulation.daily_bday import DailyBusinessDaySimulationEngine
from qfengine.system.quant_system import QuantTradingSystem

from qfengine.system.rebalance.buy_and_hold import BuyAndHoldRebalance
from qfengine.system.rebalance.daily import DailyRebalance
from qfengine.system.rebalance.end_of_month import EndOfMonthRebalance
from qfengine.system.rebalance.weekly import WeeklyRebalance
from qfengine.trading.trading_session import TradingSession

DEFAULT_ACCOUNT_NAME = 'Backtest Simulated Broker Account'
DEFAULT_PORTFOLIO_ID = '000001'
DEFAULT_PORTFOLIO_NAME = 'Backtest Simulated Broker Portfolio'



class BacktestTradingSession(TradingSession):
    """
        Encaspulates a full trading simulation backtest with externally
        provided instances for each module.
        Utilises sensible defaults to allow straightforward backtesting of
        less complex trading strategies.
        Parameters
        ----------
        start_dt : `pd.Timestamp`
            The starting datetime (UTC) of the backtest.
        end_dt : `pd.Timestamp`
            The ending datetime (UTC) of the backtest.
        universe : `Universe`
            The Asset Universe to utilise for the backtest.
        alpha_model : `AlphaModel`
            The signal/forecast alpha model for the quant trading strategy.
        risk_model : `RiskModel`
            The optional risk model for the quant trading strategy.
        signals : `SignalsCollection`, optional
            An optional collection of signals used in the trading models.
        initial_cash : `float`, optional
            The initial account equity (defaults to $1MM)
        rebalance : `str`, optional
            The rebalance frequency of the backtest, defaulting to 'weekly'.
        account_name : `str`, optional
            The name of the simulated broker account.
        portfolio_id : `str`, optional
            The ID of the portfolio being used for the backtest.
        portfolio_name : `str`, optional
            The name of the portfolio being used for the backtest.
        long_only : `Boolean`, optional
            Whether to invoke the long only order sizer or allow
            long/short leveraged portfolios. Defaults to long/short leveraged.
        fee_model : `FeeModel` class instance, optional
            The optional FeeModel derived subclass to use for transaction cost estimates.
        burn_in_dt : `pd.Timestamp`, optional
            The optional date provided to begin tracking strategy statistics,
            which is used for strategies requiring a period of data 'burn in'
    """
    def __init__(self,
                start_dt=None,
                end_dt=None,
                initial_cash=1e6,
                burn_in_dt=None,
                account_name = DEFAULT_ACCOUNT_NAME,
                portfolio_id = DEFAULT_PORTFOLIO_ID,
                portfolio_name = DEFAULT_PORTFOLIO_NAME,
                long_only = False,
                signals = None,
                **kwargs #! QUANT MODELS ---- [ALPHA, RISK, OPTIMIZER, ETC...]
    ):
        #---| Part One - Fixed Vars
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.signals = signals
        self.initial_cash = initial_cash
        self.account_name = account_name
        self.portfolio_id = portfolio_id
        self.portfolio_name = portfolio_name
        self.long_only = long_only
        self.burn_in_dt = burn_in_dt
        self.equity_curve = []
        self.target_allocations = []

        #---| Part Two - 2nd Level Init [universe, exchange, data_handler, sim_engine, broker, rebalancings]
        self.data_handler = self._init_data_handler(**kwargs)
        self.universe = self._init_universe(**kwargs)
        self.sim_engine = self._init_simulation_engine(**kwargs)
        self.exchange = self._init_exchange(**kwargs)
        self.broker = self._init_broker(**kwargs)
   
        #---| Finally - QTS
        self.qts = self._init_quant_trading_system(**kwargs)


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

    #!---| INIT FUNCTIONS
    def _init_data_handler(self, **kwargs):
        """
        Creates a DataHandler instance to load the asset pricing data
        used within the backtest.
        TODO: Currently defaults to CSV data sources of daily bar data in
        the YahooFinance format.
        Parameters
        ----------
        `BacktestDataHandler` or None
            The (potential) backtesting data handler instance.
        Returns
        -------
        `BacktestDataHandler`
            The backtesting data handler instance.
        """
        data_handler = None
        if 'data_handler' in kwargs:
            data_handler = kwargs['data_handler']
        else:
            if settings.PRINT_EVENTS:
                print(
                    'No assigned data_handler for BTS. '
                    'Defaulting to BacktestDataHandler with Equity data_sources = [DailyPriceMySQL].'
                    )
            # TODO: Only equities are supported by QSTrader for now.
            data_handler = BacktestDataHandler(
                price_data_sources = [DailyPriceMySQL(Equity)]
            )
        
        return data_handler

    def _init_dt_range(self, **kwargs):
        try:
            min_start = self.data_handler.get_assets_earliest_available_dt(self.universe.get_assets())
            max_end = self.data_handler.get_assets_latest_available_dt(self.universe.get_assets())
        except:
            raise
        
        
        if self.start_dt:
            if (self.start_dt < min_start):
                if settings.PRINT_EVENTS:
                    print("Assigned 'start_dt' %s is too early for data availability in current data_handler." %self.start_dt)
                    print("Resetting 'start_dt' = %s" %min_start)
                self.start_dt = min_start
        else:
            self.start_dt = min_start

        if self.end_dt:
            if (self.start_dt > max_end):
                if settings.PRINT_EVENTS:
                    print("Assigned 'end_dt' %s is too late for data availability in current data_handler." %self.end_dt)
                    print("Resetting 'end_dt' = %s" %max_end)
                self.end_dt = max_end
        else:
            self.end_dt = max_end
  
    def _init_simulation_engine(self, **kwargs):
        """
        Create a simulation engine instance to generate the events
        used for the quant trading algorithm to act upon.
        TODO: Currently hardcoded to daily events
        Returns
        -------
        `SimulationEngine`
            The simulation engine generating simulation timestamps.
        """
        if 'init_dt_range' in kwargs:
            if kwargs['init_dt_range']:
                self._init_dt_range(**kwargs)
        if self.start_dt is None:
            self._init_dt_range(**kwargs)
        assert self.start_dt is not None
        assert self.end_dt is not None
        
        sim_engine = None
        if 'sim_engine' in kwargs:
            try:
                iter(kwargs['sim_engine'])
            except:
                if settings.PRINT_EVENTS:
                    print("sim_engine assigned is not iterable. Implement __iter__() when designing it. Defaulting to DailyBusinessDaySimulationEngine.")
            else:
                sim_engine = kwargs['sim_engine']
        if sim_engine is None:
            sim_engine = DailyBusinessDaySimulationEngine(
                                self.start_dt, self.end_dt,
                                **kwargs
                                            )
        return sim_engine
    
    def _init_universe(self, **kwargs):
        if 'universe' not in kwargs:
            if settings.PRINT_EVENTS:
                print(
                    'No assigned universe (universe=None) to QTS. ' 
                    'Defaulting to full universe from initialized data_handler.'
                    )
            universe = self.data_handler.universe
        else:
            universe = kwargs['universe']

        return universe
            
    def _init_exchange(self, **kwargs):
        """
        Generates a simulated exchange instance used for
        market hours and holiday calendar checks.
        Returns
        -------
        `SimulatedExchanage`
            The simulated exchange instance.
        """
        if 'exchange' in kwargs:
            return kwargs['exchange']
        else:
            return SimulatedExchange(self.start_dt)

    def _init_broker(self, **kwargs):
        """
        Create the SimulatedBroker with an appropriate default
        portfolio identifiers.
        Returns
        -------
        `SimulatedBroker`
            The simulated broker instance.
        """
        if 'fee_model' in kwargs:
            fee_model = kwargs['fee_model']
        else:
            fee_model = ZeroFeeModel()
        
        if 'broker' not in kwargs:
            broker = SimulatedBroker(
                start_dt = self.start_dt,
                exchange = self.exchange,
                data_handler = self.data_handler,
                account_id=self.account_name,
                initial_funds=self.initial_cash,
                fee_model=fee_model
            )
        else:
            broker = kwargs['broker']
        
        broker.create_portfolio(self.portfolio_id, self.portfolio_name)
        broker.subscribe_funds_to_portfolio(self.portfolio_id, self.initial_cash)
        return broker

    def _init_quant_trading_system(self, **kwargs):
        """
        Creates the quantitative trading system with the provided
        alpha model.
        TODO: All portfolio construction/optimisation is hardcoded for sensible defaults in portfolio_construction_model.
        Returns
        -------
        `QuantTradingSystem`
            The quantitative trading system.
        """
        qts_kwargs = {arg:val for arg,val in kwargs.items() if arg not in dir(self)}
        qts_kwargs['start_dt'] = self.start_dt
        qts_kwargs['end_dt'] = self.end_dt
        
        qts = QuantTradingSystem(
                        universe = self.universe,
                        broker = self.broker,
                        broker_portfolio_id = self.portfolio_id,
                        data_handler = self.data_handler,
                        long_only = self.long_only,
                        submit_orders = True,
                        **qts_kwargs
                        
                    )
        return qts

    def _update_equity_curve(self, dt):
        """
        Update the equity curve values.
        Parameters
        ----------
        dt : `pd.Timestamp`
            The time at which the total account equity is obtained.
        """
        self.equity_curve.append(
            (dt, self.broker.get_account_total_equity()["master"])
        )


    #!---| VISIBLE FUNCTIONS
    def output_holdings(self):
        """
        Output the portfolio holdings to the console.
        """
        self.broker.portfolios[self.portfolio_id].holdings_to_console()

    def get_equity_curve(self):
        """
        Returns the equity curve as a Pandas DataFrame.
        Returns
        -------
        `pd.DataFrame`
            The datetime-indexed equity curve of the strategy.
        """
        equity_df = pd.DataFrame(
            self.equity_curve, columns=['Date', 'Equity']
        ).set_index('Date')
        equity_df.index = equity_df.index.date
        return equity_df

    def get_target_allocations(self):
        """
        Returns the target allocations as a Pandas DataFrame
        utilising the same index as the equity curve with
        forward-filled dates.
        Returns
        -------
        `pd.DataFrame`
            The datetime-indexed target allocations of the strategy.
        """
        equity_curve = self.get_equity_curve()
        alloc_df = pd.DataFrame(self.target_allocations).set_index('Date')
        alloc_df.index = alloc_df.index.date
        alloc_df = alloc_df.reindex(index=equity_curve.index, method='ffill')
        if self.burn_in_dt is not None:
            alloc_df = alloc_df[self.burn_in_dt:]
        return alloc_df

    def run(self, results=False):
        """
        Execute the simulation engine by iterating over all
        simulation events, rebalancing the quant trading
        system at the appropriate schedule.
        Parameters
        ----------
        results : `Boolean`, optional
            Whether to output the current portfolio holdings
        """
        if settings.PRINT_EVENTS:
            print("Beginning backtest simulation...")

        stats = {'target_allocations': []}

        for event in self.sim_engine:
            # Output the system event and timestamp
            dt = event.ts
            if settings.PRINT_EVENTS:
                print("(%s) - %s" % (dt, event.event_type))

            # Update the simulated broker
            self.broker.update(dt)

            # Update any signals on a daily basis
            if self.signals is not None and event.event_type == "market_close":
                self.signals.update(dt)

            # Run QTS on every event - rebalance config resides in QTS
            self.qts(dt, stats=stats)

            # Out of market hours we want a daily
            # performance update, but only if we
            # are past the 'burn in' period
            if event.event_type == "market_close":
                if self.burn_in_dt is not None:
                    if dt >= self.burn_in_dt:
                        self._update_equity_curve(dt)
                else:
                    self._update_equity_curve(dt)

        self.target_allocations = stats['target_allocations']

        # At the end of the simulation output the
        # portfolio holdings if desired
        if results:
            self.output_holdings()

        if settings.PRINT_EVENTS:
            print("Ending backtest simulation.")



