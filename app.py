"""
Лаборатория сортировок — графическое приложение на tkinter.

Запуск:   python app.py
Нужно:    pip install matplotlib

Вкладки:
  1. График        — зависимость времени / сравнений / перестановок от размера массива
  2. Таблица       — все результаты замеров, экспорт в CSV
  3. Выводы        — рейтинг алгоритмов и эмпирическая оценка сложности
  4. Визуализация  — пошаговая анимация сортировки столбиками
"""

import queue
import random
import re
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import matplotlib

matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from algorithms import ALGORITHMS, THEORY
from data_generators import KINDS, DESCRIPTIONS, generate
from benchmark import run_benchmark, export_csv, build_conclusions, series
from visual_sorts import VISUAL_SORTS

# метрика -> (поле в Result, множитель)
METRICS = {
    "Время, мс": ("time_s", 1000),
    "Сравнения": ("comparisons", 1),
    "Перестановки / записи": ("moves", 1),
}

MAX_SIZE = 200_000


def fmt_int(x):
    return "—" if x is None else f"{x:,}".replace(",", " ")


def parse_sizes(text):
    """'100, 500; 1000' -> [100, 500, 1000]. Бросает ValueError при ошибке."""
    parts = [p for p in re.split(r"[,\s;]+", text.strip()) if p]
    if not parts:
        raise ValueError("Укажите хотя бы один размер массива.")
    sizes = []
    for p in parts:
        try:
            n = int(p)
        except ValueError:
            raise ValueError(f"«{p}» — не целое число. Пример: 100, 500, 1000") from None
        if n < 1 or n > MAX_SIZE:
            raise ValueError(f"Размер {n} вне допустимого диапазона 1…{MAX_SIZE}.")
        sizes.append(n)
    return sorted(set(sizes))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Лаборатория сортировок")
        self.geometry("1340x860")
        self.minsize(1100, 720)

        self.results = []
        self.params_text = ""
        self.cancel = threading.Event()
        self.msg_queue = queue.Queue()
        self.running = False
        self._closing = False

        # состояние анимации
        self.anim_data = []
        self.anim_work = []
        self.anim_gen = None
        self.anim_job = None
        self.anim_steps = 0
        self.anim_last = ([], (), False)

        self._build_layout()
        self.anim_new_array()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ------------------------------------------------------------------
    # Построение интерфейса
    # ------------------------------------------------------------------
    def _build_layout(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self, padding=10)
        left.grid(row=0, column=0, sticky="ns")
        self._build_left(left)

        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        self._build_chart_tab()
        self._build_table_tab()
        self._build_conclusions_tab()
        self._build_anim_tab()

    def _build_left(self, parent):
        # --- алгоритмы ---
        box = ttk.LabelFrame(parent, text="Алгоритмы", padding=8)
        box.pack(fill="x")
        self.alg_vars = {}
        for name in ALGORITHMS:
            var = tk.BooleanVar(value=True)
            self.alg_vars[name] = var
            ttk.Checkbutton(box, text=f"{name}   {THEORY[name]}", variable=var).pack(anchor="w")

        # --- типы данных ---
        box = ttk.LabelFrame(parent, text="Типы данных", padding=8)
        box.pack(fill="x", pady=(8, 0))
        self.kind_vars = {}
        for kind in KINDS:
            var = tk.BooleanVar(value=True)
            self.kind_vars[kind] = var
            ttk.Checkbutton(box, text=kind, variable=var).pack(anchor="w")

        # --- параметры ---
        box = ttk.LabelFrame(parent, text="Параметры эксперимента", padding=8)
        box.pack(fill="x", pady=(8, 0))
        box.columnconfigure(1, weight=1)

        ttk.Label(box, text="Размеры n:").grid(row=0, column=0, sticky="w", pady=2)
        self.sizes_var = tk.StringVar(value="100, 500, 1000, 2000, 5000")
        ttk.Entry(box, textvariable=self.sizes_var, width=26).grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(box, text="Повторов:").grid(row=1, column=0, sticky="w", pady=2)
        self.repeats_var = tk.StringVar(value="3")
        ttk.Spinbox(box, from_=1, to=20, textvariable=self.repeats_var, width=8).grid(row=1, column=1, sticky="w", pady=2)

        ttk.Label(box, text="Лимит, с:").grid(row=2, column=0, sticky="w", pady=2)
        self.limit_var = tk.StringVar(value="10")
        ttk.Spinbox(box, from_=1, to=600, textvariable=self.limit_var, width=8).grid(row=2, column=1, sticky="w", pady=2)

        ttk.Label(box, text="Seed:").grid(row=3, column=0, sticky="w", pady=2)
        self.seed_var = tk.StringVar(value="42")
        ttk.Entry(box, textvariable=self.seed_var, width=10).grid(row=3, column=1, sticky="w", pady=2)

        ttk.Label(
            box,
            text="Лимит: если алгоритм на размере n\nработал дольше, на бо́льших n\nон пропускается.",
            foreground="#666666",
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))

        # --- кнопки ---
        box = ttk.Frame(parent)
        box.pack(fill="x", pady=(10, 0))
        self.run_btn = ttk.Button(box, text="▶  Запустить эксперимент", command=self.start_benchmark)
        self.run_btn.pack(fill="x")
        self.stop_btn = ttk.Button(box, text="■  Остановить", command=self.stop_benchmark, state="disabled")
        self.stop_btn.pack(fill="x", pady=(4, 0))
        ttk.Button(box, text="Сохранить таблицу (CSV)", command=self.save_csv).pack(fill="x", pady=(10, 0))
        ttk.Button(box, text="Сохранить график (PNG)", command=self.save_chart).pack(fill="x", pady=(4, 0))

        # --- прогресс ---
        self.progress = ttk.Progressbar(parent, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(12, 2))
        self.status_var = tk.StringVar(value="Готово к запуску.")
        ttk.Label(parent, textvariable=self.status_var, wraplength=260, foreground="#444444").pack(anchor="w")

    def _build_chart_tab(self):
        tab = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab, text="  График  ")

        controls = ttk.Frame(tab)
        controls.pack(fill="x", pady=(0, 6))

        ttk.Label(controls, text="Показатель:").pack(side="left")
        self.metric_cb = ttk.Combobox(controls, values=list(METRICS), state="readonly", width=22)
        self.metric_cb.current(0)
        self.metric_cb.pack(side="left", padx=(4, 14))
        self.metric_cb.bind("<<ComboboxSelected>>", lambda e: self.redraw_chart())

        ttk.Label(controls, text="Тип данных:").pack(side="left")
        self.kind_cb = ttk.Combobox(controls, values=[], state="readonly", width=24)
        self.kind_cb.pack(side="left", padx=(4, 14))
        self.kind_cb.bind("<<ComboboxSelected>>", lambda e: self.redraw_chart())

        self.log_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls, text="Логарифмические оси", variable=self.log_var,
                        command=self.redraw_chart).pack(side="left")

        self.fig = Figure(figsize=(8, 5.5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=tab)
        toolbar = NavigationToolbar2Tk(self.canvas, tab)
        toolbar.update()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.redraw_chart()

    def _build_table_tab(self):
        tab = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab, text="  Таблица  ")
        cols = ("alg", "kind", "n", "time", "cmp", "mv", "ok")
        heads = ("Алгоритм", "Тип данных", "n", "Время, мс", "Сравнения", "Перестановки/записи", "Верно")
        widths = (170, 170, 80, 110, 130, 150, 60)
        self.tree = ttk.Treeview(tab, columns=cols, show="headings")
        for c, h, w in zip(cols, heads, widths):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="w" if c in ("alg", "kind") else "e")
        sb = ttk.Scrollbar(tab, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _build_conclusions_tab(self):
        tab = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab, text="  Выводы  ")
        self.text = tk.Text(tab, wrap="word", font=("Courier New", 10), padx=8, pady=8)
        sb = ttk.Scrollbar(tab, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        self.text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.set_conclusions()

    def _build_anim_tab(self):
        tab = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(tab, text="  Визуализация  ")

        controls = ttk.Frame(tab)
        controls.pack(fill="x", pady=(0, 6))

        ttk.Label(controls, text="Алгоритм:").pack(side="left")
        self.anim_alg_cb = ttk.Combobox(controls, values=list(VISUAL_SORTS), state="readonly", width=16)
        self.anim_alg_cb.current(0)
        self.anim_alg_cb.pack(side="left", padx=(4, 12))

        ttk.Label(controls, text="Данные:").pack(side="left")
        self.anim_kind_cb = ttk.Combobox(controls, values=KINDS, state="readonly", width=22)
        self.anim_kind_cb.current(0)
        self.anim_kind_cb.pack(side="left", padx=(4, 12))

        ttk.Label(controls, text="Элементов:").pack(side="left")
        self.anim_n_var = tk.StringVar(value="40")
        ttk.Spinbox(controls, from_=5, to=150, textvariable=self.anim_n_var, width=5).pack(side="left", padx=(4, 12))

        ttk.Label(controls, text="Задержка, мс:").pack(side="left")
        self.anim_speed = tk.IntVar(value=30)
        ttk.Scale(controls, from_=1, to=300, variable=self.anim_speed, orient="horizontal",
                  length=130).pack(side="left", padx=(4, 12))

        controls2 = ttk.Frame(tab)
        controls2.pack(fill="x", pady=(0, 6))
        ttk.Button(controls2, text="Новый массив", command=self.anim_new_array).pack(side="left")
        ttk.Button(controls2, text="▶ Старт", command=self.anim_start).pack(side="left", padx=6)
        ttk.Button(controls2, text="■ Стоп", command=self.anim_stop).pack(side="left")
        self.anim_status = tk.StringVar(value="")
        ttk.Label(controls2, textvariable=self.anim_status).pack(side="left", padx=16)

        self.anim_canvas = tk.Canvas(tab, bg="white", highlightthickness=1, highlightbackground="#cccccc")
        self.anim_canvas.pack(fill="both", expand=True)
        self.anim_canvas.bind("<Configure>", lambda e: self.anim_draw(*self.anim_last))

    # ------------------------------------------------------------------
    # Эксперимент (в отдельном потоке, чтобы окно не зависало)
    # ------------------------------------------------------------------
    def start_benchmark(self):
        names = [n for n, v in self.alg_vars.items() if v.get()]
        kinds = [k for k, v in self.kind_vars.items() if v.get()]
        if not names or not kinds:
            messagebox.showwarning("Нечего запускать", "Выберите хотя бы один алгоритм и один тип данных.")
            return
        try:
            sizes = parse_sizes(self.sizes_var.get())
            repeats = int(self.repeats_var.get())
            limit = float(self.limit_var.get().replace(",", "."))
            seed = int(self.seed_var.get())
            if repeats < 1 or limit <= 0:
                raise ValueError("Число повторов и лимит должны быть положительными.")
        except ValueError as e:
            messagebox.showerror("Проверьте параметры", str(e))
            return

        self.params_text = (f"Параметры: n = {', '.join(map(str, sizes))}; повторов = {repeats}; "
                            f"лимит = {limit:g} с; seed = {seed}\n")
        self.running = True
        self.cancel = threading.Event()
        self.run_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress.configure(value=0)
        self.status_var.set("Эксперимент запущен…")
        cancel = self.cancel

        def worker():
            try:
                res = run_benchmark(
                    names, kinds, sizes, repeats=repeats, time_limit=limit, seed=seed,
                    progress=lambda d, t, m: self.msg_queue.put(("progress", d, t, m)),
                    cancel=cancel)
                self.msg_queue.put(("done", res, cancel.is_set()))
            except Exception as exc:  # noqa: BLE001 — показываем любую ошибку пользователю
                self.msg_queue.put(("error", repr(exc)))

        threading.Thread(target=worker, daemon=True).start()
        self.after(100, self.poll_queue)

    def stop_benchmark(self):
        if self.running:
            self.cancel.set()
            self.status_var.set("Останавливаю… (дождёмся конца текущего замера)")

    def poll_queue(self):
        """Забирает сообщения из рабочего потока и обновляет интерфейс (в главном потоке)."""
        if self._closing:
            return
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                kind = msg[0]
                if kind == "progress":
                    _, done, total, text = msg
                    self.progress.configure(value=100 * done / max(total, 1))
                    self.status_var.set(f"{done}/{total}  {text}")
                elif kind == "done":
                    _, res, cancelled = msg
                    self.finish_benchmark(res, cancelled)
                elif kind == "error":
                    self.running = False
                    self.run_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    self.status_var.set("Ошибка при выполнении.")
                    messagebox.showerror("Ошибка", msg[1])
        except queue.Empty:
            pass
        if self.running:
            self.after(100, self.poll_queue)

    def finish_benchmark(self, res, cancelled):
        self.running = False
        self.results = res
        self.run_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        if not cancelled:
            self.progress.configure(value=100)
        self.status_var.set(("Остановлено пользователем. " if cancelled else "Готово. ")
                            + f"Получено замеров: {len(res)}.")
        self.fill_table()
        self.set_conclusions()

        kinds = []
        for r in res:
            if r.kind not in kinds:
                kinds.append(r.kind)
        self.kind_cb.configure(values=kinds)
        if kinds:
            self.kind_cb.current(0)
        self.redraw_chart()
        self.notebook.select(0)

    # ------------------------------------------------------------------
    # Отображение результатов
    # ------------------------------------------------------------------
    def redraw_chart(self):
        ax = self.ax
        ax.clear()
        kind = self.kind_cb.get()
        label = self.metric_cb.get()
        attr, factor = METRICS[label]
        log = self.log_var.get()
        plotted = False

        if kind:
            for name in ALGORITHMS:
                xs, ys = [], []
                for r in series(self.results, name, kind):
                    v = getattr(r, attr)
                    if v is None or (log and v <= 0):
                        continue
                    xs.append(r.size)
                    ys.append(v * factor)
                if xs:
                    ax.plot(xs, ys, marker="o", markersize=4, linewidth=1.6, label=name)
                    plotted = True

        if plotted:
            ax.set_xlabel("Размер массива n")
            ax.set_ylabel(label)
            ax.set_title(f"{label} — {kind}")
            if log:
                ax.set_xscale("log")
                ax.set_yscale("log")
            ax.grid(True, which="both", alpha=0.3)
            ax.legend(fontsize=8)
        else:
            ax.set_axis_off()
            ax.text(0.5, 0.5, "Нет данных для графика.\nНажмите «Запустить эксперимент».",
                    transform=ax.transAxes, ha="center", va="center", fontsize=12, color="#666666")
        self.fig.tight_layout()
        self.canvas.draw_idle()

    def fill_table(self):
        self.tree.delete(*self.tree.get_children())
        for r in self.results:
            if r.skipped:
                time_text = "пропущено"
            else:
                time_text = f"{r.time_s * 1000:.3f}"
            self.tree.insert("", "end", values=(
                r.algorithm, r.kind, fmt_int(r.size), time_text,
                fmt_int(r.comparisons), fmt_int(r.moves), "да" if r.correct else "НЕТ"))

    def set_conclusions(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        body = build_conclusions(self.results)
        if self.results:
            descr = "\n".join(f"  • {k}: {d}" for k, d in DESCRIPTIONS.items())
            self.text.insert("end", self.params_text + "\nТипы данных:\n" + descr + "\n\n")
        self.text.insert("end", body)
        self.text.configure(state="disabled")

    # ------------------------------------------------------------------
    # Сохранение
    # ------------------------------------------------------------------
    def save_csv(self):
        if not self.results:
            messagebox.showinfo("Нет данных", "Сначала запустите эксперимент.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile="results.csv")
        if path:
            try:
                export_csv(self.results, path)
                messagebox.showinfo("Готово", f"Таблица сохранена:\n{path}")
            except OSError as e:
                messagebox.showerror("Не удалось сохранить", str(e))

    def save_chart(self):
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")],
                                            initialfile="chart.png")
        if path:
            try:
                self.fig.savefig(path, dpi=200)
                messagebox.showinfo("Готово", f"График сохранён:\n{path}")
            except OSError as e:
                messagebox.showerror("Не удалось сохранить", str(e))

    # ------------------------------------------------------------------
    # Анимация сортировки
    # ------------------------------------------------------------------
    def _anim_size(self):
        try:
            n = int(self.anim_n_var.get())
        except ValueError:
            n = 40
        n = max(5, min(150, n))
        self.anim_n_var.set(str(n))
        return n

    def anim_new_array(self):
        self.anim_stop()
        n = self._anim_size()
        self.anim_data = generate(self.anim_kind_cb.get(), n, seed=random.randrange(10 ** 6))
        self.anim_status.set(f"Массив из {n} элементов. Нажмите «Старт».")
        self.anim_draw(self.anim_data, (), False)

    def anim_start(self):
        self.anim_stop()
        if len(self.anim_data) != self._anim_size():
            self.anim_new_array()
        self.anim_work = list(self.anim_data)
        self.anim_gen = VISUAL_SORTS[self.anim_alg_cb.get()](self.anim_work)
        self.anim_steps = 0
        self.anim_step()

    def anim_stop(self):
        if self.anim_job is not None:
            self.after_cancel(self.anim_job)
            self.anim_job = None
        self.anim_gen = None

    def anim_step(self):
        if self.anim_gen is None or self._closing:
            return
        try:
            state, active = next(self.anim_gen)
        except StopIteration:
            self.anim_job = None
            self.anim_gen = None
            self.anim_draw(self.anim_work, (), True)
            self.anim_status.set(f"Готово: {self.anim_steps} шагов анимации.")
            return
        self.anim_steps += 1
        self.anim_status.set(f"Шагов: {self.anim_steps}")
        self.anim_draw(state, active, False)
        self.anim_job = self.after(max(1, int(self.anim_speed.get())), self.anim_step)

    def anim_draw(self, arr, active, done):
        self.anim_last = (arr, active, done)
        c = self.anim_canvas
        c.delete("all")
        n = len(arr)
        if n == 0:
            return
        w = max(c.winfo_width(), 200)
        h = max(c.winfo_height(), 200)
        bar_w = w / n
        lo, hi = min(arr), max(arr)
        for i, v in enumerate(arr):
            frac = 1.0 if hi == lo else 0.06 + 0.94 * (v - lo) / (hi - lo)
            top = h - frac * (h - 12)
            if done:
                color = "#2e7d32"
            elif i in active:
                color = "#d32f2f"
            else:
                color = "#4a78c2"
            c.create_rectangle(i * bar_w + 1, top, (i + 1) * bar_w - 1, h, fill=color, outline="")

    # ------------------------------------------------------------------
    def on_close(self):
        self._closing = True
        self.cancel.set()
        self.anim_stop()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
