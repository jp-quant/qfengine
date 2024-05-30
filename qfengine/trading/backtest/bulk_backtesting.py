
from qfengine.data.backtest_data_handler import BacktestDataHandler
from qfengine.trading.backtest import BacktestTradingSession
from qfengine.statistics.strategy_statistics import StrategyStatistics
from qfengine.data.price.daily_price.daily_price_mysql import DailyPriceMySQL
from qfengine.asset.equity import Equity
from qfengine.asset.universe.static import StaticUniverse
from qfengine import settings

from typing import Union, Dict, List, Tuple
import itertools
import pandas as pd
import concurrent.futures
import os


def _generate_backtest_trading_sessions(
                            BTS_params_grid,
                            data_handler = None,
                            include_default_benchmark=True
):
    def get_bts_name(bts):
        return ",".join(
                            [
            (qts_component + "=" + str(getattr(bts.qts,qts_component)))
                for qts_component in ['universe','alpha_model', 'risk_model', 'optimizer']
                            ]
                    )
    
    settings.PRINT_EVENTS = False
    data_handler = data_handler or BacktestDataHandler(
                        price_data_sources = DailyPriceMySQL(Equity),
                                 )
    for s in data_handler.price_data_sources:
        if isinstance(s, DailyPriceMySQL):
            s.executeSQL("set global max_connections = 50000")
            s.executeSQL("set global innodb_buffer_pool_size = 6000000000")
    all_params = [
            dict(zip(BTS_params_grid.keys(), v)) 
            for v in itertools.product(*BTS_params_grid.values())
                ]
    
    BTS = {}
    for kwargs in all_params:
        new_bts = BacktestTradingSession(
                                    data_handler = data_handler.copy(),
                                    **kwargs
                                    )
        new_bts_name = get_bts_name(new_bts)
        print("--------------| New Backtest Trading Session Initialized |--------------")
        print(new_bts_name)
        print(new_bts.start_dt, "to", new_bts.end_dt)
        print("------------------------------------------------------------------------")
        print("")
        BTS[new_bts_name] = new_bts

    if include_default_benchmark:
        BTS['benchmark'] = BacktestTradingSession(
                            data_handler = data_handler.copy(),
                            universe = StaticUniverse(['SPY']),
                )
    settings.PRINT_EVENTS = True
    
    return BTS

def _run_session(
                bts,
                name = None
):
    stats = {'target_allocations': []}
    if settings.PRINT_EVENTS:
        print("Beginning backtest simulation...")
        if name:
            print('Session: ' + name)
    for event in bts.sim_engine:
        # Output the system event and timestamp
        dt = event.ts
        if settings.PRINT_EVENTS:
            print("[%s]: (%s) - %s" % (bts.portfolio_id, dt, event.event_type))

        bts.broker.update(dt)

        if bts.signals is not None and event.event_type == 'market_close':
            bts.signals.update(dt)
        
        bts.qts(dt, stats = stats)

        if event.event_type == "market_close":
            if bts.burn_in_dt is not None:
                if dt >= bts.burn_in_dt:
                    bts._update_equity_curve(dt)
            else:
                bts._update_equity_curve(dt)
    bts.target_allocations = stats['target_allocations']

def _run_backtest_trading_sessions_in_parallel(
                        sessions:Union[List,Dict],
                        print_events = True,
):
    if isinstance(sessions, list):
        sessions = {("session_" + str(sessions.index(s))) : s for s in sessions}
    
    _toreset = settings.PRINT_EVENTS
    settings.PRINT_EVENTS = print_events
    t0 = pd.Timestamp.now()
    result = list(
        concurrent.futures.ThreadPoolExecutor().map(
                                                _run_session, 
                                                *zip(*((bts,name) for name,bts in sessions.items()))
                                                    )
                )
    tf = pd.Timestamp.now()
    print(tf - t0)
    settings.PRINT_EVENTS = _toreset

def save_ran_sessions(
                sessions:Union[List,Dict],
                save_dir_path,
):
    if isinstance(sessions, list):
        sessions = {("session_" + str(sessions.index(s))) : s for s in sessions}
    _path = save_dir_path
    if not os.path.exists(_path):
        os.makedirs(_path)
    for n,bts in sessions.items():
        bts.get_equity_curve().to_csv(
                            os.path.join(
                                        _path,
                                        ".".join([n,'csv'])
                                        )
                                    )

def close_sessions(
                BTS,
):
    for bts in BTS.values():
        for price_source in bts.data_handler.price_data_sources:
            price_source._conn.close()


def run(
        BTS = None,
        data_handler = None,
        BTS_params_grid = None,
        include_default_benchmark = True,
        print_events = True,
        save_dir_path = None,
)->dict: # returns strategy statistics
    #!----------------------------------|
    save_dir_path = os.path.join(
                            os.getcwd(),'backtest_results'
                                ) if save_dir_path is None else save_dir_path
    if BTS is None:
        assert BTS_params_grid is not None
        assert data_handler is not None
        BTS = _generate_backtest_trading_sessions(BTS_params_grid,
                                            data_handler = data_handler,
                                            include_default_benchmark = include_default_benchmark,
                                            )


    _run_backtest_trading_sessions_in_parallel(BTS,
                                            print_events = print_events,
                                            )


    save_ran_sessions(
                sessions = BTS,
                save_dir_path = save_dir_path
                    )

    close_sessions(BTS)
    
    return {
        name: StrategyStatistics(
                    strategy_equity = bts.get_equity_curve(),
                    title = name
                            ) for name,bts in BTS.items()
            }


def analyze_stats(
                STATS:dict
): # analyze stats returned from run() - plotting performance results, etc...
    STAT_RESULTS = pd.DataFrame({
        name: stat.get_results(stat.strategy_equity) for name,stat in STATS.items()
                        }).T
        
    equity = pd.DataFrame(dict(STAT_RESULTS.equity))
    returns = pd.DataFrame(dict(STAT_RESULTS.returns))
    cum_returns = pd.DataFrame(dict(STAT_RESULTS.cum_returns))

    top_sharpe = STAT_RESULTS.sharpe.sort_values().index.values[-10:]

    for n in top_sharpe:
        STATS[n].plot_results()
    
    print("Top Sharpe:")
    print(top_sharpe)



_sample_script = (
'''

BTS_params_grid = {
        #----| Static Universe(s)
        **{
            "universe" : [
                        StaticUniverse(
                            data_handler.assetsList(sector = 'Others'),
                            sector = 'Others'
                               )
                        ],
          },

        #---| Naive Alpha & Risk Signals
        **{
            'alpha_model' : [
                DailyCloseExpectedReturnsAlpha,
                    ],

            'risk_model' : [
                SampleCovarianceRiskModel,
                RMTCovarianceRiskModel
                    ],
        }



        #---| Tailing Alpha & Risk Signals
        **{ 
            'alpha_model' : [
                        DailyCloseTailingExpectedReturnsAlpha
                        ],
                'alpha_model_init' : [
                            {'tailing_time_delta' : time_delta} 
                                    for time_delta in ['1y', '180d', '90d']
                                ],
        'risk_model' : [
                        TailingSampleCovarianceRiskModel,
                        TailingRMTCovarianceRiskModel
                        ],
        'risk_model_init' : [
                        {'tailing_time_delta' : time_delta} 
                                for time_delta in ['1y', '180d', '90d']
                             ],

        },

        #----| Portfolio Optimizers  
        **{
        'optimizer' : [
                        MinimumVarianceOptimizer,
                        SharpeRatioOptimizer,
                        MeanVarianceOptimizer,
                    ],
        }
}


BTS = _generate_backtest_trading_sessions(BTS_params_grid, data_handler)




run(BTS)





all_sessions = list(BTS.keys())
batch_size = 10 # parallelize 10 sessions per run
STATS = {}
batch_number = 1
while len(STATS) != len(all_sessions):
    left_over_sessions = [s for s in all_sessions if s not in STATS]
    sessions_to_run = left_over_sessions[:batch_size]
    BTS_batch = {s:BTS[s] for s in sessions_to_run}

    print("----------------------------------------")
    print("Running Batch #%s:" %str(batch_number))
    for s in sessions_to_run:
        print("  "+s)
    print("----------------------------------------")
    
    BTS_stats = run(BTS_batch)
    analyze_stats(BTS_stats)
    for name,stats in BTS_stats.items():
        STATS[name] = stats
    batch_number += 1





'''
)