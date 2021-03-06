from contextlib import contextmanager
from timeit import default_timer as time
from threading import Thread, Event
from time import sleep

# Tick context
@contextmanager
def tick_context(value, sleep=sleep):
    """Generate a context that controls the duration of its execution."""
    start = time()
    yield
    sleep_time = start + value - time()
    if sleep_time > 0:
        sleep(sleep_time)


class StateMachineManager(object):
    def __init__(self, loop_time, state_machine_cls, **state_machine_kwargs):
        """ Thread manager to run state machine
        args :
               loop time : time between loop execution
               state_machine_cls : class of the state machine
               state_machine_kwargs:  arguments of the state machine

        This manager call in a thread self.state_machine.proceed periodically.
        It offer a interface to start / stop / pause /resume state machine
        execution.
        """
        self.loop_time = loop_time
        self.state_machine = None
        self.state_machine_cls = state_machine_cls
        self.state_machine_kwargs = state_machine_kwargs
        self.running_thread = None
        self.evt_run = Event()
        self.evt_end_step = Event()
        self.evt_stop = Event()
        self.evt_done = Event()

    def start(self):
        """ Start the cycling loop """
        self.evt_run.set()
        self.evt_end_step.clear()
        self.evt_stop.clear()
        self.evt_done.clear()
        self.state_machine = self.state_machine_cls(**self.state_machine_kwargs)
        self.running_thread = Thread(target=self.loop)
        self.running_thread.start()

    def is_running(self):
        return self.state_machine and self.evt_run.isSet()

    def pause(self):
        """ break the cycling loop"""
        self.evt_run.clear()

    def next_step(self):
        """ execute one step loop"""
        self.evt_end_step.clear()
        self.evt_run.set()
        self.evt_end_step.wait()
        self.evt_run.clear()
        self.running = False

    def resume(self):
        """ re-run the cycling loop"""
        self.evt_run.set()

    def stop(self):
        """ stop the cycling loop"""
        self.evt_stop.set()
        # Wait the end of the thread
        if self.running_thread is not None:
            self.running_thread.join()
        self.state_machine = None

    def loop(self):
        """The main loop for one conditioning run."""
        while  not self.state_machine.finished  and  not self.evt_stop.isSet():
            with tick_context(self.loop_time, sleep=self.evt_stop.wait):
                self.evt_end_step.clear()
                self.state_machine.proceed()
                self.evt_end_step.set()
            while not self.evt_run.isSet():
                self.evt_run.wait(1.0)  # Paused; do nothing
        self.evt_done.set()
        self.state_machine = None
