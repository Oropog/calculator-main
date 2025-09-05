import re
from tkinter import messagebox

def evaluate(self):
    try:
        expr = self.expr.get()
        if not expr.strip():
            return
        if not re.fullmatch(r"[0-9+\-*/().\s^]+", expr):
            raise ValueError("Недопустимые символы")
        # заменяем ^ на ** перед вычислением
        result = eval(expr.replace('^', '**'), {"__builtins__": None}, {})
        self.expr.set(str(result))
    except Exception as e:
        messagebox.showerror("Ошибка", f"Невозможно вычислить: {e}")

def power_enabled():
    return True