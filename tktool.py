import abc
import traceback
import threading
from tkinter.font import Font
from typing import Optional, List


def make_font(**kwargs):
    return Font(family=r"./noto/NotoSansSC-Thin.otf", **kwargs)


class TkEventMain(metaclass=abc.ABCMeta):
    """
    Tkinter 处理子线程基类
    """
    tk_refresh_delay = 50

    def __init__(self):
        self._event_list: List[TkEventBase] = []
        self.set_after_run(self.tk_refresh_delay, lambda: self.run_event())

    def push_event(self, event: "TkEventBase"):  # 添加子线程
        self._event_list.append(event)
        self.show_loading(event.get_title())
        self.run_event()

    def run_event(self):  # 定时任务, 检测子线程是否结束, 并运行 done_after_event
        if len(self._event_list) == 0:
            return

        new_event: List[TkEventBase] = []
        done_event: List[TkEventBase] = []
        for event in self._event_list:
            if event.is_end():
                done_event.append(event)
            else:
                new_event.append(event)
        self._event_list = new_event
        if len(self._event_list) == 0:
            self.stop_loading()

        for event in done_event:  # 隐藏进度条后执行Event-GUI任务
            try:
                event.done_after_event()
            except:
                traceback.print_exc()
        self.set_after_run_now(self.tk_refresh_delay, self.run_event)

    @abc.abstractmethod
    def show_loading(self, title: str):  # 有子线程时显示加载
        ...

    @abc.abstractmethod
    def stop_loading(self):  # 子线程运行完成后关闭加载
        ...

    @abc.abstractmethod
    def set_after_run(self, ms, func, *args):
        ...

    @abc.abstractmethod
    def set_after_run_now(self, ms, func, *args):
        ...


class TkEventBase(metaclass=abc.ABCMeta):
    """
    Tkinter 子线程任务
    """

    def __init__(self):
        self.thread: Optional[TkThreading] = None  # 子线程

    def is_end(self) -> bool:  # 判断子线程是否结束
        if self.thread is not None and not self.thread.is_alive():
            return True
        return False

    @abc.abstractmethod
    def get_title(self) -> str:  # 获取任务名字
        ...

    def done_after_event(self):  # 子线程结束后, 在GUI线程执行的代码
        if self.thread is not None:
            self.thread.wait_event()


class TkThreading(threading.Thread):
    """
    tkinter 子线程
    """

    def __init__(self, func, *args, start_now: bool = True):
        """
        :param func: 子线程函数
        :param args: 子线程参数
        :param start_now: 是否马上运行 (否则要回调.start函数)
        """
        threading.Thread.__init__(self)
        self.func = func
        self.args = args
        self.result = None

        if start_now:
            self.start()

    def run(self):
        try:
            self.result = self.func(*self.args)
        except:
            traceback.print_exc()
        finally:
            del self.func, self.args

    def wait_event(self) -> any:
        """
        等待线程结束
        :return: 线程函数的返回值
        """
        self.join()
        return self.result
