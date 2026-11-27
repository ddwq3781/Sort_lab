
"""
Запуск:   python app.py
Нужно:    pip install matplotlib
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
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from algorithms import ALGORITHMS, THEORY
from data_generators import KINDS, DESCRIPTIONS, generate
from benchmark import run_benchmark, export_csv, build_conclusions, series
from visual_sorts import VISUAL_SORTS


METRICS = {
    "Время, мс": ("time_s", 1000),
    "Сравнения": ("comparisons", 1),
    "Перестановки / записи": ("moves", 1),
}

MAX_SIZE = 200_000

root = None

results = []
params_text = ""

cancel = threading.Event()
msg_queue = queue.Queue()
running = False
closing = False

anim_data = []
anim_work = []
anim_gen = None
anim_job = None
anim_steps = 0
anim_last = ([], (), False)

alg_vars = {}
kind_vars = {}

sizes_var = None
repeats_var = None
limit_var = None
seed_var = None

run_btn = None
stop_btn = None
progress = None
status_var = None

notebook = None

metric_cb = None
kind_cb = None

fig = None
ax = None
canvas = None

tree = None
text = None

anim_alg_cb = None
anim_kind_cb = None
anim_n_var = None
anim_speed = None
anim_status = None
anim_canvas = None


def fmt_int(x):
    if x is None:
        return "—"
    return f"{x:,}".replace(",", " ")


def parse_sizes(text):
    parts = [p for p in re.split(r"[,\s;]+", text.strip()) if p]

    if not parts:
        raise ValueError("Укажите хотя бы один размер массива.")

    sizes = []

    for p in parts:
        try:
            n = int(p)
        except ValueError:
            raise ValueError(
                f"«{p}» — не целое число. Пример: 100, 500, 1000"
            ) from None

        if n < 1 or n > MAX_SIZE:
            raise ValueError(
                f"Размер {n} вне допустимого диапазона 1…{MAX_SIZE}."
            )

        sizes.append(n)

    sizes = sorted(set(sizes))

    return sizes


# Построение интерфейса

def create_interface():
    global notebook

    root.columnconfigure(1, weight=1)
    root.rowconfigure(0, weight=1)

    left = ttk.Frame(root, padding=10)
    left.grid(row=0, column=0, sticky="ns")

    create_left_panel(left)

    notebook = ttk.Notebook(root)
    notebook.grid(
        row=0,
        column=1,
        sticky="nsew",
        padx=(0, 10),
        pady=10
    )

    create_chart_tab()
    create_table_tab()
    create_conclusions_tab()
    create_anim_tab()


def create_left_panel(parent):
    global sizes_var
    global repeats_var
    global limit_var
    global seed_var
    global run_btn
    global stop_btn
    global progress
    global status_var

    box = ttk.LabelFrame(parent, text="Алгоритмы", padding=8)
    box.pack(fill="x")

    for name in ALGORITHMS:
        var = tk.BooleanVar(value=True)
        alg_vars[name] = var

        ttk.Checkbutton(
            box,
            text=f"{name}   {THEORY[name]}",
            variable=var
        ).pack(anchor="w")

    box = ttk.LabelFrame(parent, text="Типы данных", padding=8)
    box.pack(fill="x", pady=(8, 0))

    for kind in KINDS:
        var = tk.BooleanVar(value=True)
        kind_vars[kind] = var

        ttk.Checkbutton(
            box,
            text=kind,
            variable=var
        ).pack(anchor="w")

    box = ttk.LabelFrame(parent, text="Параметры эксперимента", padding=8)
    box.pack(fill="x", pady=(8, 0))

    box.columnconfigure(1, weight=1)

    ttk.Label(box, text="Размеры n:").grid(
        row=0, column=0, sticky="w", pady=2
    )

    sizes_var = tk.StringVar(
        value="100, 500, 1000, 2000, 5000"
    )

    ttk.Entry(
        box,
        textvariable=sizes_var,
        width=26
    ).grid(row=0, column=1, sticky="ew", pady=2)

    ttk.Label(box, text="Повторов:").grid(
        row=1, column=0, sticky="w", pady=2
    )

    repeats_var = tk.StringVar(value="3")

    ttk.Spinbox(
        box,
        from_=1,
        to=20,
        textvariable=repeats_var,
        width=8
    ).grid(row=1, column=1, sticky="w", pady=2)

    ttk.Label(box, text="Лимит, с:").grid(
        row=2, column=0, sticky="w", pady=2
    )

    limit_var = tk.StringVar(value="10")

    ttk.Spinbox(
        box,
        from_=1,
        to=600,
        textvariable=limit_var,
        width=8
    ).grid(row=2, column=1, sticky="w", pady=2)

    ttk.Label(box, text="Seed:").grid(
        row=3, column=0, sticky="w", pady=2
    )

    seed_var = tk.StringVar(value="42")

    ttk.Entry(
        box,
        textvariable=seed_var,
        width=10
    ).grid(row=3, column=1, sticky="w", pady=2)

    ttk.Label(
        box,
        text="Лимит: если алгоритм на размере n\n"
             "работал дольше, на бо́льших n\n"
             "он пропускается.",
        foreground="#666666"
    ).grid(
        row=4,
        column=0,
        columnspan=2,
        sticky="w",
        pady=(6, 0)
    )

    box = ttk.Frame(parent)
    box.pack(fill="x", pady=(10, 0))

    run_btn = ttk.Button(
        box,
        text="▶  Запустить эксперимент",
        command=start_benchmark
    )
    run_btn.pack(fill="x")

    stop_btn = ttk.Button(
        box,
        text="■  Остановить",
        command=stop_benchmark,
        state="disabled"
    )
    stop_btn.pack(fill="x", pady=(4, 0))

    ttk.Button(
        box,
        text="Сохранить таблицу (CSV)",
        command=save_csv
    ).pack(fill="x", pady=(10, 0))

    ttk.Button(
        box,
        text="Сохранить график (PNG)",
        command=save_chart
    ).pack(fill="x", pady=(4, 0))

    progress = ttk.Progressbar(
        parent,
        mode="determinate",
        maximum=100
    )
    progress.pack(fill="x", pady=(12, 2))

    status_var = tk.StringVar(value="Готово к запуску.")

    ttk.Label(
        parent,
        textvariable=status_var,
        wraplength=260,
        foreground="#444444"
    ).pack(anchor="w")


def create_chart_tab():
    global metric_cb
    global kind_cb
    global fig
    global ax
    global canvas

    tab = ttk.Frame(notebook, padding=6)
    notebook.add(tab, text="  График  ")

    controls = ttk.Frame(tab)
    controls.pack(fill="x", pady=(0, 6))

    ttk.Label(controls, text="Показатель:").pack(side="left")

    metric_cb = ttk.Combobox(
        controls,
        values=list(METRICS),
        state="readonly",
        width=22
    )
    metric_cb.current(0)
    metric_cb.pack(side="left", padx=(4, 14))
    metric_cb.bind("<<ComboboxSelected>>", redraw_chart)

    ttk.Label(controls, text="Тип данных:").pack(side="left")

    kind_cb = ttk.Combobox(
        controls,
        values=[],
        state="readonly",
        width=24
    )
    kind_cb.pack(side="left", padx=(4, 14))
    kind_cb.bind("<<ComboboxSelected>>", redraw_chart)

    fig = Figure(figsize=(8, 5.5), dpi=100)
    ax = fig.add_subplot(111)

    canvas = FigureCanvasTkAgg(fig, master=tab)

    canvas.get_tk_widget().pack(fill="both", expand=True)

    redraw_chart()


def create_table_tab():
    global tree

    tab = ttk.Frame(notebook, padding=10)
    notebook.add(tab, text="  Таблица  ")

    ttk.Label(
        tab,
        text="Результаты эксперимента",
        font=("Segoe UI", 13, "bold")
    ).pack(anchor="w", pady=(0, 3))

    ttk.Label(
        tab,
        text="Время указано в миллисекундах. Пропущенные замеры отмечены отдельно.",
        foreground="#666666"
    ).pack(anchor="w", pady=(0, 10))

    table_frame = ttk.Frame(tab)
    table_frame.pack(fill="both", expand=True)

    cols = ("alg", "kind", "n", "time", "cmp", "mv", "ok")

    heads = (
        "Алгоритм",
        "Тип данных",
        "Размер массива",
        "Время, мс",
        "Сравнения",
        "Перестановки / записи",
        "Результат"
    )

    widths = (175, 165, 115, 105, 120, 165, 105)

    style = ttk.Style(root)
    style.configure(
        "Results.Treeview",
        font=("Segoe UI", 10),
        rowheight=29
    )
    style.configure(
        "Results.Treeview.Heading",
        font=("Segoe UI", 10, "bold"),
        padding=(6, 9)
    )

    tree = ttk.Treeview(
        table_frame,
        columns=cols,
        show="headings",
        style="Results.Treeview"
    )

    for c, h, w in zip(cols, heads, widths):
        tree.heading(c, text=h)

        anchor = "w" if c in ("alg", "kind") else "center"
        tree.column(c, width=w, minwidth=75, anchor=anchor, stretch=True)

    tree.tag_configure("even", background="#f3f6fa")
    tree.tag_configure("odd", background="#ffffff")
    tree.tag_configure("wrong", background="#fce8e6")
    tree.tag_configure("skipped", foreground="#777777")

    vertical = ttk.Scrollbar(
        table_frame,
        orient="vertical",
        command=tree.yview
    )
    horizontal = ttk.Scrollbar(
        table_frame,
        orient="horizontal",
        command=tree.xview
    )

    tree.configure(
        yscrollcommand=vertical.set,
        xscrollcommand=horizontal.set
    )

    tree.grid(row=0, column=0, sticky="nsew")
    vertical.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")

    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)


def create_conclusions_tab():
    global text

    tab = ttk.Frame(notebook, padding=6)
    notebook.add(tab, text="  Выводы  ")

    text = tk.Text(
        tab,
        wrap="word",
        font=("Courier New", 10),
        padx=8,
        pady=8
    )

    sb = ttk.Scrollbar(
        tab,
        orient="vertical",
        command=text.yview
    )

    text.configure(yscrollcommand=sb.set)

    text.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    set_conclusions()


def create_anim_tab():
    global anim_alg_cb
    global anim_kind_cb
    global anim_n_var
    global anim_speed
    global anim_status
    global anim_canvas

    tab = ttk.Frame(notebook, padding=6)
    notebook.add(tab, text="  Визуализация  ")

    controls = ttk.Frame(tab)
    controls.pack(fill="x", pady=(0, 6))

    ttk.Label(controls, text="Алгоритм:").pack(side="left")

    anim_alg_cb = ttk.Combobox(
        controls,
        values=list(VISUAL_SORTS),
        state="readonly",
        width=16
    )
    anim_alg_cb.current(0)
    anim_alg_cb.pack(side="left", padx=(4, 12))

    ttk.Label(controls, text="Данные:").pack(side="left")

    anim_kind_cb = ttk.Combobox(
        controls,
        values=KINDS,
        state="readonly",
        width=22
    )
    anim_kind_cb.current(0)
    anim_kind_cb.pack(side="left", padx=(4, 12))

    ttk.Label(controls, text="Элементов:").pack(side="left")

    anim_n_var = tk.StringVar(value="40")

    ttk.Spinbox(
        controls,
        from_=5,
        to=150,
        textvariable=anim_n_var,
        width=5
    ).pack(side="left", padx=(4, 12))

    ttk.Label(controls, text="Задержка, мс:").pack(side="left")

    anim_speed = tk.IntVar(value=30)

    ttk.Scale(
        controls,
        from_=1,
        to=300,
        variable=anim_speed,
        orient="horizontal",
        length=130
    ).pack(side="left", padx=(4, 12))

    controls2 = ttk.Frame(tab)
    controls2.pack(fill="x", pady=(0, 6))

    ttk.Button(
        controls2,
        text="Новый массив",
        command=anim_new_array
    ).pack(side="left")

    ttk.Button(
        controls2,
        text="▶ Старт",
        command=anim_start
    ).pack(side="left", padx=6)

    ttk.Button(
        controls2,
        text="■ Стоп",
        command=anim_stop
    ).pack(side="left")

    anim_status = tk.StringVar(value="")

    ttk.Label(
        controls2,
        textvariable=anim_status
    ).pack(side="left", padx=16)

    anim_canvas = tk.Canvas(
        tab,
        bg="white",
        highlightthickness=1,
        highlightbackground="#cccccc"
    )

    anim_canvas.pack(fill="both", expand=True)

    anim_canvas.bind(
        "<Configure>",
        anim_canvas_resized
    )


def anim_canvas_resized(event=None):
    anim_draw(*anim_last)


# Эксперимент (в отдельном потоке, чтобы окно не зависало)

def selected_items(variables):
    return [name for name, var in variables.items() if var.get()]


def start_benchmark():
    global params_text
    global running
    global cancel

    names = selected_items(alg_vars)
    kinds = selected_items(kind_vars)

    if not names or not kinds:
        messagebox.showwarning(
            "Нечего запускать",
            "Выберите хотя бы один алгоритм и один тип данных."
        )
        return

    try:
        sizes = parse_sizes(sizes_var.get())

        repeats = int(repeats_var.get())

        limit = float(
            limit_var.get().replace(",", ".")
        )

        seed = int(seed_var.get())

        if repeats < 1 or limit <= 0:
            raise ValueError(
                "Число повторов и лимит должны быть положительными."
            )

    except ValueError as e:
        messagebox.showerror(
            "Проверьте параметры",
            str(e)
        )
        return

    params_text = (
        f"Параметры: n = {', '.join(map(str, sizes))}; "
        f"повторов = {repeats}; "
        f"лимит = {limit:g} с; seed = {seed}\n"
    )

    running = True
    cancel = threading.Event()

    run_btn.configure(state="disabled")
    stop_btn.configure(state="normal")

    progress.configure(value=0)
    status_var.set("Эксперимент запущен…")

    worker_thread = threading.Thread(
        target=benchmark_worker,
        args=(names, kinds, sizes, repeats, limit, seed, cancel),
        daemon=True
    )

    worker_thread.start()

    root.after(100, poll_queue)


def benchmark_worker(names, kinds, sizes, repeats, limit, seed, stop_event):
    try:
        res = run_benchmark(
            names,
            kinds,
            sizes,
            repeats=repeats,
            time_limit=limit,
            seed=seed,
            progress=benchmark_progress,
            cancel=stop_event
        )

        msg_queue.put(
            ("done", res, stop_event.is_set())
        )

    except Exception as exc:
        msg_queue.put(
            ("error", repr(exc))
        )


def benchmark_progress(done, total, text_message):
    msg_queue.put(
        ("progress", done, total, text_message)
    )


def stop_benchmark():
    if running:
        cancel.set()

        status_var.set(
            "Останавливаю… (дождёмся конца текущего замера)"
        )


def poll_queue():
    global running

    if closing:
        return

    try:
        while True:
            msg = msg_queue.get_nowait()

            kind = msg[0]

            if kind == "progress":
                done = msg[1]
                total = msg[2]
                text_message = msg[3]

                progress.configure(
                    value=100 * done / max(total, 1)
                )

                status_var.set(
                    f"{done}/{total}  {text_message}"
                )

            elif kind == "done":
                res = msg[1]
                cancelled = msg[2]

                finish_benchmark(res, cancelled)

            elif kind == "error":
                running = False

                run_btn.configure(state="normal")
                stop_btn.configure(state="disabled")

                status_var.set("Ошибка при выполнении.")

                messagebox.showerror(
                    "Ошибка",
                    msg[1]
                )

    except queue.Empty:
        pass

    if running:
        root.after(100, poll_queue)


def finish_benchmark(res, cancelled):
    global running
    global results

    running = False
    results = res

    run_btn.configure(state="normal")
    stop_btn.configure(state="disabled")

    if not cancelled:
        progress.configure(value=100)

    if cancelled:
        message = "Остановлено пользователем. "
    else:
        message = "Готово. "

    status_var.set(
        message + f"Получено замеров: {len(res)}."
    )

    fill_table()
    set_conclusions()

    kinds = []

    for r in res:
        if r.kind not in kinds:
            kinds.append(r.kind)

    kind_cb.configure(values=kinds)

    if kinds:
        kind_cb.current(0)

    redraw_chart()

    notebook.select(0)


# Отображение результатов

def redraw_chart(event=None):
    ax.clear()

    kind = kind_cb.get()
    label = metric_cb.get()

    attr, factor = METRICS[label]


    plotted = False

    if kind:
        for name in ALGORITHMS:
            xs = []
            ys = []

            for r in series(results, name, kind):
                v = getattr(r, attr)

                if v is None:
                    continue

                xs.append(r.size)
                ys.append(v * factor)

            if xs:
                ax.plot(
                    xs,
                    ys,
                    marker="o",
                    markersize=4,
                    linewidth=1.6,
                    label=name
                )

                plotted = True

    if plotted:
        ax.set_xlabel("Размер массива n")
        ax.set_ylabel(label)
        ax.set_title(f"{label} — {kind}")

        ax.grid(True, which="both", alpha=0.3)
        ax.legend(fontsize=8)

    else:
        ax.set_axis_off()

        ax.text(
            0.5,
            0.5,
            "Нет данных для графика.\n"
            "Нажмите «Запустить эксперимент».",
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=12,
            color="#666666"
        )

    fig.tight_layout()
    canvas.draw_idle()


def fill_table():
    tree.delete(*tree.get_children())

    for index, r in enumerate(results):
        if r.skipped:
            time_text = "—"
            result_text = "Пропущено"
            tag = "skipped"
        else:
            time_text = f"{r.time_s * 1000:.3f}"
            result_text = "✓ Верно" if r.correct else "✕ Ошибка"
            tag = "even" if index % 2 == 0 else "odd"

            if not r.correct:
                tag = "wrong"

        tree.insert(
            "",
            "end",
            values=(
                r.algorithm,
                r.kind,
                fmt_int(r.size),
                time_text,
                fmt_int(r.comparisons),
                fmt_int(r.moves),
                result_text
            ),
            tags=(tag,)
        )


def set_conclusions():
    text.configure(state="normal")
    text.delete("1.0", "end")

    body = build_conclusions(results) or ""

    if results:
        descr = []

        for k, d in DESCRIPTIONS.items():
            descr.append(f"  • {k}: {d}")

        descr = "\n".join(descr)

        text.insert(
            "end",
            params_text +
            "\nТипы данных:\n" +
            descr +
            "\n\n"
        )

    text.insert("end", body)

    text.configure(state="disabled")


# Сохранение

def save_csv():
    if not results:
        messagebox.showinfo(
            "Нет данных",
            "Сначала запустите эксперимент."
        )
        return

    path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV", "*.csv")],
        initialfile="results.csv"
    )

    if path:
        try:
            export_csv(results, path)

            messagebox.showinfo(
                "Готово",
                f"Таблица сохранена:\n{path}"
            )

        except OSError as e:
            messagebox.showerror(
                "Не удалось сохранить",
                str(e)
            )


def save_chart():
    path = filedialog.asksaveasfilename(
        defaultextension=".png",
        filetypes=[("PNG", "*.png")],
        initialfile="chart.png"
    )

    if path:
        try:
            fig.savefig(path, dpi=200)

            messagebox.showinfo(
                "Готово",
                f"График сохранён:\n{path}"
            )

        except OSError as e:
            messagebox.showerror(
                "Не удалось сохранить",
                str(e)
            )


# Анимация сортировки

def anim_size():
    try:
        n = int(anim_n_var.get())

    except ValueError:
        n = 40

    n = max(5, min(150, n))

    anim_n_var.set(str(n))

    return n


def anim_new_array():
    global anim_data

    anim_stop()

    n = anim_size()

    anim_data = generate(
        anim_kind_cb.get(),
        n,
        seed=random.randrange(10 ** 6)
    )

    anim_status.set(
        f"Массив из {n} элементов. Нажмите «Старт»."
    )

    anim_draw(anim_data, (), False)


def anim_start():
    global anim_work
    global anim_gen
    global anim_steps

    anim_stop()

    if len(anim_data) != anim_size():
        anim_new_array()

    anim_work = list(anim_data)

    anim_gen = VISUAL_SORTS[anim_alg_cb.get()](anim_work)

    anim_steps = 0

    anim_step()


def anim_stop():
    global anim_job
    global anim_gen

    if anim_job is not None:
        root.after_cancel(anim_job)
        anim_job = None

    anim_gen = None


def anim_step():
    global anim_job
    global anim_gen
    global anim_steps

    if anim_gen is None or closing:
        return

    try:
        state, active = next(anim_gen)

    except StopIteration:
        anim_job = None
        anim_gen = None

        anim_draw(anim_work, (), True)

        anim_status.set(
            f"Готово: {anim_steps} шагов анимации."
        )

        return

    anim_steps += 1

    anim_status.set(
        f"Шагов: {anim_steps}"
    )

    anim_draw(state, active, False)

    anim_job = root.after(
        max(1, int(anim_speed.get())),
        anim_step
    )


def anim_draw(arr, active, done):
    global anim_last

    anim_last = (arr, active, done)

    c = anim_canvas

    c.delete("all")

    n = len(arr)

    if n == 0:
        return

    w = max(c.winfo_width(), 200)
    h = max(c.winfo_height(), 200)

    bar_w = w / n

    lo = min(arr)
    hi = max(arr)

    for i, v in enumerate(arr):
        if hi == lo:
            frac = 1.0
        else:
            frac = 0.06 + 0.94 * (v - lo) / (hi - lo)

        top = h - frac * (h - 12)

        if done:
            color = "#2e7d32"

        elif i in active:
            color = "#d32f2f"

        else:
            color = "#4a78c2"

        c.create_rectangle(
            i * bar_w + 1,
            top,
            (i + 1) * bar_w - 1,
            h,
            fill=color,
            outline=""
        )


def on_close():
    global closing

    closing = True

    cancel.set()

    anim_stop()

    root.destroy()


def main():
    global root

    root = tk.Tk()

    root.title("Лаборатория сортировок")
    root.geometry("1340x860")
    root.minsize(1100, 720)

    create_interface()

    anim_new_array()

    root.protocol(
        "WM_DELETE_WINDOW",
        on_close
    )

    root.mainloop()


if __name__ == "__main__":
    main()
