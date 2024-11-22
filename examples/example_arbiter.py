# example_arbiter.py

from wdmsim.arbiter.base_arbiter import BaseArbiter
from wdmsim.arbiter.arbiter_factory import arbiter_factory
from wdmsim.arbiter.arbiter_instr import SearchInst, LockInst, UnlockInst

# register the arbiter class to the factory
# the register_str_id is the string id that will be used to refer to this arbiter in the CLI
@arbiter_factory(register_str_id="example_one_by_one")
class SimpleArbiter(BaseArbiter):
    # override algorithm function to implement the arbiter algorithm
    def algorithm(self):
        # set lock sequence before start running an algorithm
        if self.target_lane_order:
            slice_lock_sequence = [self.target_lane_order.index(lane) for lane in self.target_lane_order]
        else:
            slice_lock_sequence = list(range(self.num_slices))

        # loop through the lock sequence and issue LockInst to each slice
        # for each iteration, yield to update the lock-step
        for rx_idx in slice_lock_sequence:
            LockInst(self, rx_idx, "least_significant", 0).run()
            if self.check_lock_done(rx_idx) and not self.check_zero_lock(rx_idx):
                yield
            else:
                self.lock_error_state = True
                yield

        # if the sequence is done and not in error state, set end_state to True
        self.end_state = True
        yield


