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
    root = tk.Tk()
    root.iconname('Label Point')
    root.iconbitmap('./myLabel.ico')  # 使用.ico格式的图标文件
    # root.geometry("600x400")  # 设置窗口大小，可以根据需要调整
    # load_images(label)  # 加载图片文件夹中的所有图片
    # 在主函数中创建按钮并绑定事件处理器
    ImageMarkingTool(root)
    root.mainloop()


class ImageMarkingTool:
    def __init__(self, master):
        self.config = {'folder_path': '/Users/tansss/Downloads/TY-LOCNet/data/inf/val',
                       'csv_path': '/Users/tansss/Downloads/TY-LOCNet/data/inf/val_label.csv'}
        self.master = master
        self.master.title("Label Point")
        self.name = None
        # img
        self.folder_path = None
        self.img_files = []
        self.img_index = 0
        self.img_path = None
        self.img_resize = 224
        self.img = None
        self.photo_image = None  # 转换为Tkinter支持的图像对象
        # csv
        self.csv_path = None
        self.df = None
        self.row_to_modify = None
        # 创建菜单栏和功能按钮
        menu_bar = tk.Menu(master)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="open folder", command=self.load_images)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=master.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)
        master.config(menu=menu_bar)

        # 创建显示区域和功能按钮
        fun_frame = tk.Frame(master, bg='#191920')
        fun_frame.pack(fill=tk.X)
        Button(fun_frame, bg='#131314', fg='#b5b8be', focuscolor='#131314', text="Previous Image",
               command=self.previous_image).pack(
            side=tk.LEFT)
        Button(fun_frame, bg='#131314', fg='#b5b8be', focuscolor='#131314', text="Next Image",
               command=self.next_image).pack(side=tk.LEFT)
        Button(fun_frame, bg='#131314', fg='#b5b8be', focuscolor='#131314', text="Reset Label",
               command=self.reset_label).pack(side=tk.LEFT)
        Button(fun_frame, bg='#131314', fg='#b5b8be', focuscolor='#131314', text="save CSV",
               command=self.save_csv).pack(side=tk.LEFT)
        # 创建文本框
        self.label_box = tk.Label(fun_frame, bg='#191920', foreground='#bcbebd')
        self.label_box.pack(side=tk.LEFT)
        self.label_box.config(width=20, height=2)  # 宽度为20个字符，高度为5行
        self.labeled_box = tk.Label(fun_frame, bg='#191920', foreground='#bcbebd')
        self.labeled_box.pack(side=tk.LEFT)
        self.labeled_box.config(width=20, height=2)  # 宽度为20个字符，高度为5行

        # canvas组件
        self.scale_factor = 1.0  # 缩放因子
        img_frame = tk.Frame(master)
        self.canvas = tk.Canvas(img_frame, highlightthickness=0)
        # 创建滚动区域
        self.v_scrollbar = ttk.Scrollbar(img_frame, orient='vertical', command=self.scroll_y)
        self.h_scrollbar = ttk.Scrollbar(img_frame, orient='horizontal', command=self.scroll_x)
        # 设置Canvas与滚动条关联
        self.canvas.config(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)
        # 将Canvas、滚动条放入frame中，并pack布局
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        img_frame.pack(fill=tk.BOTH, expand=True)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        # 监听鼠标事件
        self.canvas.bind('<ButtonPress-1>', self.mark_pixel)
        self.canvas.bind('<Motion>', self.on_mouse_move)
        self.canvas.bind('<MouseWheel>', self.on_mouse_wheel)
        # 监听键盘事件
        master.bind("<Left>", self.previous_image)  # 绑定左箭头快捷键到on_left_arrow函数
        master.bind("<Right>", self.next_image)  # 绑定右箭头快捷键到on_right_arrow函数
        master.mainloop()

    def on_frame_configure(self, event):
        """当内部frame大小改变时，更新Canvas滚动区域"""
        self.canvas.config(scrollregion=self.canvas.bbox('all'))

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
        if self.csv_path is None:  # 如果csv路径尚未设置（即第一次运行程序时）
            # self.csv_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[
            #     ("CSV Files", "*.csv")])  # 获取保存csv文件的路径和文件名（这里假设csv_path是ImageMarkingTool类的一个属性）
            self.csv_path = self.config['csv_path']
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
                messagebox.showwarning("csv data error", 'No matching filename found')
            else:
                messagebox.showwarning("csv data error", 'Finds a match for more than one row')

    def mark_pixel(self, event):
        if self.img is None:
            return None
        x_label, y_label = self.on_mouse_move()
        if x_label < self.img_resize and y_label < self.img_resize:
            self.update_label(x_label, y_label)

    def update_label(self, x_label, y_label):
        if self.df is None:
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
        date = datetime.datetime.now().strftime("%Y%m%d-%H%M")
        date = f'{self.csv_path.split(".")[0]}-{date}.csv'
        self.df.to_csv(date, index=False)

    def load_images(self):
        # self.folder_path = filedialog.askdirectory()  # 选择文件夹路径
        self.folder_path = self.config['folder_path']
        if self.folder_path:
            self.img_files = sorted(glob.glob('*.png', root_dir=self.folder_path))
            if self.img_files:  # 如果文件夹中有图片文件
                self.img_path = os.path.join(self.folder_path, self.img_files[0])  # 取第一张图片的路径
                self.process_image()  # 处理并显示第一张图片
            else:
                messagebox.showerror("Error", "No image files found in the folder.")
        else:
            messagebox.showerror("Error", "Failed to select a folder.")

    def process_image(self):
        self.img = Image.open(self.img_path).resize((self.img_resize, self.img_resize),
                                                    resample=Image.NEAREST)
        self.master.title(f'{self.img_path}(第{self.img_index + 1}张图片)')
        x_label, y_label = self.get_img_xy()
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
