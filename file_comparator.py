import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import shutil
import threading
import subprocess
import sys
from datetime import datetime

# 预设文件类型扩展名
PRESET_EXTENSIONS = {
    "图片文件": {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'},
    "视频文件": {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'},
    "文档文件": {'.txt', '.doc', '.docx', '.pdf', '.xls', '.xlsx', '.ppt', '.pptx', '.md'}
}

class FileComparatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("文件比较器工具")
        self.root.geometry("1050x850")
        
        # 状态变量
        self.is_running = False
        self.comparison_thread = None
        
        # 动态创建的对比文件夹选择组件（模式1使用）
        self.compare_folder_var = tk.StringVar()
        
        self.create_widgets()
        self.on_mode_changed()  # 初始化界面
        
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # 文件夹选择部分
        folder_frame = ttk.LabelFrame(main_frame, text="文件夹选择", padding="10")
        folder_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        folder_frame.columnconfigure(1, weight=1)
        
        # 基准文件夹
        ttk.Label(folder_frame, text="基准文件夹（参考文件夹）:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.base_folder_var = tk.StringVar()
        self.base_folder_entry = ttk.Entry(folder_frame, textvariable=self.base_folder_var, width=70)
        self.base_folder_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(folder_frame, text="浏览", command=self.select_base_folder).grid(row=0, column=2, padx=5)
        
        # 对比文件夹容器（动态内容）
        self.compare_container = ttk.Frame(folder_frame)
        self.compare_container.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.compare_container.columnconfigure(1, weight=1)
        
        # 输出目录
        ttk.Label(folder_frame, text="输出目录（保存增量文件）:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.output_folder_var = tk.StringVar()
        self.output_folder_entry = ttk.Entry(folder_frame, textvariable=self.output_folder_var, width=70)
        self.output_folder_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(folder_frame, text="浏览", command=self.select_output_folder).grid(row=2, column=2, padx=5)
        
        # 选项部分
        options_frame = ttk.LabelFrame(main_frame, text="选项", padding="10")
        options_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        options_frame.columnconfigure(1, weight=1)
        
        # 比较模式
        ttk.Label(options_frame, text="比较模式:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.comparison_mode = ttk.Combobox(options_frame, width=40, state="readonly")
        self.comparison_mode['values'] = ["指定基准 vs 指定对比", "基准文件夹 vs 对比文件夹（同父目录）"]
        self.comparison_mode.current(0)
        self.comparison_mode.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.comparison_mode.bind("<<ComboboxSelected>>", lambda e: self.on_mode_changed())
        
        # 文件类型
        ttk.Label(options_frame, text="文件类型:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.file_type = ttk.Combobox(options_frame, width=40, state="readonly")
        self.file_type['values'] = ["所有文件", "图片文件", "视频文件", "文档文件"]
        self.file_type.current(0)
        self.file_type.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        
        # 自定义扩展名
        ttk.Label(options_frame, text="自定义扩展名（逗号分隔，不含点）:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.custom_extensions_var = tk.StringVar()
        self.custom_extensions_entry = ttk.Entry(options_frame, textvariable=self.custom_extensions_var, width=40)
        self.custom_extensions_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5)
        
        # 选项复选框
        self.keep_relative_path = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="保留相对路径（拷贝时保持目录结构）", variable=self.keep_relative_path).grid(row=3, column=0, sticky=tk.W, pady=2)
        
        self.exclude_hidden = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="排除隐藏文件/目录", variable=self.exclude_hidden).grid(row=3, column=1, sticky=tk.W, pady=2)
        
        self.only_new_files = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="仅生成清单（不拷贝增量文件）", variable=self.only_new_files).grid(row=3, column=2, sticky=tk.W, pady=2)
        
        # 按钮部分
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="开始", command=self.start_comparison)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="停止", command=self.stop_comparison, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5)
        
        self.preview_button = ttk.Button(button_frame, text="预览", command=self.preview_folders)
        self.preview_button.grid(row=0, column=2, padx=5)
        
        ttk.Button(button_frame, text="打开输出目录", command=self.open_output_directory).grid(row=0, column=3, padx=5)
        ttk.Button(button_frame, text="另存清单", command=self.save_list).grid(row=0, column=4, padx=5)
        ttk.Button(button_frame, text="帮助", command=self.show_help).grid(row=0, column=5, padx=5)
        
        # 状态显示
        self.status_label = ttk.Label(main_frame, text="状态: 已停止")
        self.status_label.grid(row=3, column=0, sticky=tk.W, pady=5)
        
        # 合并的日志+预览区域
        output_frame = ttk.LabelFrame(main_frame, text="输出信息", padding="10")
        output_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, height=20)
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # 清空按钮
        clear_btn_frame = ttk.Frame(output_frame)
        clear_btn_frame.grid(row=1, column=0, pady=5)
        ttk.Button(clear_btn_frame, text="清空输出", command=self.clear_output).grid(row=0, column=0)
        
    def on_mode_changed(self):
        """根据比较模式动态显示不同的对比文件夹选择控件"""
        for widget in self.compare_container.winfo_children():
            widget.destroy()
            
        mode = self.comparison_mode.get()
        if mode == "指定基准 vs 指定对比":
            ttk.Label(self.compare_container, text="对比文件夹:").grid(row=0, column=0, sticky=tk.W, pady=2)
            self.compare_entry = ttk.Entry(self.compare_container, textvariable=self.compare_folder_var, width=70)
            self.compare_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
            ttk.Button(self.compare_container, text="浏览", command=self.select_compare_folder).grid(row=0, column=2, padx=5)
        else:
            ttk.Label(self.compare_container, text="基准子文件夹:").grid(row=0, column=0, sticky=tk.W, pady=2)
            self.base_subfolder = ttk.Combobox(self.compare_container, width=20, state="readonly")
            self.base_subfolder['values'] = ["a", "b", "c", "d"]
            self.base_subfolder.current(0)
            self.base_subfolder.grid(row=0, column=1, sticky=tk.W, padx=5)
            
            ttk.Label(self.compare_container, text="对比子文件夹:").grid(row=0, column=2, sticky=tk.W, pady=2)
            self.compare_subfolder = ttk.Combobox(self.compare_container, width=20, state="readonly")
            self.compare_subfolder['values'] = ["a", "b", "c", "d"]
            self.compare_subfolder.current(1)
            self.compare_subfolder.grid(row=0, column=3, sticky=tk.W, padx=5)
            
    def select_base_folder(self):
        folder = filedialog.askdirectory(title="选择基准文件夹")
        if folder:
            self.base_folder_var.set(folder)
            self.output(f"已选择基准目录: {folder}")
            
    def select_compare_folder(self):
        folder = filedialog.askdirectory(title="选择对比文件夹")
        if folder:
            self.compare_folder_var.set(folder)
            self.output(f"已选择对比目录: {folder}")
            
    def select_output_folder(self):
        folder = filedialog.askdirectory(title="选择输出目录")
        if folder:
            self.output_folder_var.set(folder)
            self.output(f"已选择输出目录: {folder}")
            
    def get_paths(self):
        """根据当前模式返回 (base_path, compare_path)"""
        base = self.base_folder_var.get()
        if not base:
            return None, None
        mode = self.comparison_mode.get()
        if mode == "指定基准 vs 指定对比":
            compare = self.compare_folder_var.get()
            if not compare:
                return None, None
            return base, compare
        else:
            base_sub = self.base_subfolder.get()
            compare_sub = self.compare_subfolder.get()
            if not base_sub or not compare_sub:
                return None, None
            return os.path.join(base, base_sub), os.path.join(base, compare_sub)
            
    def should_include_file(self, filename):
        """根据文件类型过滤决定是否包含该文件"""
        ext = os.path.splitext(filename)[1].lower()
        if not ext:
            return False
        mode = self.file_type.get()
        if mode == "所有文件":
            return True
        if mode in PRESET_EXTENSIONS:
            return ext in PRESET_EXTENSIONS[mode]
        return False
        
    def check_custom_extension(self, filename):
        """检查自定义扩展名（如果用户填写）"""
        custom = self.custom_extensions_var.get().strip()
        if not custom:
            return True
        ext = os.path.splitext(filename)[1].lower()
        if not ext:
            return False
        ext = ext[1:]  # 去掉点
        allowed = [e.strip().lower() for e in custom.split(',')]
        return ext in allowed
        
    def preview_folders(self):
        """预览两个文件夹的统计信息和增量文件清单"""
        base_path, compare_path = self.get_paths()
        if not base_path:
            self.output("错误: 请正确选择基准文件夹和对比文件夹")
            return
        if not os.path.exists(base_path):
            self.output(f"错误: 基准文件夹不存在: {base_path}")
            return
        if not compare_path or not os.path.exists(compare_path):
            self.output(f"错误: 对比文件夹不存在: {compare_path}")
            return
        
        def scan_and_preview():
            try:
                base_files = self.scan_folder(base_path)
                compare_files = self.scan_folder(compare_path)
                only_in_base = base_files - compare_files
                only_in_compare = compare_files - base_files
                common = base_files & compare_files
                
                # 输出统计信息
                msg = f"\n========== 预览统计 ==========\n"
                msg += f"基准文件夹: {base_path}\n"
                msg += f"对比文件夹: {compare_path}\n"
                msg += f"基准文件夹文件数: {len(base_files)}\n"
                msg += f"对比文件夹文件数: {len(compare_files)}\n"
                msg += f"仅在基准文件夹（增量）: {len(only_in_base)}\n"
                msg += f"仅在对比文件夹（冗余）: {len(only_in_compare)}\n"
                msg += f"共同文件: {len(common)}\n"
                msg += "===============================\n"
                
                # 输出增量文件清单（最多30条）
                if only_in_base:
                    msg += f"\n增量文件清单 (共{len(only_in_base)}个，显示前30个):\n"
                    for i, file in enumerate(sorted(only_in_base)):
                        if i >= 30:
                            msg += f"... 还有 {len(only_in_base)-30} 个文件未显示\n"
                            break
                        msg += f"  {file}\n"
                else:
                    msg += "\n没有增量文件（所有基准文件均在对比文件夹中存在）\n"
                    
                self.output(msg)
            except Exception as e:
                self.output(f"预览错误: {str(e)}")
        threading.Thread(target=scan_and_preview, daemon=True).start()
        
    def scan_folder(self, folder_path):
        """扫描文件夹，返回相对路径集合，根据过滤规则"""
        files = set()
        for root, dirs, files_in_dir in os.walk(folder_path):
            if self.exclude_hidden:
                dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files_in_dir:
                if self.exclude_hidden and file.startswith('.'):
                    continue
                if not self.should_include_file(file):
                    continue
                if not self.check_custom_extension(file):
                    continue
                rel_path = os.path.relpath(os.path.join(root, file), folder_path)
                if self.keep_relative_path:
                    files.add(rel_path)
                else:
                    files.add(file)
        return files
        
    def start_comparison(self):
        if self.is_running:
            return
        base_path, compare_path = self.get_paths()
        if not base_path or not compare_path:
            messagebox.showwarning("警告", "请完整填写基准文件夹和对比文件夹")
            return
        if not os.path.exists(base_path):
            messagebox.showwarning("警告", f"基准文件夹不存在: {base_path}")
            return
        if not os.path.exists(compare_path):
            messagebox.showwarning("警告", f"对比文件夹不存在: {compare_path}")
            return
        output_folder = self.output_folder_var.get()
        if not output_folder:
            messagebox.showwarning("警告", "请选择输出目录")
            return
        
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.preview_button.config(state=tk.DISABLED)
        self.status_label.config(text="状态: 运行中...")
        self.output(f"[{datetime.now().strftime('%H:%M:%S')}] 开始比较")
        self.output(f"基准: {base_path}")
        self.output(f"对比: {compare_path}")
        self.output(f"输出: {output_folder}")
        
        self.comparison_thread = threading.Thread(target=self.run_comparison, args=(base_path, compare_path, output_folder))
        self.comparison_thread.start()
        
    def stop_comparison(self):
        self.is_running = False
        self.output("正在停止...")
        
    def run_comparison(self, base_path, compare_path, output_folder):
        """在子线程中执行比较和拷贝操作"""
        try:
            os.makedirs(output_folder, exist_ok=True)
            
            self.output("开始扫描基准文件夹...")
            base_files = self.scan_folder(base_path)
            if not self.is_running:
                return
            self.output(f"基准文件夹扫描完成，共 {len(base_files)} 个文件")
            
            self.output("开始扫描对比文件夹...")
            compare_files = self.scan_folder(compare_path)
            if not self.is_running:
                return
            self.output(f"对比文件夹扫描完成，共 {len(compare_files)} 个文件")
            
            only_in_base = base_files - compare_files
            only_in_compare = compare_files - base_files
            common = base_files & compare_files
            
            self.output(f"差异统计: 新增 {len(only_in_base)}，冗余 {len(only_in_compare)}，共同 {len(common)}")
            
            # 生成清单CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            list_file = os.path.join(output_folder, f"增量清单_{timestamp}.csv")
            with open(list_file, 'w', encoding='utf-8') as f:
                f.write("文件比较清单\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"基准文件夹: {base_path}\n")
                f.write(f"对比文件夹: {compare_path}\n")
                f.write("\n文件列表:\n")
                f.write("文件路径,状态\n")
                for file in sorted(only_in_base):
                    f.write(f"{file},仅在基准文件夹存在（增量）\n")
                for file in sorted(only_in_compare):
                    f.write(f"{file},仅在对比文件夹存在（冗余）\n")
                for file in sorted(common):
                    f.write(f"{file},共同存在\n")
            self.output(f"清单已保存: {list_file}")
            
            # 显示新增文件清单（最多显示前30个）
            if only_in_base:
                self.output(f"\n新增文件清单 (共{len(only_in_base)}个):")
                display_list = sorted(only_in_base)[:30]
                for file in display_list:
                    self.output(f"  {file}")
                if len(only_in_base) > 30:
                    self.output(f"  ... 还有 {len(only_in_base)-30} 个文件未显示")
                self.output("")
            
            # 拷贝增量文件
            if not self.only_new_files.get() and only_in_base:
                self.output(f"开始拷贝增量文件到输出目录...")
                copied = 0
                for rel_path in only_in_base:
                    if not self.is_running:
                        self.output("用户停止了拷贝")
                        return
                    src = os.path.join(base_path, rel_path)
                    dst = os.path.join(output_folder, rel_path)
                    try:
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)
                        copied += 1
                        if copied % 50 == 0:
                            self.output(f"已拷贝 {copied}/{len(only_in_base)} 个文件")
                    except Exception as e:
                        self.output(f"拷贝失败 {rel_path}: {str(e)}")
                self.output(f"拷贝完成，共拷贝 {copied} 个文件")
            elif only_in_base:
                self.output("仅生成清单模式，未拷贝文件")
            else:
                self.output("没有增量文件需要拷贝")
                
            self.output(f"\n输出目录: {output_folder}")
            self.output("比较任务完成")
            self.status_label.config(text="状态: 已完成")
        except Exception as e:
            self.output(f"错误: {str(e)}")
            self.status_label.config(text="状态: 出错")
        finally:
            self.is_running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.preview_button.config(state=tk.NORMAL)
            
    # ---------- 线程安全的输出方法 ----------
    def output(self, message):
        """将消息输出到合并的文本区域（线程安全）"""
        self.root.after(0, self._output_safe, message)
        
    def _output_safe(self, message):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        self.output_text.insert(tk.END, f"{timestamp} {message}\n")
        self.output_text.see(tk.END)
        
    def clear_output(self):
        self.output_text.delete(1.0, tk.END)
        
    def open_output_directory(self):
        """跨平台打开输出目录，增强错误处理"""
        folder = self.output_folder_var.get()
        if not folder:
            messagebox.showwarning("警告", "未设置输出目录")
            return
        if not os.path.exists(folder):
            messagebox.showwarning("警告", f"输出目录不存在:\n{folder}")
            return
        
        # 尝试多种方式打开文件夹
        try:
            if sys.platform == 'win32':
                os.startfile(folder)
            elif sys.platform == 'darwin':  # macOS
                subprocess.Popen(['open', folder])
            else:  # Linux
                subprocess.Popen(['xdg-open', folder])
        except Exception as e:
            # 如果上述方法失败，给出手动提示
            messagebox.showerror("打开失败", f"无法自动打开目录，请手动打开:\n{folder}\n\n错误信息: {str(e)}")
            
    def save_list(self):
        """另存当前清单"""
        folder = self.output_folder_var.get()
        if not folder or not os.path.exists(folder):
            messagebox.showwarning("警告", "请先执行一次比较，或设置有效的输出目录")
            return
        files = [f for f in os.listdir(folder) if f.startswith("增量清单_") and f.endswith(".csv")]
        if not files:
            messagebox.showinfo("提示", "输出目录中没有找到清单文件")
            return
        latest = max(files, key=lambda x: os.path.getctime(os.path.join(folder, x)))
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=latest)
        if save_path:
            try:
                shutil.copy2(os.path.join(folder, latest), save_path)
                self.output(f"清单已另存为: {save_path}")
                messagebox.showinfo("成功", f"清单已另存到:\n{save_path}")
            except Exception as e:
                messagebox.showerror("保存失败", f"无法保存清单:\n{str(e)}")
            
    def show_help(self):
        """显示帮助窗口"""
        help_window = tk.Toplevel(self.root)
        help_window.title("帮助")
        help_window.geometry("650x550")
        help_window.transient(self.root)
        help_window.grab_set()
        
        text = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, font=("Consolas", 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        help_content = """
文件比较器工具使用帮助

1. 选择比较模式
   - 指定基准 vs 指定对比：比较两个完全独立的文件夹。
   - 基准文件夹 vs 对比文件夹（同父目录）：比较同一父目录下的两个子文件夹（如 a 和 b）。

2. 设置路径
   - 基准文件夹：参考文件夹（将从此处拷贝新增文件）。
   - 对比文件夹：根据模式选择另一个文件夹或子文件夹。
   - 输出目录：存放比较结果清单和拷贝的增量文件。

3. 文件过滤
   - 按类型过滤：可只比较图片、视频、文档等。
   - 自定义扩展名：例如输入 jpg,png,mp4（不含点）。
   - 排除隐藏文件：自动跳过以点开头的文件和目录。

4. 选项说明
   - 保留相对路径：拷贝时保持原目录结构（推荐）。
   - 仅生成清单：只输出 CSV 清单，不实际拷贝文件。

5. 操作步骤
   - 点击“预览”可快速查看两个文件夹的差异统计和增量文件清单。
   - 点击“开始”执行完整比较，并自动拷贝增量文件到输出目录。
   - 可随时点击“停止”中断操作。
   - 完成后可“打开输出目录”或“另存清单”。

6. 输出信息
   - 输出区域会显示详细的扫描日志、新增文件列表和拷贝进度。
   - 每次比较会生成一个以“增量清单_”开头的 CSV 文件，记录所有文件状态。

7. 常见问题
   - 无反应？请检查文件夹路径是否正确，输出目录是否可写。
   - 文件未过滤？自定义扩展名需用英文逗号分隔，不含点。
   - 拷贝失败？可能是文件被占用或权限不足，请检查目标目录。
   - 打开输出目录失败？请手动在文件管理器中打开提示的路径。

如有其他问题，请联系开发者。
"""
        text.insert(tk.END, help_content)
        text.config(state=tk.DISABLED)
        
        btn = ttk.Button(help_window, text="关闭", command=help_window.destroy)
        btn.pack(pady=10)
        
if __name__ == "__main__":
    root = tk.Tk()
    app = FileComparatorApp(root)
    root.mainloop()