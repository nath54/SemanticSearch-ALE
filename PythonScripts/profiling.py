"""
Utility to easily profile programs to see the time took by each tasks in your program, and easily visualize them within the little webapp that comes together with this python program.

Author: Nathan Cerisara
"""

from typing import Optional, Any, Self

import os
import json
import atexit
import time
import datetime
from threading import get_native_id as get_current_thread_id
from threading import Lock

from lib import escapeCharacters

#
os.system("") # enables ansi escape characters in terminal

#

PATH_LAST_RESULT_JS: str = "../profiling_results/web_visualisation/js/results_data.js"
DIR_PATH_RESULTS: str = "../profiling_results/results/"
PROFILING_GLOBALS_VARIABLE_NAME: str = "global_session_profiling"

#
class Task:
    """
    Represents a task
    """

    def __init__(self, app_time_started: float, task_name: str, thread_id: int = get_current_thread_id()) -> None:

        # We store here the time when the app has started
        self.app_time_started: float = app_time_started

        # Name of the task
        self.task_name: str = task_name

        # Id of the thread where the task has been executed first
        # TODO -> move to first app initialisation to each execution start
        self.thread_id: int = thread_id

        # Times of each times this task starts
        self.task_executions_starts: list[float] = []

        # Current task parent of each executions of this task
        self.task_executions_parent_tasks: list[tuple[str, int]] = []

        # Update times of each executions of this task
        self.task_executions_updates: list[list[tuple[float, str]]] = []

        # Times of each times this task ends
        self.task_executions_ends: list[tuple[float, str]] = []

        # Contains all the subtasks of this task
        self.task_executions_subtasks: list[list[Task]] = []

        # -1 = this task is not in execution, else the id of the execution to access each feature in the lists above
        self.execution_id: int = -1

    #
    def starts(self, parent_task: Optional[Self] = None, parent_task_exec_id: int = 0) -> None:
        """
        Starts this task

        Args:
            parent_task (Optional[Task]) : Parent of this execution of this task. Defaults to None
            parent_task_exec_id (int) : Id of the current execution of the parent task of this task. Defaults to 0

        Raises:
            SystemError: Tried to starts a task that has already started and not ended!
            SystemError: Task_executions_updates length is different from task_executions_starts!
            SystemError: Task_executions_children_tasks length is different from task_executions_starts!
            SystemError: Task_executions_ends length is different from task_executions_starts!
            SystemError: Task_executions_ends length is different from task_executions_starts!
        """

        if self.execution_id != -1:
            raise SystemError(f"Tried to starts a task that has already started and not ended! (task_name={self.task_name})")
        #
        self.execution_id = len(self.task_executions_starts)
        #
        if len(self.task_executions_updates) != self.execution_id:
            raise SystemError(f"Error: Task_executions_updates length is different from task_executions_starts! (task_name={self.task_name}, starts_length=({len(self.task_executions_starts)}, updates_length={len(self.task_executions_updates)}))")
        #
        if len(self.task_executions_subtasks) != self.execution_id:
            raise SystemError(f"Error: Task_executions_children_tasks length is different from task_executions_starts! (task_name={self.task_name}, starts_length=({len(self.task_executions_starts)}, children_length={len(self.task_executions_subtasks)}))")
        #
        if len(self.task_executions_ends) != self.execution_id:
            raise SystemError(f"Error: Task_executions_ends length is different from task_executions_starts! (task_name={self.task_name}, starts_length=({len(self.task_executions_starts)}, ends_length={len(self.task_executions_ends)}))")
        #
        if len(self.task_executions_parent_tasks) != self.execution_id:
            raise SystemError(f"Error: Task_executions_ends length is different from task_executions_starts! (task_name={self.task_name}, starts_length=({len(self.task_executions_starts)}, ends_length={len(self.task_executions_ends)}))")
        #
        self.task_executions_starts.append(time.time() - self.app_time_started)
        self.task_executions_updates.append([])
        self.task_executions_subtasks.append([])
        self.task_executions_parent_tasks.append(("" if parent_task is None else parent_task.task_name, parent_task_exec_id))
        self.task_executions_ends.append((0, ""))

    #
    def add_subtask(self, sub_task: Self) -> None:
        """
        Add a subtask to the current execution of this task.

        Args:
            sub_task (Task): subtask to add to the current execution of this task

        Raises:
            SystemError: Tried to add a subtask to a task that isn't running!
        """

        #
        if self.execution_id == -1:
            raise SystemError(f"Tried to add a subtask to a task that isn't running! (task_name={self.task_name}, subtask_name={sub_task.task_name})")
        #
        self.task_executions_subtasks[self.execution_id].append(sub_task)

    #
    def update(self, message: str = "") -> None:
        """
        Add an update tick to the current execution of this task.
        Usage example: in a for loop, this task is arround the for loop, and inside the for loop, we tick the task each time the loop ends or starts.

        Args:
            message (str, optional): Message that accompanying this update. Defaults to "".

        Raises:
            SystemError: Tried to update a task that isn't running!
        """

        if self.execution_id == -1:
            raise SystemError(f"Tried to update a task that isn't running! (task_name={self.task_name})")
        #
        self.task_executions_updates[self.execution_id].append((time.time() - self.app_time_started, message))

    #
    def ends(self, message: str = "") -> None:
        """
        Ends the current execution of this task.

        Args:
            message (str, optional): Message that accompanying the end of this task's execution. Defaults to "".

        Raises:
            SystemError: Tried to ends a task that isn't running!
        """

        if self.execution_id == -1:
            raise SystemError(f"Tried to ends a task that isn't running! (task_name={self.task_name})")
        #
        self.task_executions_ends[self.execution_id] = (time.time() - self.app_time_started, message)
        self.execution_id = -1

    #
    def export_to_json(self) -> dict:
        """
        Export this task and its profiling data into a dictionnary that is json compatible.

        Returns:
            dict: A dictionnary JSON compatible that represents this task's profiling data
        """

        return {
            "task_name": self.task_name,
            "thread_id": self.thread_id,
            "task_executions_starts": self.task_executions_starts,
            "task_executions_parent_tasks": self.task_executions_parent_tasks,
            "task_executions_updates": self.task_executions_updates,
            "task_executions_ends": self.task_executions_ends,
            "task_executions_subtasks": [[st.task_name for st in le] for le in self.task_executions_subtasks]
        }

#
class GlobalProfiler:
    """
    Main System that will manage profiling for the session.
    """

    def __init__(self, session_name: str = "", verbose: bool = False) -> None:
        """
        GlobalProfiler Initialisation

        Args:
            verbose (bool, optional): print a message to the console when each starting, updating or ending a task. Defaults to False.
        """

        #
        self.verbose: bool = verbose
        #
        self.tasks: dict[str, Task] = {}
        #
        self.threads_tasks_queues: dict[int, list[Task]] = {}
        #
        self.session_name: str = session_name
        #
        self.session_profiling_saved: bool = False
        #
        self.time_app_start: float = time.time()
        #
        self.date_app_started: str = datetime.datetime.now().strftime("%d/%m/%Y")
        #
        self.mutex: Lock = Lock()
        #
        atexit.register(self.exit_handler)

    #
    def verbose_print(self, txt: str) -> None:
        """
        Prints a message only if the verbose option is activated.

        Args:
            txt (str): Message to print.
        """

        if self.verbose:
            print(f"\033[35m\nProfiling Verbose:\n{txt}\n\033[m")

    #
    def exit_handler(self) -> None:
        """
        Function that catch an exit signal to save the profiling data before exiting the program.
        """

        #
        self.verbose_print("Program exit catched.")
        #
        self.save_session_profiling()

    #
    def save_session_profiling(self) -> None:
        """
        Save the profiling data to a json file and update the visualisation data on the webpage.
        """

        if self.session_profiling_saved:
            return
        #
        self.session_profiling_saved = True
        #
        save_dict: dict = {
            "session_name": self.session_name,
            "session_date": self.date_app_started,
            "time_app_started": 0,
            "time_app_finished": time.time() - self.time_app_start,
            "tasks": {}
        }
        #
        for task_name in self.tasks:
            save_dict["tasks"][task_name] = self.tasks[task_name].export_to_json()
        #
        if not os.path.exists(DIR_PATH_RESULTS):
            os.makedirs(DIR_PATH_RESULTS)
        #
        save_dict_txt: str = json.dumps(save_dict)
        #
        file_name: str = f"profiling_result_{datetime.datetime.now().strftime('%d-%m-%Y_%Hh%M')}.json"
        with open(f"{DIR_PATH_RESULTS}{file_name}", "w") as f:
            f.write(save_dict_txt)
        #
        self.verbose_print(f"Profiling results saved to : {DIR_PATH_RESULTS}{file_name}")
        #
        txt_js: str = f"const results_data = {save_dict_txt};"
        #
        with open(f"{PATH_LAST_RESULT_JS}", "w") as f:
            f.write(txt_js)

    #
    def task_add_to_current_thread_queue(self, task: Task) -> None:
        """
        Add a task to the current thread tasks queue

        Args:
            task (Task): Task to add
        """

        id_crt_thread: int = get_current_thread_id()
        #
        self.verbose_print(f"Add task to current thread queue : (thread={id_crt_thread}, task={task.task_name})")
        #
        if not id_crt_thread in self.threads_tasks_queues:
            #
            self.verbose_print(f"Add current thread to self.threads_tasks_queues : (thread={id_crt_thread})")
            #
            self.threads_tasks_queues[id_crt_thread] = []
        #
        self.threads_tasks_queues[id_crt_thread].append(task)

    #
    def remove_last_task_from_current_thread_queue(self) -> None:
        """
        Remove the last task from the current thread tasks queue

        Raises:
            SystemError: Unkown thread id
            SystemError: No task left to remove
        """

        #
        id_crt_thread: int = get_current_thread_id()
        #
        self.verbose_print(f"Remove last task from current thread queue : (thread={id_crt_thread})")
        #
        if not id_crt_thread in self.threads_tasks_queues:
            raise SystemError(f"task_remove_from_current_thread_queue error : unknown id thread {id_crt_thread}")
        #
        if len(self.threads_tasks_queues[id_crt_thread]) == 0:
            raise SystemError(f"task_remove_from_current_thread_queue error : no tasks left to remove!")
        #
        self.threads_tasks_queues[id_crt_thread].pop(-1)

    #
    def get_last_task_current_thread_queue(self) -> Optional[Task]:
        """
        Get the last task if exists from the current thread tasks queue

        Returns:
            Optional[Task]: The last task if exists, else None
        """

        #
        id_crt_thread: int = get_current_thread_id()
        #
        self.verbose_print(f"Get last task from current thread queue : (thread={id_crt_thread})")
        #
        if not id_crt_thread in self.threads_tasks_queues:
            return None
        #
        if len(self.threads_tasks_queues[id_crt_thread]) == 0:
            return None
        #
        self.verbose_print(f"Get last task from current thread queue done : (thread={id_crt_thread}, task={self.threads_tasks_queues[id_crt_thread][-1].task_name})")
        #
        return self.threads_tasks_queues[id_crt_thread][-1]

    #
    def task_start(self, task_name: str) -> None:
        """
        Starts the profiling of a task

        Args:
            task_name (str): the name of the task to profile
        """

        #
        task_name = escapeCharacters(task_name)

        #
        id_crt_thread: int = get_current_thread_id()
        #
        self.verbose_print(f"Task start : (thread={id_crt_thread}, task={task_name})")
        #
        self.mutex.acquire()

        try:
            #
            # On crée la tâche si elle n'existe déjà pas
            if not task_name in self.tasks:
                #
                self.tasks[task_name] = Task(
                                            app_time_started=self.time_app_start,
                                            task_name=task_name,
                                            thread_id=id_crt_thread
                                        )

            #
            parent_task_obj: Optional[Task] = self.get_last_task_current_thread_queue()
            #
            parent_task_exec_id: int = 0 if parent_task_obj is None else parent_task_obj.execution_id

            # On la rajoute à la queue des dernières tâches en cours
            self.task_add_to_current_thread_queue(self.tasks[task_name])

            # Et on la lance
            self.tasks[task_name].starts(
                                            parent_task=parent_task_obj,
                                            parent_task_exec_id=parent_task_exec_id
                                        )

            # On la rajoute aussi au parent
            if parent_task_obj is not None:
                #
                self.verbose_print(f"Task start - Parent found & added : (thread={id_crt_thread}, task={self.tasks[task_name].task_name}, parent={parent_task_obj.task_name})")
                #
                parent_task_obj.add_subtask(self.tasks[task_name])

        finally:
            #
            self.mutex.release()

    #
    def task_update(self, task_name: str, message: str = "") -> None:
        """
        Add a tick to the profiled task.

        Args:
            task_name (str): the name of the task to tick
            message (str, optional): The message attached to this update. Defaults to "".

        Raises:
            SystemError: The task doesn't exists.
        """

        #
        task_name = escapeCharacters(task_name)

        #
        id_crt_thread: int = get_current_thread_id()
        #
        self.verbose_print(f"Task update : (thread={id_crt_thread}, task={task_name})")
        #
        self.mutex.acquire()
        try:
            #
            if not task_name in self.tasks:
                raise SystemError(f"Error: Tried to update a non existing task! (task_name={task_name})")
            #
            self.tasks[task_name].update(message)
        finally:
            #
            self.mutex.release()

    #
    def last_task_ends(self, message: str = "") -> None:
        """
        Ends the last task that is running on the current thread.

        Args:
            message (str, optional): Message attached to the end of this task. Defaults to "".

        Raises:
            SystemError: No tasks left to end.
        """

        #
        id_crt_thread: int = get_current_thread_id()
        #
        self.verbose_print(f"Last task end : (thread={id_crt_thread})")
        #
        self.mutex.acquire()
        try:
            #
            last_current_task: Optional[Task] = self.get_last_task_current_thread_queue()
            #
            if last_current_task is None:
                raise SystemError(f"Error: Tried to end a task while there are not tasks to end!")
            #
            self.verbose_print(f"Last task to end found : (thread={id_crt_thread}, task={last_current_task.task_name})")
            #
            last_current_task.ends(message)

            # On l'enlève de la queue des dernières tâches en cours
            self.remove_last_task_from_current_thread_queue()
        finally:
            #
            self.mutex.release()

#
def profiling_init(session_name: str = "") -> None:
    """
    Initialise the global profiling session, and adds it to the global variables.
    You must use this function only once time at the end of the main script of your program.

    Raises:
        SystemError: There is already a thing at the place of the GlobalProfiler object that is not a GlobalProfiler object!
        SystemError: The GlobalProfiler object has already been initialised.
    """

    #
    if PROFILING_GLOBALS_VARIABLE_NAME in globals():
        if not isinstance(globals()[PROFILING_GLOBALS_VARIABLE_NAME], GlobalProfiler):
            raise SystemError("There is already a thing at the place of the GlobalProfiler object that is not a GlobalProfiler object!")
        #
        raise SystemError("The GlobalProfiler object has already been initialised.")

    #
    globals()[PROFILING_GLOBALS_VARIABLE_NAME] = GlobalProfiler(session_name=session_name)

#
def get_global_profiling() -> GlobalProfiler:
    """
    Get the global profiler object

    Raises:
        SystemError: Trying to access to the Global object while it has not been initialised.
        SystemError: There is already a thing at the place of the GlobalProfiler object that is not a GlobalProfiler object!

    Returns:
        GlobalProfiler: The global profiler object.
    """

    #
    if not PROFILING_GLOBALS_VARIABLE_NAME in globals():
        raise SystemError("Error : Trying to access to the Global object while it has not been initialised.")
    #
    if not isinstance(globals()[PROFILING_GLOBALS_VARIABLE_NAME], GlobalProfiler):
        raise SystemError("There is already a thing at the place of the GlobalProfiler object that is not a GlobalProfiler object!")
    #
    return globals()[PROFILING_GLOBALS_VARIABLE_NAME]

#
def profiling_task_start(task_name: str) -> None:
    """
    Starts the profiling of a task

    Args:
        task_name (str): Name of the task to profile
    """

    get_global_profiling().task_start(task_name)

#
def profiling_task_update(task_name: str, message: str = "") -> None:
    """
    Add a tick update to the running task

    Args:
        task_name (str): the name of the task to tick
        message (str, optional): Message attached to the update. Defaults to "".
    """

    get_global_profiling().task_update(task_name, message)

#
def profiling_last_task_ends(message: str = "") -> None:
    """
    Ends the last task running on the current thread

    Args:
        message (str, optional): Message attached to the end of the task. Defaults to "".
    """

    get_global_profiling().last_task_ends(message)

#
def profiling_save_and_stop() -> None:
    """
    Save the profiling results and delete the global profiler object.
    """

    get_global_profiling().save_session_profiling()
    del globals()[PROFILING_GLOBALS_VARIABLE_NAME]
