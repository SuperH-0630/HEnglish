import tktool
import tkinter
import tkinter.ttk as ttk
import tkinter.filedialog as fd
import tkinter.messagebox as msg
from typing import List, Tuple, Callable, Optional
import abc

import db
import word


class HEnglishTkinter(tktool.TkEventMain, metaclass=abc.ABCMeta):
    tk_zoom = 1

    def set_after_run(self, ms, func, *args):  # 正常运行前设置定时任务 super.__init__可能会调用
        self.init_after_run_list.append((ms, func, args))

    def __conf_set_after_run(self):  # 配合 set_after_run 使用
        for ms, func, args in self.init_after_run_list:
            self.set_after_run_now(ms, func, *args)

    def set_after_run_now(self, ms, func, *args):  # 正常运行时设置定时任务
        self._window.after(ms, func, *args)

    def __init__(self, title: str,
                 top: Optional["HEnglishTkinter"] = None,
                 size: Tuple[float, float] = ((1 / 3), (2 / 3))):
        self.init_after_run_list: List[Tuple[int, Callable, Tuple]] = []
        super(HEnglishTkinter, self).__init__()

        if top:
            self._window = tkinter.Toplevel(top._window)
            top._window.lift()
        else:
            self._window = tkinter.Tk()

        self._sys_height = self._window.winfo_screenheight()
        self._sys_width = self._window.winfo_screenwidth()

        self._win_height = int(self._sys_height * size[1] * self.tk_zoom)  # 窗口高度
        self._win_width = int(self._sys_width * size[0] * self.tk_zoom)  # 窗口宽度

        self.__conf_windows(title)
        self.__conf_set_after_run()

    def __conf_windows(self, title: str):
        self._window.title(title)
        self._window.geometry(f'{self._win_width}x{self._win_height}')
        self._window['bg'] = '#F0FFFF'
        self._window.resizable(True, True)  # 禁止缩放
        self._window.overrideredirect(False)  # 显示标题栏
        self._window.bind('<Configure>', self.__window_resize)  # 调整界面大小
        self._window.minsize(int(self._sys_width * (1 / 3) * self.tk_zoom),
                             int(self._sys_height * (1 / 3) * self.tk_zoom))

        self._create_windows()
        self._set_windows()

    def __window_resize(self, event=None):
        if self._win_width != self._window.winfo_width() or self._win_height != self._window.winfo_height():
            self._win_height = self._window.winfo_height()
            self._win_width = self._window.winfo_width()
            self._set_windows()

    @abc.abstractmethod
    def _create_windows(self):
        pass

    @abc.abstractmethod
    def _set_windows(self):
        pass

    def mainloop(self):
        self._window.mainloop()


class HEnglish(HEnglishTkinter):
    about_info = """H-English 是一个使用剑桥词典的英语学习小工具。
使用Python+SQLite作为实现，爬取剑桥词典的英语单词。
本项目为开源项目，供免费学习使用。
产生任何法律问题本人概不负责。"""

    def __init__(self):
        super(HEnglish, self).__init__("H-English")
        self.db = db.WordDatabase()
        self.wd = self.db.wd

    def _create_windows(self):
        self._title_label = tkinter.Label(self._window)
        self._control_frame = tkinter.Frame(self._window)
        self._control_btn = [tkinter.Button(self._control_frame) for _ in range(6)]

    def _set_windows(self):
        self.__conf_title()
        self.__conf_control_btn()

    def __conf_title(self):
        if self._win_width >= self._win_height:
            font = tktool.make_font(size=int(self._win_height * 0.06), weight="bold")
        else:
            font = tktool.make_font(size=int(self._win_width * 0.05), weight="bold")
        self._title_label['font'] = font
        self._title_label['bg'] = '#F0FFFF'
        self._title_label['text'] = "Huan-English-Dictionary"  # 使用英语标题在GUI更美观
        self._title_label['anchor'] = 'c'
        self._title_label.place(relx=0.0, rely=0.03, relwidth=1.0, relheight=0.13)
        self._title = tkinter.Label()

    def __conf_control_btn(self):
        if self._win_width >= self._win_height:
            font = tktool.make_font(size=int(self._win_height * 0.03))
            self._control_btn[0].place(relx=0.07, rely=0.10, relwidth=0.4, relheight=0.2)
            self._control_btn[1].place(relx=0.53, rely=0.10, relwidth=0.4, relheight=0.2)
            self._control_btn[2].place(relx=0.07, rely=0.40, relwidth=0.4, relheight=0.2)
            self._control_btn[3].place(relx=0.53, rely=0.40, relwidth=0.4, relheight=0.2)
            self._control_btn[4].place(relx=0.07, rely=0.70, relwidth=0.4, relheight=0.2)
            self._control_btn[5].place(relx=0.53, rely=0.70, relwidth=0.4, relheight=0.2)
        else:
            font = tktool.make_font(size=int(self._win_width * 0.03))
            self._control_btn[0].place(relx=0.1, rely=0.08, relwidth=0.8, relheight=0.1)
            self._control_btn[1].place(relx=0.1, rely=0.23, relwidth=0.8, relheight=0.1)
            self._control_btn[2].place(relx=0.1, rely=0.38, relwidth=0.8, relheight=0.1)
            self._control_btn[3].place(relx=0.1, rely=0.53, relwidth=0.8, relheight=0.1)
            self._control_btn[4].place(relx=0.1, rely=0.68, relwidth=0.8, relheight=0.1)
            self._control_btn[5].place(relx=0.1, rely=0.83, relwidth=0.8, relheight=0.1)

        self._control_frame['bg'] = "#FFFFFF"
        self._control_frame['relief'] = "ridge"
        self._control_frame['bd'] = 5
        self._control_frame.place(relx=0.05, rely=0.20, relwidth=0.90, relheight=0.75)

        for i in zip(self._control_btn,
                     ["Word Test", "Dictionary", "Export", "Import", "Delete", "About"],
                     ["#DCDCDC", "#DCDCDC", "#DCDCDC", "#DCDCDC", "#DCDCDC", "#DCDCDC"],
                     [None, None, None, self.import_word, None, self.about]):
            i[0]['font'] = font
            i[0]['fg'] = "#000000"
            i[0]['bg'] = i[2]
            i[0]['activeforeground'] = "#FFFFFF"
            i[0]['activebackground'] = i[2]
            i[0]['anchor'] = 'c'
            i[0]['relief'] = "ridge"
            i[0]['bd'] = 5
            i[0]['text'] = i[1]
            i[0]['command'] = i[3]

    def import_word(self):
        Import(self, self._window)

    def about(self):
        msg.showinfo("关于", self.about_info)

    def show_loading(self, title: str):  # 有子线程时显示加载
        ...

    def stop_loading(self):  # 子线程运行完成后关闭加载
        ...

    def disable(self):
        self._window.state('icon')
        for i in self._control_btn:
            i['state'] = 'disable'

    def enable(self):
        self._window.state('normal')
        for i in self._control_btn:
            i['state'] = 'normal'


class Import(HEnglishTkinter):
    class ImportEvent(tktool.TkEventBase, metaclass=abc.ABCMeta):
        def __init__(self, imp: "Import"):
            super().__init__()
            self.imp = imp
            self.thread = None
            self.file = ""

        @abc.abstractmethod
        def func(self, *args):
            ...

        def get_title(self) -> str:
            return "Import"

        def start(self, *args):
            self.thread = tktool.TkThreading(self.func, *args)
            return self

        def done_after_event(self):
            res = self.thread.wait_event()
            if res:
                msg.showinfo("操作成功", f"成功从{self.file}中读取单词")

    class ImportFromText(ImportEvent):
        def __init__(self, imp: "Import"):
            super().__init__(imp)

        def func(self, file: str):
            self.file = file
            return self.imp._father.db.update_from_txt(file)

    class ImportFromTable(ImportEvent):
        def __init__(self, imp: "Import"):
            super().__init__(imp)

        def func(self, file: str, t: str):
            self.file = file
            return self.imp._father.db.update_from_table(file, t)

    def __init__(self, father: HEnglish, father_windows: tkinter.Tk):
        super(Import, self).__init__("Import", father, size=(1 / 3, 1 / 3))
        self._father = father
        self._father_windows = father_windows
        self._father.disable()
        self._window.protocol("WM_DELETE_WINDOW", self.close)

    def close(self):
        self._window.destroy()
        self._father.enable()

    def _create_windows(self):
        self._title_label = tkinter.Label(self._window)
        self._loading_pro = ttk.Progressbar(self._window)
        self._control_btn = [tkinter.Button(self._window) for _ in range(6)]

    def _set_windows(self):
        self.__conf_title()
        self.__conf_loader()
        self.__conf_control_btn()

    def __conf_title(self):
        if self._win_width >= self._win_height:
            font = tktool.make_font(size=int(self._win_height * 0.06), weight="bold")
        else:
            font = tktool.make_font(size=int(self._win_width * 0.05), weight="bold")
        self._title_label['font'] = font
        self._title_label['bg'] = '#F0FFFF'
        self._title_label['text'] = "Import Word"  # 使用英语标题在GUI更美观
        self._title_label['anchor'] = 'c'
        self._title_label.place(relx=0.0, rely=0.03, relwidth=1.0, relheight=0.13)
        self._title = tkinter.Label()

    def __conf_loader(self):
        self._loading_pro['mode'] = 'indeterminate'  # 来回显示
        self._loading_pro['orient'] = 'horizontal'  # 横向进度条
        self._loading_pro['maximum'] = 100

    def __conf_control_btn(self):
        if self._win_width >= self._win_height:
            font = tktool.make_font(size=int(self._win_height * 0.04))
            self._control_btn[0].place(relx=0.07, rely=0.28, relwidth=0.4, relheight=0.2)
            self._control_btn[1].place(relx=0.53, rely=0.28, relwidth=0.4, relheight=0.2)
            self._control_btn[2].place(relx=0.07, rely=0.66, relwidth=0.4, relheight=0.2)
            self._control_btn[3].place(relx=0.53, rely=0.66, relwidth=0.4, relheight=0.2)
        else:
            font = tktool.make_font(size=int(self._win_width * 0.04))
            self._control_btn[0].place(relx=0.1, rely=0.20, relwidth=0.8, relheight=0.1)
            self._control_btn[1].place(relx=0.1, rely=0.33, relwidth=0.8, relheight=0.1)
            self._control_btn[2].place(relx=0.1, rely=0.46, relwidth=0.8, relheight=0.1)
            self._control_btn[3].place(relx=0.1, rely=0.59, relwidth=0.8, relheight=0.1)

        for i in zip(self._control_btn,
                     ["From Text", "From CSV", "From Excel", "From Json"],
                     ["#DCDCDC", "#DCDCDC", "#DCDCDC", "#DCDCDC"],
                     [self.import_from_text, self.import_from_csv, self.import_from_excel, self.import_from_json]):
            i[0]['font'] = font
            i[0]['fg'] = "#000000"
            i[0]['bg'] = i[2]
            i[0]['activeforeground'] = "#FFFFFF"
            i[0]['activebackground'] = i[2]
            i[0]['anchor'] = 'c'
            i[0]['relief'] = "ridge"
            i[0]['bd'] = 5
            i[0]['text'] = i[1]
            i[0]['command'] = i[3]

    def import_from_text(self):
        file = fd.askopenfilename(filetypes=[("Text", ".txt"), ("All", "*")])
        if file != "":
            self.push_event(self.ImportFromText(self).start(file))

    def import_from_csv(self):
        file = fd.askopenfilename(filetypes=[("CSV", ".csv"), ("All", "*")])
        if file != "":
            self.push_event(self.ImportFromTable(self).start(file, "csv"))

    def import_from_excel(self):
        file = fd.askopenfilename(filetypes=[("Excel", ".xlsx"), ("All", "*")])
        if file != "":
            self.push_event(self.ImportFromTable(self).start(file, "excel"))

    def import_from_json(self):
        file = fd.askopenfilename(filetypes=[("Json", ".json"), ("All", "*")])
        if file != "":
            self.push_event(self.ImportFromTable(self).start(file, "json"))

    def show_loading(self, title: str):
        self._loading_pro['value'] = 0
        self._loading_pro.place(relx=0.10, rely=0.17, relwidth=0.80, relheight=0.05)
        self._loading_pro.start(50)

    def stop_loading(self):
        self._loading_pro.place_forget()
        self._loading_pro.stop()


if __name__ == '__main__':
    hgui = HEnglish()
    hgui.mainloop()
