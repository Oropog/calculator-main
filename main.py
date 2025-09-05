# calculator_main.py
#!/usr/bin/env python3
from __future__ import annotations
import os
import re
import sys
import subprocess
import importlib.util
from typing import Iterable, Set

# =====================
#  CONFIGURATION
# =====================
ALLOWED_IDS_RAW: Set[str] = {
    "0170209201132347",
    "0170-2092",
    "0113-2347",
    "FE00ABAA00008877",
}

env_ids = {s.strip() for s in os.environ.get("USB_ALLOWED_IDS", "").split(",") if s.strip()}
ALLOWED_IDS_RAW |= env_ids

_norm = lambda s: re.sub(r"[^0-9A-Za-z]", "", s or "").upper()
ALLOWED_IDS_NORM: Set[str] = {_norm(s) for s in ALLOWED_IDS_RAW}

# Глобальная ссылка на функцию возведения в степень,
# загружаемую с флеш-накопителя при его наличии
power_func = None

# =====================
#  DEVICE ENUMERATION
# =====================
def _run(cmd: list[str]) -> str:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return out
    except Exception:
        return ""

def collect_candidate_ids() -> Set[str]:
    candidates: Set[str] = set()

    def add_tokens(tokens: Iterable[str]):
        for t in tokens:
            t = t.strip()
            if not t:
                continue
            candidates.add(t)
            candidates.add(_norm(t))

    plat = sys.platform
    if plat.startswith("win"):
        out = _run(["wmic", "volume", "get", "DriveLetter,SerialNumber,Label"])
        add_tokens(re.findall(r"[A-F0-9]{4}-[A-F0-9]{4}", out, re.IGNORECASE))
        out2 = _run(["wmic", "diskdrive", "get", "SerialNumber,Model,PNPDeviceID"])
        add_tokens(re.findall(r"SerialNumber\s+([\w-]+)", out2, re.IGNORECASE))
        add_tokens(re.findall(r"\b[0-9A-Za-z]{8,}[-_]?[0-9A-Za-z]*\b", out2))

    return candidates

def usb_is_authorized() -> bool:
    cands = collect_candidate_ids()
    if any(token in ALLOWED_IDS_RAW for token in cands):
        return True
    if any(token in ALLOWED_IDS_NORM for token in cands):
        return True
    return False

def power_enabled() -> bool:
    """Проверяет наличие флешки с power_module.py и загружает модуль."""
    global power_func
    # Перебираем потенциальные буквы дисков Windows
    for drive_letter in [d + ":" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]:
        module_path = os.path.join(drive_letter, "power_module.py")
        if os.path.exists(module_path):
            try:
                spec = importlib.util.spec_from_file_location("power_module", module_path)
                mod = importlib.util.module_from_spec(spec)
                assert spec.loader is not None
                spec.loader.exec_module(mod)
                power_func = getattr(mod, "power", None)
                if callable(power_func):
                    return True
            except Exception:
                power_func = None
            break
    return False

# =====================
#  GUI CALCULATOR
# =====================
import tkinter as tk
from tkinter import messagebox

class Calculator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("USB-Locked Calculator")
        self.geometry("340x450")
        self.resizable(False, False)

        self.expr = tk.StringVar()
        entry = tk.Entry(self, textvariable=self.expr, justify="right", font=("Arial", 24), state="readonly")
        entry.pack(fill="x", padx=12, pady=12, ipady=10)

        self.power_on = power_enabled()

        btns = [
            ["7", "8", "9", "/"],
            ["4", "5", "6", "*"],
            ["1", "2", "3", "-"],
            ["0", ".", "C", "+"],
            ["(", ")", "←", "="],
        ]
        if self.power_on:
            btns.append(["^"])

        grid = tk.Frame(self)
        grid.pack(expand=True, fill="both", padx=10, pady=(0,12))

        for r, row in enumerate(btns):
            for c, label in enumerate(row):
                b = tk.Button(grid, text=label, font=("Arial",16), width=4, height=2,
                              command=lambda x=label: self.on_press(x))
                b.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")

        for i in range(4):
            grid.columnconfigure(i, weight=1)
        for i in range(len(btns)):
            grid.rowconfigure(i, weight=1)

    def on_press(self, label: str):
        if label == "C":
            self.expr.set("")
        elif label == "=":
            self.evaluate()
        elif label == "←":
            self.expr.set(self.expr.get()[:-1])
        elif label == "^":
            if self.power_on:
                self.expr.set(self.expr.get() + "^")
            else:
                messagebox.showwarning("Ограничение", "Операция возведения в степень доступна только с подключенной флешкой FE00ABAA00008877")
        else:
            self.expr.set(self.expr.get() + label)

    def evaluate(self):
        try:
            expr = self.expr.get()
            if not expr.strip():
                return
            if not re.fullmatch(r"[0-9+\-*/().\s^]+", expr):
                raise ValueError("Недопустимые символы")
            if "^" in expr:
                if not self.power_on or not callable(power_func):
                    raise ValueError(
                        "Операция возведения в степень доступна только с подключенной флешкой FE00ABAA00008877"
                    )
                expr = re.sub(r"(\d+(?:\.\d+)?)\^(\d+(?:\.\d+)?)", r"power_func(\1, \2)", expr)
                result = eval(expr, {"__builtins__": None, "power_func": power_func})
            else:
                result = eval(expr, {"__builtins__": None}, {})
            self.expr.set(str(result))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Невозможно вычислить: {e}")


def main():
    if not usb_is_authorized():
        want = ", ".join(sorted(ALLOWED_IDS_RAW))
        messagebox.showwarning("Доступ запрещён",
            f"Калькулятор работает только при подключенной разрешённой флешке.\n\nОжидаемые идентификаторы: {want}\nПодключите нужный носитель и запустите программу снова.")
        sys.exit(2)

    app = Calculator()
    app.mainloop()

if __name__ == "__main__":
    main()
