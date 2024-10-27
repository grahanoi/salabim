import salabim as sim
import math
from base_library import BasicEntity, ResourceStation, QueueStation
import statistics as stat
import pandas as pd

# Time units conversion constants
HOUR = 1
DAY = 24 * HOUR
ANIMATION = True
ANIMATION_SPEED = 2

# Simulation parameters
RUN_DURATION = 30 * DAY  # Total simulation run time

BILL_OF_MATERIALS = {
    "product_1": {
        "initial_stock": 0,
        "reorder_point": None,
        "reorder_quantity": None,
        "duration": 1,
        "weight": 1200.55,
        "parts": {
            "dichlorotris": 1,
            "ehtylenediamine": 1,
            "propan_2_ol": 1,
            "trimethy_octadienal": 1,
            "sodium_methoxide": 1,
            "sodium_bicarbonate": 1,
        },
    },
    "product_2": {
        "initial_stock": 0,
        "reorder_point": None,
        "reorder_quantity": None,
        "duration": 1,
        "weight": 16266.65,
        "parts": {
            "homofarnesol": 1,
            "biocatalyst_shc": 1,
            "succinic_acid": 1,
            "phosphoric_acid": 1,
            "sodium_hydroxide": 1,
            "sodium_dodecyl_sulfate": 1,
        },
    },
    "dichlorotris": {
        "initial_stock": 1000,
        "reorder_point": None,
        "reorder_quantity": None,
        "duration": 0,
        "weight": 0.5,
        "parts": dict(),
    },
    "ehtylenediamine": {
        "initial_stock": 1000,
        "reorder_point": None,
        "reorder_quantity": None,
        "duration": 0,
        "weight": 0.05,
        "parts": dict(),
    },
    "propan_2_ol": {
        "initial_stock": 1000,
        "reorder_point": None,
        "reorder_quantity": None,
        "weight": 100,
        "duration": 0,
        "parts": dict(),
    },
    "trimethy_octadienal": {
        "initial_stock": 1000,
        "reorder_point": None,
        "reorder_quantity": None,
        "duration": 0,
        "weight": 5000,
        "parts": dict(),
    },
    "sodium_methoxide": {
        "initial_stock": 1000,
        "reorder_point": None,
        "reorder_quantity": None,
        "duration": 0,
        "weight": 250,
        "parts": dict(),
    },
    "sodium_bicarbonate": {
        "initial_stock": 1000,
        "reorder_point": None,
        "reorder_quantity": None,
        "duration": 0,
        "weight": 500,
        "parts": dict(),
    },
    "homofarnesol": {
        "initial_stock": 1000,
        "reorder_point": None,
        "reorder_quantity": None,
        "duration": 0,
        "weight": 12800,
        "parts": dict(),
    },
    "biocatalyst_shc": {
        "initial_stock": 1000,
        "reorder_point": None,
        "reorder_quantity": None,
        "duration": 0,
        "weight": 16.65,
        "parts": dict(),
    },
    "succinic_acid": {
        "initial_stock": 1000,
        "reorder_point": None,
        "reorder_quantity": None,
        "weight": 2400,
        "duration": 0,
        "parts": dict(),
    },
    "phosphoric_acid": {
        "initial_stock": 1000,
        "reorder_point": None,
        "reorder_quantity": None,
        "duration": 0,
        "weight": 25,
        "parts": dict(),
    },
    "sodium_hydroxide": {
        "initial_stock": 1000,
        "reorder_point": None,
        "reorder_quantity": None,
        "duration": 0,
        "weight": 25,
        "parts": dict(),
    },
    "sodium_dodecyl_sulfate": {
        "initial_stock": 1000,
        "reorder_point": None,
        "reorder_quantity": None,
        "duration": 0,
        "weight": 1000,
        "parts": dict(),
    },
}


class QueueMonitor(sim.Component):
    """A component that monitors and records the state of a queue over time."""

    def setup(self, queue: sim.Queue, interval: int = 1 * HOUR):
        """Setup method for initializing the queue monitor."""
        self.queue = queue
        self.interval = interval
        self.data = []

    def process(self):
        """Process method to continuously monitor and record the queue length over time."""
        while True:
            self.data.append((self.env.now(), len(self.queue)))
            self.hold(self.interval)


class ConstantRateSource(sim.Component):
    """A source component that generates batches at a constant rate."""

    def setup(self, product_type, arrival_rate):
        """Setup method for initializing the constant inter-arrival time."""
        self.arrival_rate = arrival_rate
        self.constant_inter_arrival_time = sim.Exponential(mean=1 / self.arrival_rate)
        self.product_type = product_type

    def process(self):
        """Process method to continuously generate batches at the specified constant rate."""
        while True:
            self.hold(self.constant_inter_arrival_time)
            Batch(type=self.product_type)
            self.env.n_batches_created[self.product_type] += 1


class Part(sim.Component):
    def setup(self, type, parts=None):
        self.type = type
        self.parts = parts


class ReactionServer(sim.Component):
    """Custom reaction server that handles processing and cleaning after every 5 batches."""

    def setup(
        self,
        capacity=1,
        cleaning_time_product1=2,
        cleaning_time_product2=10,
        cleaning_time_product_change=0,
        x=0,
        y=0,
        display_name="Reaction",
        **kwargs,
    ):
        self.capacity = capacity
        self.cleaning_time_product1 = cleaning_time_product1
        self.cleaning_time_product2 = cleaning_time_product2
        self.cleaning_time_product_change = cleaning_time_product_change
        self.resource = sim.Resource(capacity=capacity, name="ReactionServer")
        self.batches_processed = 0
        self.cleaning = sim.State("cleaning", value=False)
        self.current_claimer = None
        self.last_claimer = None
        # For animation, we can create a station
        self.station = ResourceStation(
            name="Reaction",
            capacity=capacity,
            x=x,
            y=y,
            display_name=display_name,
            **kwargs,
        )
        self.anim_queue = sim.AnimateQueue(
            self.resource.requesters(),
            x=x,
            y=y + 40,
            direction="n",
            max_length=10,
            title="",
            # title=lambda t: str(len(self.requesters())),  # t
            # titlecolor=mm.LABEL_COLOR,
            # titlefont=mm.FONT,
            # titlefontsize=mm.FONT_SIZE,
        )

    def process(self):
        while True:
            if self.batches_processed >= self.env.n_batches_product1:
                self.batches_processed = 0
                self.cleaning.set(True)
                self.resource.set_capacity(0)  # Make resource unavailable
                if self.current_claimer == "product_1":
                    self.hold(self.env.cleaning_time_reaction_product1)
                else:
                    self.hold(self.env.cleaning_time_reaction_product2)
                if (
                    self.current_claimer is not None
                    and self.current_claimer != self.last_claimer
                ):
                    self.hold(self.env.cleaning_time_reaction_product_change)

                # Reset batches_processed
                self.cleaning.set(False)
                self.resource.set_capacity(self.capacity)
            else:
                self.passivate()


class Batch(BasicEntity):
    """Represents a Batch moving through various processing stages in the simulation."""

    def setup(self, type):

        super().setup()
        self.type = type
        self.bom = BILL_OF_MATERIALS[type]
        self.raw_materials = self.bom["parts"]
        self.weight = self.bom["weight"]
        if self.type == "product_1":
            self.update_fillcolor("green")
        elif self.type == "product_2":
            self.update_fillcolor("blue")

    def process(self):
        """Process method defining the path and actions of a Batch through the system."""
        t_entered = self.env.now()
        self.invisible()
        parts = self.collect_parts()
        self.hold(self.bom["duration"])
        self.parts = Part(type=self.type, parts=parts)

        if self.type == "product_1":
            self.collect_batches(
                self.env.batch_queue_reaction[self.type],
                self.env.n_batches_product1,
            )
        elif self.type == "product_2":
            self.collect_batches(
                self.env.batch_queue_reaction[self.type],
                self.env.n_batches_product2,
            )
        self.visible()
        self.move_and_hold(
            self.env.server_reaction.station.x,
            self.env.server_reaction.station.y,
            duration=self.env.arrival_duration,
            mode="moving",
        )
        self.invisible()
        # start the subprocess reaction
        self.subprocess_reaction()
        if self.type == "product_1":
            self.diminish_batchgroup(total_batches_in_group=self.env.n_batches_product1)
        self.visible()
        self.move_and_hold(
            self.env.batch_queue_distillation.x,
            self.env.batch_queue_distillation.y,
            duration=self.env.arrival_duration,
            mode="moving",
        )
        self.invisible()

        if self.type == "product_1":
            self.collect_batches(
                self.env.batch_queue_distillation, self.env.n_batches_distillation
            )
            self.subprocess_distillation()
        elif self.type == "product_2":
            self.collect_batches(
                self.env.batch_queue_crystallization, self.env.n_batches_crystallization
            )
            self.subprocess_crystallization()

        self.subprocess_evaluation()
        self.subprocess_packaging()
        t_left = self.env.now()
        delta_t = t_left - t_entered
        self.env.time_in_system.append(delta_t)
        self.env.batches_completed[self.type] += 1
        self.env.log.append(
            {
                "type": self.type,
                "t_entered_system": t_entered,
                "t_left_system": t_left,
            }
        )

    def subprocess_reaction(self):
        self.env.server_reaction.current_claimer = self.type
        self.request(self.env.server_reaction.resource, mode="requesting")
        self.visible()
        if self.type == "product_1":
            server_reaction_pt = self.env.server_reaction_product1_pt()
        elif self.type == "product_2":
            server_reaction_pt = self.env.server_reaction_product2_pt()
        self.hold(server_reaction_pt, mode="processing")
        self.release(self.env.server_reaction.resource)
        # Increment the batches_processed counter
        self.env.server_reaction.batches_processed += 1
        self.env.server_reaction.last_claimer = self.type
        # Activate the ReactionServer if the cleaning condition is met
        if self.env.server_reaction.batches_processed >= self.env.n_batches_product1:
            self.env.server_reaction.activate()

    def subprocess_distillation(self):
        """Subprocess for the first type of analysis."""
        self.move_and_hold(
            self.env.server_distillation.x,
            self.env.server_distillation.y,
            duration=self.env.arrival_duration,
            mode="moving",
        )
        self.invisible()
        self.request(self.env.server_distillation)
        self.visible()
        server_distillation_pt = self.env.server_distillation_pt()
        self.hold(server_distillation_pt, mode="processing")
        self.release(self.env.server_distillation)

    def subprocess_crystallization(self):
        """Subprocess for Cristallizaton."""
        self.move_and_hold(
            self.env.server_crystallization.x,
            self.env.server_crystallization.y,
            duration=self.env.arrival_duration,
            mode="moving",
        )
        self.invisible()
        self.request(self.env.server_crystallization, mode="requesting")
        self.visible()
        server_crystallization_pt = self.env.server_crystallization_pt()

        self.hold(server_crystallization_pt, mode="processing")
        self.release(self.env.server_crystallization)

    def subprocess_evaluation(self):
        """Subprocess for the evaluation."""
        self.move_and_hold(
            self.env.server_evaluation.x,
            self.env.server_evaluation.y,
            duration=self.env.arrival_duration,
            mode="moving",
        )
        self.invisible()
        self.request(self.env.server_evaluation)
        self.visible()
        if self.type == "product_1":
            evaluation_pt = self.env.server_evaluation_product1_pt()
        elif self.type == "product_2":
            evaluation_pt = self.env.server_evaluation_product2_pt()
        else:
            raise Exception("Unknown product type.")
        self.hold(evaluation_pt, mode="processing")
        self.release(self.env.server_evaluation)

    def subprocess_packaging(self):
        """Subprocess for the evaluation."""
        self.move_and_hold(
            self.env.server_packaging.x,
            self.env.server_packaging.y,
            duration=self.env.arrival_duration,
            mode="moving",
        )
        self.invisible()
        self.request(self.env.server_packaging)
        self.visible()
        if self.type == "product_1":
            packaging_pt = self.env.server_packaging_product1_pt()
        elif self.type == "product_2":
            packaging_pt = self.env.server_packaging_product2_pt()
        else:
            raise Exception("Unknown product type.")
        self.hold(packaging_pt, mode="processing")
        self.release(self.env.server_packaging)

    def collect_batches(self, q_server, n_batches):
        # Collect n batches before server processing
        q_server.add(self)
        if len(q_server) < n_batches:
            self.passivate()
        else:
            # When n batches are collected, activate all of them
            for batch in list(q_server):
                if batch.ispassive():
                    batch.activate()
            # **Clear the batch queue after activating the batches**
            q_server.clear()

    def reorder_parts(self):
        """Reorder the parts needed if projected stock is below reorder point."""
        for type, quantity in self.bom["parts"].items():
            current_stock = len(self.env.stock[type])
            ordered_stock = len([o for o in self.env.orders if o.type == type])
            projected_stock = current_stock + ordered_stock - quantity
            if projected_stock <= BILL_OF_MATERIALS[type]["reorder_point"]:
                for _ in range(BILL_OF_MATERIALS[type]["reorder_quantity"]):
                    Batch(type=type).enter(self.env.orders)

    def collect_parts(self):
        """Wait until all parts are available and get them from stock."""
        types_needed = [
            type
            for type, quantity in self.bom["parts"].items()
            for _ in range(quantity)
        ]
        n = len(types_needed)
        parts_collected = []
        while len(types_needed) > 0:
            part = self.from_store([self.env.stock[type] for type in set(types_needed)])
            parts_collected.append(part)
            types_needed.remove(part.type)
        if len(parts_collected) != n:
            raise Exception("Not all parts collected.")
        return sorted(parts_collected, key=lambda p: p.type)

    def diminish_batchgroup(self, total_batches_in_group=5):
        """
        Process a batch and destroy a certain number of batches in a group.
        """
        # number to destroy is always 5/2 of the total batches in the group but rounded
        num_batches_to_destroy = math.floor(total_batches_in_group / 5 * 2)
        self.env.count_batches_after_reaction += 1
        batch_number_in_group = (
            self.env.count_batches_after_reaction % total_batches_in_group
        )
        if batch_number_in_group == 0:
            batch_number_in_group = total_batches_in_group

        batches_to_destroy = list(range(1, num_batches_to_destroy + 1))

        if batch_number_in_group in batches_to_destroy:
            self.move_and_hold(
                100,
                0,
                duration=2,
                mode="moving",
            )
            self.invisible()
        if batch_number_in_group == total_batches_in_group:
            self.env.count_batches_after_reaction = 0


def set_speed(speed: float, env: sim.Environment = None) -> None:
    env.speed(float(speed))


def simulate(
    scenario=1,
    scenario_name="",
    replication_nr=0,
    random_seed="*",  # Use seed for reproducibility
    animate=ANIMATION,
    run_duration=RUN_DURATION,
    rate_multiplier=1,
    n_batches_product1=5,
    n_batches_product2=3,
    n_batches_distillation=3,
    n_batches_crystallization=3,
    server_reaction_capacity=1,
    server_distillation_capacity=1,
    server_crystallization_capacity=1,
    server_evaluation_capacity=1,
    server_packaging_capacity=1,
    server_reaction_product1_pt_low=6,
    server_reaction_product1_pt_high=6,
    server_reaction_product1_pt_mode=6,
    server_reaction_product2_pt_low=72,
    server_reaction_product2_pt_high=72,
    server_reaction_product2_pt_mode=72,
    # Zeiten t
    cleaning_time_reaction_product1=2,
    cleaning_time_reaction_product2=10,
    cleaning_time_reaction_product_change=0,
    server_distillation_pt_low=3,
    server_distillation_pt_high=6,
    server_distillation_pt_mode=4,
    server_crystallization_pt_low=2,
    server_crystallization_pt_high=2,
    server_crystallization_pt_mode=2,
    server_evaluation_product1_pt_low=0.2,
    server_evaluation_product1_pt_high=0.75,
    server_evaluation_product1_pt_mode=0.4,
    server_evaluation_product2_pt_low=0.2,
    server_evaluation_product2_pt_high=0.75,
    server_evaluation_product2_pt_mode=0.4,
    server_packaging_product1_pt_low=0.8,
    server_packaging_product1_pt_high=1.2,
    server_packaging_product1_pt_mode=1,
    server_packaging_product2_pt_low=0.8,
    server_packaging_product2_pt_high=1.2,
    server_packaging_product2_pt_mode=1,
):
    """
    Main simulation function that sets up and runs a simulation scenario.
    """
    params = locals().copy()  # Capture the function arguments as parameters
    print(locals())
    env = sim.Environment(random_seed=random_seed)
    # Animation-Setup
    env.animate(animate)
    env.speed(2)
    sim.AnimateSlider(
        x=100,
        y=100,
        vmin=0,
        vmax=64,
        resolution=1,
        v=ANIMATION_SPEED,
        label="Speed",
        action=lambda speed: set_speed(speed, env=env),
        env=env,
    )

    env.n_batches_product1 = n_batches_product1
    env.n_batches_product2 = n_batches_product2
    env.n_batches_distillation = n_batches_distillation
    env.n_batches_crystallization = n_batches_crystallization
    env.count_batches_after_reaction = 0
    env.time_entered = 0
    # setup initial stock
    env.stock = {
        type: sim.Store(
            name=type,
            fill=[Part(type=type) for _ in range(bom["initial_stock"])],
        )
        for type, bom in BILL_OF_MATERIALS.items()
    }

    # Batch queue before reaction
    env.batch_queue_reaction = {
        "product_1": QueueStation(
            name="BatchQueue_Reaction_Product1",
            x=0,
            y=450,
            display_name="Q_P1_RawMaterial",
            queue_direction="n",
        ),
        "product_2": QueueStation(
            name="BatchQueue_Reaction_Product2",
            x=0,
            y=200,
            display_name="Q_P2_RawMaterial",
            queue_direction="s",
            queue_offset=-40,
        ),
    }

    env.server_reaction = ReactionServer(
        name="ReactionServer",
        capacity=server_reaction_capacity,
        cleaning_time_product1=cleaning_time_reaction_product1 * HOUR,
        cleaning_time_product2=cleaning_time_reaction_product2 * HOUR,
        cleaning_time_product_change=cleaning_time_reaction_product_change * HOUR,
        x=140,
        y=350,
        display_name="Reaction",
    )
    env.batch_queue_distillation = QueueStation(
        name="BatchQueue_Distillation",
        x=250,
        y=500,
        display_name="Store_Distillation",
    )
    env.server_distillation = ResourceStation(
        name="Distillation",
        capacity=server_distillation_capacity,
        x=400,
        y=500,
        width=120,
        display_name="Distillation",
    )
    env.batch_queue_crystallization = QueueStation(
        name="BatchQueue_crystallization",
        x=250,
        y=150,
        display_name="Store__crystallization",
        queue_direction="s",
        queue_offset=-40,
    )
    env.server_crystallization = ResourceStation(
        name="Crystallization",
        capacity=server_crystallization_capacity,
        x=400,
        y=150,
        width=120,
        display_name="Crystallization",
    )

    env.server_evaluation = ResourceStation(
        name="Evaluation",
        capacity=server_evaluation_capacity,
        x=600,
        y=350,
        display_name="Evaluation",
    )

    env.server_packaging = ResourceStation(
        name="Packaging",
        capacity=server_packaging_capacity,
        x=800,
        y=350,
        display_name="Packaging",
    )

    # Define processing times for each station using a Triangular distribution
    env.server_reaction_product1_pt = sim.Triangular(
        low=server_reaction_product1_pt_low * HOUR,
        high=server_reaction_product1_pt_high * HOUR,
        mode=server_reaction_product1_pt_mode * HOUR,
    )
    env.server_reaction_product2_pt = sim.Triangular(
        low=server_reaction_product2_pt_low * HOUR,
        high=server_reaction_product2_pt_high * HOUR,
        mode=server_reaction_product2_pt_mode * HOUR,
    )
    env.cleaning_time_product1 = sim.Triangular(
        low=5 * HOUR, mode=7 * HOUR, high=10 * HOUR
    )
    env.cleaning_time_reaction_product1 = cleaning_time_reaction_product1
    env.cleaning_time_reaction_product2 = cleaning_time_reaction_product2
    env.cleaning_time_reaction_product_change = cleaning_time_reaction_product_change

    # Dreicksverteilungen t
    env.server_delivery_pt = sim.Triangular(low=3 * HOUR, high=5 * HOUR, mode=4 * HOUR)
    env.server_distillation_pt = sim.Triangular(
        low=server_distillation_pt_low * HOUR,
        high=server_distillation_pt_high * HOUR,
        mode=server_distillation_pt_mode * HOUR,
        # low=3 * HOUR, high=6 * HOUR, mode=4 * HOUR
    )
    env.server_crystallization_pt = sim.Triangular(
        low=server_crystallization_pt_low * HOUR,
        high=server_crystallization_pt_high * HOUR,
        mode=server_crystallization_pt_mode * HOUR,
        # low=2 * HOUR, high=2 * HOUR, mode=2 * HOUR
    )
    env.server_evaluation_product1_pt = sim.Triangular(
        low=server_evaluation_product1_pt_low * HOUR,
        high=server_evaluation_product1_pt_high * HOUR,
        mode=server_evaluation_product1_pt_mode * HOUR,
        # low=0.2 * HOUR, high=0.75 * HOUR, mode=0.4 * HOUR
    )
    env.server_evaluation_product2_pt = sim.Triangular(
        low=server_evaluation_product2_pt_low * HOUR,
        high=server_evaluation_product2_pt_high * HOUR,
        mode=server_evaluation_product2_pt_mode * HOUR,
        # low=0.2 * HOUR, high=0.75 * HOUR, mode=0.4 * HOUR
    )
    env.server_packaging_product1_pt = sim.Triangular(
        low=server_packaging_product1_pt_low * HOUR,
        high=server_packaging_product1_pt_high * HOUR,
        mode=server_packaging_product1_pt_mode * HOUR,
        # low=0.8 * HOUR, high=1.2 * HOUR, mode=1 * HOUR
    )
    env.server_packaging_product2_pt = sim.Triangular(
        low=server_packaging_product2_pt_low * HOUR,
        high=server_packaging_product2_pt_high * HOUR,
        mode=server_packaging_product2_pt_mode * HOUR,
        # low=0.8 * HOUR, high=1.2 * HOUR, mode=1 * HOUR
    )
    env.arrival_duration = 1  # Duration for moving between stations
    env.n_batches_created = {
        "product_1": 0,
        "product_2": 0,
    }  # Counter for the number of batches created}
    env.batches_completed = {
        "product_1": 0,
        "product_2": 0,
    }  # Counter for the number of batches completed
    env.log = []
    env.time_in_system = []

    ConstantRateSource(env=env, product_type="product_1", arrival_rate= rate_multiplier / DAY)
    ConstantRateSource(env=env, product_type="product_2", arrival_rate= rate_multiplier / DAY)

    # Initialize the queue monitor
    monitor_queue_reaction = QueueMonitor(
        env=env, queue=env.server_reaction.resource.requesters()
    )
    # Start the ReactionServer process
    env.server_reaction.activate()  # t

    # Run the simulation
    try:
        env.run(run_duration)
    except sim.SimulationStopped:
        msg = "simulation stopped"
    except Exception as e:
        msg = f"another exception: {e}"
    else:
        msg = "simulation ended"

    # Collect and return simulation results
    return {
        **params,
        "msg": msg,
        "t_end": env.now(),
        # Collect statistics
        "server_reaction_waiting_time_mean": env.server_reaction.resource.requesters().length_of_stay.mean(),
        "server_reaction_waiting_time_max": env.server_reaction.resource.requesters().length_of_stay.maximum(),
        "server_reaction_queue_length_mean": env.server_reaction.resource.requesters().length.mean(),
        "server_reaction_queue_length_max": env.server_reaction.resource.requesters().length.maximum(),
        "server_reaction_occupancy": env.server_reaction.resource.occupancy.mean(),
        "distillation_waiting_time_mean": env.server_distillation.requesters().length_of_stay.mean(),
        "distillation_queue_length_mean": env.server_distillation.requesters().length.mean(),
        "distillation_batches_processed": env.server_distillation.claimers().number_of_departures,
        "server_crystallization_waiting_time_mean": env.server_crystallization.requesters().length_of_stay.mean(),
        "server_crystallization_queue_length_mean": env.server_crystallization.requesters().length.mean(),
        "server_crystallization_batches_processed": env.server_crystallization.claimers().number_of_departures,
        "server_evaluation_waiting_time_mean": env.server_evaluation.requesters().length_of_stay.mean(),
        "server_evaluation_queue_length_mean": env.server_evaluation.requesters().length.mean(),
        "server_packaging_waiting_time_mean": env.server_packaging.requesters().length_of_stay.mean(),
        "server_packaging_queue_length_mean": env.server_packaging.requesters().length.mean(),
        "queue_reaction_length": monitor_queue_reaction.data,
        "n_batches_created_product_1": env.n_batches_created["product_1"],
        "finished_batchesproduct_1": env.batches_completed["product_1"],
        "unfinished_batchesproduct_1": env.n_batches_created["product_1"]
        - env.batches_completed["product_1"],
        "n_batches_created_product_2": env.n_batches_created["product_2"],
        "finished_batchesproduct_2": env.batches_completed["product_2"],
        "unfinished_batchesproduct_2": env.n_batches_created["product_2"]
        - env.batches_completed["product_2"],
        "time_in_system_max": max(env.time_in_system) if env.time_in_system else 0,
        "time_in_system_mean": (
            stat.mean(env.time_in_system) if env.time_in_system else 0
        ),
        "df_log_batches_entered": (env.log),
    }


if __name__ == "__main__":
    pass
