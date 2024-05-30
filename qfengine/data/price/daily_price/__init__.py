#--| Pseudos



''' PriceHandler, Strategy, PortfolioHandler, PositionSizer, RiskManager and ExecutionHandler. 
    The main components are the

    
    
    
    They handle portfolio/order management system and
    brokerage connection functionality.

    The system is event-driven and communicates via an events queue using subclassed Event
    objects. The full list of components is as follows:

    • Event - All "messages" of data within the system are encapsulated in an Event object. The various events include TickEvent, BarEvent, SignalEvent, SentimentEvent,
    OrderEvent and FillEvent.

    • Position - This class encapsulates all data associated with an open position in an asset.
    That is, it tracks the realised and unrealised profit and loss (PnL) by averaging the multiple
    "legs" of the transaction, inclusive of transaction costs.

    • Portfolio - The Portfolio class encapsulates a list of Positions, as well as a cash
    balance, equity and PnL. This object is used by the PositionSizer and RiskManager
    objects for portfolio construction and risk management purposes.

    • PortfolioHandler - The PortfolioHandler class is responsible for the management of
    the current Portfolio, interacting with the RiskManager and PositionSizer as well as
    submitting orders to be executed by an ExecutionHandler.

    • PriceHandler - The PriceHandler and derived subclasses are used to ingest financial
    asset pricing data from various sources. In particular, there are separate class hierarchies
    for bar and tick data.

    • Strategy - The Strategy object and subclasses contain the "alpha generation" code for
    creating trading signals.

    • PositionSizer - The PositionSizer class provides the PortfolioHandler with guidance
    on how to size positions once a strategy signal is received. For instance the PositionSizer
    could incorporate a Kelly Criterion approach or carry out monthly rebalancing of a fixedweight portfolio.

    • RiskManager - The RiskManager is used by the PortfolioHandler to verify, modify
    or veto any suggested trades that pass through from the PositionSizer, based on the
    current composition of the portfolio and external risk considerations (such as correlation
    to indices or volatility).

    • ExecutionHandler - This object is tasked with sending orders to brokerages and receiving
    "fills". For backtesting this behaviour is simulated, with realistic fees taken into account.

    • Statistics - This is used to produce performance reports from backtests. A "tearsheet" capability has recently been added providing detailed statistics on equity curve performance,
    with benchmark comparison.

    • Backtest - Encapsulates the event-driven behaviour of the system, including the handling
    of the events queue. Requires knowledge of all other components in order to simulate a full
    backtest.

'''
