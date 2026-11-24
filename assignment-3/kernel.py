### Fill in the following information before submitting
# Group id: 16
# Members: Bruhati Aarushi Kuchi, Rutu Aarabhi Kuchi, Tanvi Badadare

from collections import deque

# PID is just an integer, but it is used to make it clear when a integer is expected to be a valid PID.
PID = int

# This class represents the PCB of processes.
# It is only here for your convinience and can be modified however you see fit.
class PCB:
    pid: PID

    def __init__(self, pid: PID, priority: int = 0, process_type: str = "Background"):
        self.pid = pid
        self.priority = priority
        self.process_type = process_type
        self.rr_ticks = 0
        

# This class represents the Kernel of the simulation.
# The simulator will create an instance of this object and use it to respond to syscalls and interrupts.
# DO NOT modify the name of this class or remove it.
class Kernel:
    scheduling_algorithm: str
    ready_queue: deque[PCB]
    waiting_queue: deque[PCB]
    running: PCB
    idle_pcb: PCB

    # Called before the simulation begins.
    # Use this method to initilize any variables you need throughout the simulation.
    # logger is provided which allows you to include your own print statements in the
    #   output logs. These will not impact grading.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def __init__(self, scheduling_algorithm: str, logger):
        self.scheduling_algorithm = scheduling_algorithm
        self.ready_queue = deque()
        self.waiting_queue = deque()
        self.idle_pcb = PCB(0)
        self.running = self.idle_pcb
        self.timer_ticks = 0

        self.foreground_queue = deque()
        self.background_queue = deque()
        self.multilevel_ticks = 0
        self.current_level = "Foreground"

        self.semaphores = {}         # semaphore_id current value
        self.semaphore_waiting = {}  # semaphore_id list of blocked PCBs
        self.mutex_locked = {}       # mutex_id True/False
        self.mutex_waiting = {}      # mutex_id list of blocked PCBs

    # This method is triggered every time a new process has arrived.
    # new_process is this process's PID.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def new_process_arrived(self, new_process: PID, priority: int, process_type: str) -> PID:
        new_pcb = PCB(new_process, priority, process_type)

        if self.scheduling_algorithm == "Priority":
            self.ready_queue.append(new_pcb)
            return self.choose_next_process()

        elif self.scheduling_algorithm == "Multilevel":
            if process_type == "Foreground":
                self.foreground_queue.append(new_pcb)
            else:
                self.background_queue.append(new_pcb)

            if self.running is self.idle_pcb:
                if self.current_level == "Foreground":
                    current_queue = self.foreground_queue
                    other_queue = self.background_queue
                    other_level = "Background"
                else:
                    current_queue = self.background_queue
                    other_queue = self.foreground_queue
                    other_level = "Foreground"

                if len(current_queue) > 0:
                    self.multilevel_ticks = 0
                    self.running = current_queue.popleft()
                    self.timer_ticks = self.running.rr_ticks
                elif len(other_queue) > 0:
                    self.current_level = other_level
                    self.multilevel_ticks = 0
                    self.running = other_queue.popleft()
                    self.timer_ticks = self.running.rr_ticks

            return self.running.pid

        else:
            if self.running is self.idle_pcb:
                self.running = new_pcb
                self.timer_ticks = 0
                return self.running.pid

            self.ready_queue.append(new_pcb)
            return self.running.pid

    # This method is triggered every time the current process performs an exit syscall.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_exit(self) -> PID:
        self.running = self.idle_pcb
        self.timer_ticks = 0

        if self.scheduling_algorithm == "Multilevel":
            if self.current_level == "Foreground":
                current_queue = self.foreground_queue
                other_queue = self.background_queue
                other_level = "Background"
            else:
                current_queue = self.background_queue
                other_queue = self.foreground_queue
                other_level = "Foreground"

            if len(current_queue) > 0:
                self.running = current_queue.popleft()
                self.timer_ticks = self.running.rr_ticks
                return self.running.pid

            if len(other_queue) > 0:
                self.current_level = other_level
                self.multilevel_ticks = 0
                self.running = other_queue.popleft()
                self.timer_ticks = self.running.rr_ticks
                return self.running.pid

            return self.running.pid

        return self.choose_next_process()

    # This is where you can select the next process to run.
    # This method is not directly called by the simulator and is purely for your convinience.
    # Feel free to modify this method as you see fit.
    def choose_next_process(self):
        if self.scheduling_algorithm == "Priority":
            options = list(self.ready_queue)

            if self.running is not self.idle_pcb:
                options.append(self.running)

            if len(options) == 0:
                self.running = self.idle_pcb
                return self.running.pid

            winning_process = max(
                options,
                key=lambda p: (p.priority, -p.pid)
            )

            options.remove(winning_process)
            self.ready_queue = deque(options)
            self.running = winning_process
            return self.running.pid

        elif self.scheduling_algorithm == "FCFS" or self.scheduling_algorithm == "RR":
            if len(self.ready_queue) == 0:
                self.running = self.idle_pcb
            else:
                self.running = self.ready_queue.popleft()

            self.timer_ticks = 0
            return self.running.pid

        return self.running.pid

    # Block the running process and switch to the next one.
    def block_running(self, waiting_list):
        waiting_list.append(self.running)
        self.running = self.idle_pcb   
        return self.choose_next_process()

    # Pick which blocked process to release, based on the algorithm.
    def pick_waiter(self, waiting_list):
        if self.scheduling_algorithm == "Priority":
            chosen = max(waiting_list, key=lambda p: (p.priority, -p.pid))
        else:  # FCFS and RR: lowest PID
            chosen = min(waiting_list, key=lambda p: p.pid)
        waiting_list.remove(chosen)
        return chosen

    # Make a released process ready again.
    def release(self, pcb):
        self.ready_queue.append(pcb)
        if self.scheduling_algorithm == "Priority":
            return self.choose_next_process()   
        return self.running.pid                 
    

    # This method is triggered when the currently running process requests to change its priority.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_set_priority(self, new_priority: int) -> PID:
        self.running.priority = new_priority
        if self.scheduling_algorithm == "Priority":
            return self.choose_next_process()
        return self.running.pid

    # This function represents the hardware timer interrupt.
    # It is triggered every 10 milliseconds and is the only way a kernel can track passing time.
    # Do not use real time to track how much time has passed as time is simulated.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def timer_interrupt(self) -> PID:
        if self.scheduling_algorithm == "RR":
            if self.running is self.idle_pcb:
                return self.running.pid

            self.timer_ticks += 1
            if self.timer_ticks < 4:
                return self.running.pid

            self.timer_ticks = 0
            if len(self.ready_queue) == 0:
                return self.running.pid

            self.ready_queue.append(self.running)
            self.running = self.ready_queue.popleft()

        elif self.scheduling_algorithm == "Multilevel":
            if self.current_level == "Foreground" and self.running.process_type == "Foreground":
                self.timer_ticks += 1
                if self.timer_ticks == 4:
                    self.running.rr_ticks = 0
                    self.timer_ticks = 0
                    if len(self.foreground_queue) > 0:
                        self.foreground_queue.append(self.running)
                        self.running = self.foreground_queue.popleft()
                        self.timer_ticks = self.running.rr_ticks

            self.multilevel_ticks += 1
            if self.multilevel_ticks == 20:
                self.multilevel_ticks = 0
                if self.current_level == "Foreground":
                    other_queue = self.background_queue
                    other_level = "Background"
                else:
                    other_queue = self.foreground_queue
                    other_level = "Foreground"

                if len(other_queue) > 0:
                    if self.running is not self.idle_pcb:
                        self.running.rr_ticks = self.timer_ticks
                        if self.running.process_type == "Foreground":
                            self.foreground_queue.appendleft(self.running)
                        else:
                            self.background_queue.appendleft(self.running)
                    self.current_level = other_level
                    self.running = other_queue.popleft()
                    self.timer_ticks = self.running.rr_ticks

        return self.running.pid


    # This method is triggered when the currently running process requests to initialize a new semaphore.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_init_semaphore(self, semaphore_id: int, initial_value: int):
        self.semaphores[semaphore_id] = initial_value
        self.semaphore_waiting[semaphore_id] = []
        #return
    
    # This method is triggered when the currently running process calls p() on an existing semaphore.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_semaphore_p(self, semaphore_id: int) -> PID:
        if self.semaphores[semaphore_id] > 0:
            self.semaphores[semaphore_id] -= 1
            return self.running.pid
        return self.block_running(self.semaphore_waiting[semaphore_id])
        # return self.running.pid
    
    # This method is triggered when the currently running process calls v() on an existing semaphore.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_semaphore_v(self, semaphore_id: int) -> PID:
        waiting = self.semaphore_waiting[semaphore_id]
        if len(waiting) > 0:
            return self.release(self.pick_waiter(waiting))
        self.semaphores[semaphore_id] += 1
        return self.running.pid
    
    # This method is triggered when the currently running process requests to initialize a new mutex.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_init_mutex(self, mutex_id: int):
        self.mutex_locked[mutex_id] = False
        self.mutex_waiting[mutex_id] = []
        #return
    
    # This method is triggered when the currently running process calls lock() on an existing mutex.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_mutex_lock(self, mutex_id: int) -> PID:
        if not self.mutex_locked[mutex_id]:
            self.mutex_locked[mutex_id] = True
            return self.running.pid
        return self.block_running(self.mutex_waiting[mutex_id])
        #return self.running.pid
    
    # This method is triggered when the currently running process calls unlock() on an existing mutex.
    # DO NOT rename or delete this method. DO NOT change its arguments.
    def syscall_mutex_unlock(self, mutex_id: int) -> PID:
        waiting = self.mutex_waiting[mutex_id]
        if len(waiting) > 0:
            return self.release(self.pick_waiter(waiting))  # lock passes to it; stays locked
        self.mutex_locked[mutex_id] = False
        return self.running.pid
