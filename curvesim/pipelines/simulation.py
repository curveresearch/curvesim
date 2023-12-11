import gin

from curvesim.metrics.results import make_results
from curvesim.pipelines import run_pipeline


@gin.configurable
class SimulationContext:
    """
    An Inversion-of-Control (IoC) container for the simulation application
    that uses Gin for dependency injection.

    While Gin doesn't require such a container, this makes configuration
    more explicit.
    """

    def __init__(
        self,
        time_sequence,
        reference_market,
        sim_market_factory,
        sim_market_parameters,
        trader_class,
        log_class,
        metric_classes,
    ):
        """
        all constructor args will be Gin injected
        """
        self.time_sequence = time_sequence
        self.reference_market = reference_market
        self.sim_market_factory = sim_market_factory
        self.sim_market_parameters = sim_market_parameters
        self.trader_class = trader_class
        self.log_class = log_class
        self.metric_classes = metric_classes

    def executor(
        self,
        sim_market,
    ):
        """
        Executes a trading strategy for the given sim market
        and time sequence.
        """
        # These all use Gin injection, completely separating
        # any need to consider constructor dependencies from
        # this logic.
        trader = self.trader_class()
        log = self.log_class()
        sim_market.prepare_for_run()

        for timestep in self.time_sequence:
            sim_market.prepare_for_trades(timestep)
            sample = self.reference_market.prices(timestep)
            trade_data = trader.process_time_sample(sample, sim_market)
            log.update(price_sample=sample, trade_data=trade_data)

        return log.compute_metrics()

    @property
    def configured_sim_markets(
        self,
    ):
        sim_market_parameters = self.sim_market_parameters
        sim_market_factory = self.sim_market_factory

        initial_params = sim_market_parameters.initial_parameters
        all_run_params = sim_market_parameters.run_parameters

        yield sim_market_factory.create(**initial_params)

        for run_params in all_run_params:
            init_kwargs = initial_params.copy()
            init_kwargs.update(run_params)
            sim_market = sim_market_factory.create(**init_kwargs)
            yield sim_market

    def run_simulation(
        self,
        ncpu=None,
    ):
        configured_sim_markets = self.configured_sim_markets
        initial_sim_market = next(configured_sim_markets)
        output = run_pipeline(configured_sim_markets, self.executor, ncpu)

        metrics = [Metric(pool=initial_sim_market) for Metric in self.metric_classes]
        results = make_results(*output, metrics)
        return results
