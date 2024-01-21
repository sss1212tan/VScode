import configparser
import datetime
import glob
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageDraw, ImageOps
import pandas as pd
from tkmacosx import Button


# button的部分属性在mac不可调整， 比如无法改变button背景颜色，tkmacosx库，它提供的button按钮功能更全，并且还是跨平台的。
def main():
    app = ImageMarkingTool()
    app.mainloop()


class SettingsWindow:
    def __init__(self, master):
        self.master = master
        self.folder_path_var = tk.StringVar()
        self.csv_path_var = tk.StringVar()
        self.window = tk.Toplevel(master)
        self.window.transient(master)  # 设置子窗口与主窗口相关联
        self.window.grab_set()
        self.window.title("设置路径")
        self.section = 'path'
        self.key_csv = 'csv_file'
        self.key_folder = 'image_folder'
        self.config_file = 'config.ini'
        self.init_variables()
        # 添加标签和输入框（这里使用了Entry作为展示路径的控件）
        tk.Label(self.window, text="默认图片文件夹路径：").grid(row=0, column=0)
        storage_entry = tk.Entry(self.window, textvariable=self.folder_path_var, justify='center', width=30)
        storage_entry.grid(row=0, column=1, rowspan=1, columnspan=2)

        tk.Label(self.window, text="默认CSV文件路径：").grid(row=1, column=0)
        config_entry = tk.Entry(self.window, textvariable=self.csv_path_var, justify='center', width=30)
        config_entry.grid(row=1, column=1, rowspan=1, columnspan=2)

        # 添加选择文件/目录的按钮
        select_file_button = tk.Button(self.window, text="选择",
                                       command=lambda: self.select_path(self.folder_path_var,
                                                                        file_type=filedialog.askdirectory))
        select_file_button.grid(row=0, column=3)

        select_config_button = tk.Button(self.window, text="选择",
                                         command=lambda: self.select_path(self.csv_path_var,
                                                                          file_type=filedialog.askopenfilename))
        select_config_button.grid(row=1, column=3)
        # 在“确定”按钮上方添加横线
        separator = ttk.Separator(self.window, orient="horizontal")
        separator.grid(row=2, column=0, columnspan=4, sticky=tk.E + tk.W, pady=20)  # 横向扩展到三列
        # 添加确认或取消按钮，以符合模态窗口的特点
        cancel_button = tk.Button(self.window, text="取消", command=self.window.destroy)
        ok_button = tk.Button(self.window, text="确定", command=self.close_window)
        cancel_button.grid(row=3, column=1)  # 横向扩展填充整列
        ok_button.grid(row=3, column=2)  # 横向扩展填充整列

    def close_window(self):
        folder_path = self.folder_path_var.get()
        csv_path = self.csv_path_var.get()
        # 创建一个配置解析器对象
        config = configparser.ConfigParser()
        # 读取INI文件
        config.read(self.config_file)
        # 修改指定section下的指定key的值
        config.set(self.section, self.key_csv, csv_path)
        config.set(self.section, self.key_folder, folder_path)
        # 写入INI文件
        with open(self.config_file, 'w') as f:
            config.write(f)
            f.close()
        self.master.init_config()
        self.window.destroy()

    def init_variables(self):
        config = configparser.ConfigParser()
        if os.path.exists(self.config_file):
            config.read(self.config_file)
            if config.has_option(self.section, self.key_csv) and config.has_option(self.section, self.key_folder):
                csv_path = config.get(self.section, self.key_csv)
                folder_path = config.get(self.section, self.key_folder)
                self.csv_path_var.set(csv_path)
                self.folder_path_var.set(folder_path)

    def select_path(self, var, file_type):
        if file_type == filedialog.askopenfilename:
            path = file_type(
                title="选择CSV文件文件",
                initialdir="/path/to/default/directory",  # 设置初始目录
                filetypes=[('CSV文件', '*.csv')],  # 设置允许选择的文件类型
            )
        else:
            path = file_type()
        if path:
            var.set(path)

    def show(self):
        self.window.geometry('500x150')
        # 禁止用户通过鼠标拖动边缘来调整窗口大小
        self.window.resizable(False, False)
        self.window.mainloop()


class ImageMarkingTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.name = None
        # img
        self.folder_path = None
        self.img_files = []
        self.img_index = 0
        self.img_path = None
        self.img_resize = 224
        self.img = None
        self.photo_image = None  # 转换为Tkinter支持的图像对象
        self.scale_factor = 1.0  # 缩放因子
        # csv
        self.csv_path = None
        self.df = None
        self.row_to_modify = None
        # 创建菜单栏和功能按钮
        self.init_menu()
        # 创建显示区域和功能按钮
        fun_frame = tk.Frame(self)
        self.label_box = tk.Label(fun_frame)
        self.labeled_box = tk.Label(fun_frame)
        self.init_fun(fun_frame)
        # canvas组件
        img_frame = tk.Frame(self)
        self.canvas = tk.Canvas(img_frame)
        self.init_img(img_frame)
        # 初始化配置文件
        self.init_config()

    def open_settings(self):
        settings = SettingsWindow(self)
        settings.show()

    def init_config(self):
        # 创建一个配置解析器对象
        config = configparser.ConfigParser()
        section = 'path'
        key_csv = 'csv_file'
        key_folder = 'image_folder'
        if os.path.exists('config.ini'):
            # 读取INI文件
            config.read('config.ini')
            # 获取指定section下的指定key的值
            if config.has_option(section, key_csv) and config.has_option(section, key_folder):
                csv_path = config.get(section, key_csv)
                folder_path = config.get(section, key_folder)
                if (os.path.exists(csv_path) and os.path.exists(folder_path)
                        and os.path.splitext(csv_path)[-1] == '.csv'):
                    self.csv_path = csv_path
                    self.folder_path = folder_path
                    self.load_images()
        else:
            # 添加section和对应的key-value对
            config.add_section(section)
            config.set(section, key_csv, '')
            config.set(section, key_folder, '')
            # 写入INI文件
            with open('config.ini', 'w') as f:
                config.write(f)
                f.close()

    def init_menu(self):
        self.iconname('Label Point')
        self.iconbitmap('myLabel.ico')  # 使用.ico格式的图标文件
        menu_bar = tk.Menu(self)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Settings", command=self.open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menu_bar)
        self.title("Label Point")
        # 监听键盘事件
        self.bind("<Left>", self.previous_image)  # 绑定左箭头快捷键到on_left_arrow函数
        self.bind("<Right>", self.next_image)  # 绑定右箭头快捷键到on_right_arrow函数

    def init_fun(self, fun_frame):
        bg_btn = '#131314'
        fg_btn = '#b5b8be'
        focuscolor = '#131314'
        bg = '#191920'
        fg = '#bcbebd'
        fun_frame.config(bg=bg)
        fun_frame.pack(fill=tk.X)
        Button(fun_frame, bg=bg_btn, fg=fg_btn, focuscolor=focuscolor, text="Previous Image",
               command=self.previous_image).pack(
            side=tk.LEFT)
        Button(fun_frame, bg=bg_btn, fg=fg_btn, focuscolor=focuscolor, text="Next Image",
               command=self.next_image).pack(side=tk.LEFT)
        Button(fun_frame, bg=bg_btn, fg=fg_btn, focuscolor=focuscolor, text="Reset Label",
               command=self.reset_label).pack(side=tk.LEFT)
        Button(fun_frame, bg=bg_btn, fg=fg_btn, focuscolor=focuscolor, text="save CSV",
               command=self.save_csv).pack(side=tk.LEFT)
        # 创建文本框
        self.label_box.pack(side=tk.LEFT)
        self.label_box.config(width=20, height=2, bg=bg, foreground=fg)  # 宽度为20个字符，高度为5行
        self.labeled_box.pack(side=tk.LEFT)
        self.labeled_box.config(width=20, height=2, bg=bg, foreground=fg)  # 宽度为20个字符，高度为5行

    def init_img(self, img_frame):
        # 创建滚动区域
        v_scrollbar = ttk.Scrollbar(img_frame, orient='vertical', command=self.scroll_y)
        h_scrollbar = ttk.Scrollbar(img_frame, orient='horizontal', command=self.scroll_x)
        # 设置Canvas与滚动条关联
        self.canvas.config(highlightthickness=0, yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        # 将Canvas、滚动条放入frame中，并pack布局
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        img_frame.pack(fill=tk.BOTH, expand=True)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        # 监听鼠标事件
        self.canvas.bind('<ButtonPress-1>', self.mark_pixel)
        self.canvas.bind('<Motion>', self.on_mouse_move)
        self.canvas.bind('<MouseWheel>', self.on_mouse_wheel)

    def scroll_y(self, *args):
        """响应垂直滚动条"""
        self.canvas.yview(*args)

    def scroll_x(self, *args):
        """响应水平滚动条"""
        self.canvas.xview(*args)

    def on_mouse_wheel(self, event):
        delta = event.delta / 120  # 滚轮滚动的角度，通常为120单位/每次滚动
        self.scale_factor += delta * 0.1  # 示例：增加或减少10%的缩放比例
        self.scale_factor = max(0.1, min(5.0, self.scale_factor))  # 设置缩放范围限制
        self.update_display()

    def on_mouse_move(self, event=None):
        # 获取鼠标指针在原图上的像素位置
        if self.img is not None:
            canvas_pos = self.canvas.winfo_pointerxy()
            # canvas_pos是鼠标指针相对于窗口的坐标，再减去窗口左上角的坐标,加上滚动的距离canvasx
            x = canvas_pos[0] - self.canvas.winfo_rootx() + self.canvas.canvasx(0)  # 抵消水平滚动的距离
            y = canvas_pos[1] - self.canvas.winfo_rooty() + self.canvas.canvasy(0)  # 抵消垂直滚动的距离
            # 根据缩放因子转换到原图坐标
            img_x = x / self.scale_factor
            img_y = y / self.scale_factor
            pixel_color = "无"
            if img_x < self.img_resize and img_y < self.img_resize:
                pixel_color = self.img.getpixel((int(img_x), int(img_y)))
            self.label_box['text'] = f"像素标号: ({img_x:.2f}, {img_y:.2f})\n颜色：{pixel_color}"  # 插入新的文本
            return img_x, img_y

    def get_img_xy(self):
        if self.csv_path is None:  # 如果csv路径尚未设置
            return
            # csv对于字符串类型支持不友好，index必须是数字类型，否则不兼容
        self.df = pd.read_csv(self.csv_path, converters={'filename': str, 'x': float, 'y': float})
        self.name = self.img_path.split('/')[-1].split('.')[0]
        self.row_to_modify = self.df['filename'] == self.name
        target_row = self.df.loc[self.row_to_modify]
        # 由于可能找到多行或找不到匹配项，需要检查结果
        if target_row.shape[0] == 1:
            # 如果找到一行，则提取这一行数据
            x_percent, y_percent = self.df.loc[self.row_to_modify].iloc[0][1:3]
            # 图片像素按索引存取
            x = (self.img_resize - 1) * x_percent
            y = (self.img_resize - 1) * y_percent
            self.labeled_box['text'] = f"标记位置：({x:.2f},{y:.2f})\n百分比: ({x_percent:.2f}, {y_percent:.2f})"
            return x, y
        else:
            if target_row.empty:
                messagebox.showwarning("csv data error", f'No matching filename found:{self.name}')
            else:
                messagebox.showwarning("csv data error", f'Finds a match({self.name}) for more than one row:\n'
                                                         f'{self.df.loc[self.row_to_modify]}')
            self.clear_data()

    def mark_pixel(self, event):
        if self.img is None:
            return None
        x_label, y_label = self.on_mouse_move()
        if x_label < self.img_resize and y_label < self.img_resize:
            self.update_label(x_label, y_label)

    def update_label(self, x_label, y_label):
        if self.df is None or self.img_path is None:
            messagebox.showwarning("csv data error", 'please select csv file when show image')
            return
        # 图片像素按索引存取
        x_percent = x_label / (self.img_resize - 1)
        y_percent = y_label / (self.img_resize - 1)
        self.df.loc[self.row_to_modify, ['filename', 'x', 'y']] = [self.name, x_percent, y_percent]
        # 确保至少找到一行匹配项
        if self.row_to_modify.any():
            # 保存修改后的DataFrame回原CSV文件或其他新文件
            self.df.to_csv(self.csv_path, index=False, mode='w')  # 使用追加模式写入csv文件
            self.add_rect(x_label, y_label)
            self.labeled_box[
                'text'] = f"标记位置：({x_label:.2f},{y_label:.2f})\n百分比: ({x_percent:.2f}, {y_percent:.2f})"
        else:
            messagebox.showwarning("csv data error", 'not found image filename in csv')

    def add_rect(self, x, y):
        # messagebox.showinfo("Success", f"Saved to {self.csv_path}")
        # 创建一个ImageDraw对象，用于在图片上绘制像素点
        draw = ImageDraw.Draw(self.img)
        # 定义矩形的左上角和右下角坐标
        differ = 0.5
        rectangle_top_left = (x - differ, y - differ)  # 调整矩形大小和位置，根据需要修改坐标值
        rectangle_bottom_right = (x + differ, y + differ)  # 调整矩形大小和位置，根据需要修改坐标值

        # 在图片上绘制矩形
        draw.rectangle([rectangle_top_left, rectangle_bottom_right], fill=(255, 0, 0))  # RGB颜色为红色(255, 0, 0)

        # 将处理后的图片更新到Label上显示
        self.update_display()

    def reset_label(self):
        reset = 0.5 * (self.img_resize - 1)
        self.update_label(reset, reset)

    def save_csv(self):
        if self.csv_path:
            date = datetime.datetime.now().strftime("%Y%m%d-%H%M")
            date = f'{self.csv_path.split(".")[0]}-{date}.csv'
            self.df.to_csv(date, index=False)

    def load_images(self):
        if self.folder_path:
            self.img_files = sorted(glob.glob('*.png', root_dir=self.folder_path))
            if self.img_files:  # 如果文件夹中有图片文件
                self.img_index = 0
                self.img_path = os.path.join(self.folder_path, self.img_files[self.img_index])  # 取第一张图片的路径
                self.process_image()  # 处理并显示第一张图片
            else:
                messagebox.showerror("Error", "No image files found in the folder.")
                self.clear_data()
        else:
            messagebox.showerror("Error", "Failed to select a folder.")

    def clear_data(self):
        self.canvas.delete('all')
        self.img = None
        self.label_box['text'] = ''
        self.labeled_box['text'] = ''
        self.img_path = None
        self.img_index = 0
        self.csv_path = None
        self.df = None
        self.row_to_modify = None

    def process_image(self):
        result = self.get_img_xy()
        if result is None:
            return
        self.img = Image.open(self.img_path).resize((self.img_resize, self.img_resize),
                                                    resample=Image.NEAREST)
        self.title(f'{self.img_path}(第{self.img_index + 1}张图片)')
        x_label, y_label = result
        self.add_rect(x_label, y_label)

    def update_display(self):
        if self.img:
            scaled_img = ImageOps.scale(self.img, self.scale_factor, resample=Image.NEAREST)
            self.photo_image = ImageTk.PhotoImage(scaled_img)
            self.canvas.delete('all')
            self.canvas.create_image(0, 0, anchor='nw', image=self.photo_image)
            self.canvas.config(scrollregion=self.canvas.bbox('all'))  # 设置滚动区域为图片的实际大小

    def next_image(self, event=None):
        if self.img_index < len(self.img_files) - 1:  # 如果不是最后一张图片
            self.img_index += 1  # 下一张图片的索引
            self.img_path = os.path.join(self.folder_path, self.img_files[self.img_index])  # 更新图片路径
            self.process_image()  # 显示下一张图片

    def previous_image(self, event=None):
        if self.img_index > 0:  # 如果不是第一张图片
            self.img_index -= 1  # 上一张图片的索引
            self.img_path = os.path.join(self.folder_path, self.img_files[self.img_index])  # 更新图片路径
            self.process_image()  # 显示上一张图片


if __name__ == "__main__":
    main()
