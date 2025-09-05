import os
import csv
import datetime
from collections import defaultdict

from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.togglebutton import ToggleButton
from kivy.core.window import Window

from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg
import matplotlib
matplotlib.use("module://kivy.garden.matplotlib.backend_kivy")
import matplotlib.pyplot as plt

from fpdf import FPDF

DATA_CSV = "records.csv"
CATEGORIES = ["Food","Transport","Bills","Groceries","Entertainment","Health","Savings","Other"]

def ensure_csv():
    if not os.path.exists(DATA_CSV):
        with open(DATA_CSV, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["date","type","category","amount","note"])

def read_all():
    ensure_csv()
    with open(DATA_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def append_row(kind, category, amount, note, date=None):
    ensure_csv()
    if date is None:
        date = datetime.date.today().isoformat()
    with open(DATA_CSV, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([date, kind, category, amount, note])

def month_filter(rows, year, month):
    out = []
    for r in rows:
        try:
            d = datetime.datetime.strptime(r["date"], "%Y-%m-%d").date()
            if d.year == year and d.month == month:
                out.append(r)
        except Exception:
            pass
    return out

class HomeTab(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=10, spacing=8, **kwargs)

        row1 = GridLayout(cols=2, size_hint_y=None, height=40, spacing=8)
        row1.add_widget(Label(text="Amount"))
        self.amount = TextInput(hint_text="0.00", multiline=False, input_filter="float")
        row1.add_widget(self.amount)

        row2 = GridLayout(cols=2, size_hint_y=None, height=40, spacing=8)
        row2.add_widget(Label(text="Category"))
        self.category = Spinner(text=CATEGORIES[0], values=CATEGORIES)
        row2.add_widget(self.category)

        self.note = TextInput(hint_text="Note (optional)", size_hint_y=None, height=40, multiline=False)

        row3 = GridLayout(cols=2, size_hint_y=None, height=40, spacing=8)
        self.btn_income = Button(text="Add Income")
        self.btn_expense = Button(text="Add Expense")
        self.btn_income.bind(on_release=lambda *_: self.add(kind="income"))
        self.btn_expense.bind(on_release=lambda *_: self.add(kind="expense"))
        row3.add_widget(self.btn_income)
        row3.add_widget(self.btn_expense)

        self.add_widget(row1); self.add_widget(row2); self.add_widget(self.note); self.add_widget(row3)

        self.list_area = GridLayout(cols=1, size_hint_y=None, spacing=4, padding=(0,8))
        self.list_area.bind(minimum_height=self.list_area.setter("height"))
        sc = ScrollView(); sc.add_widget(self.list_area); self.add_widget(sc)

        self.total_label = Label(text="Total: 0.00", size_hint_y=None, height=30, bold=True)
        self.add_widget(self.total_label)
        self.refresh_today()

    def add(self, kind):
        if not self.amount.text.strip():
            return
        try:
            amt = float(self.amount.text.strip())
        except ValueError:
            return
        cat = self.category.text.strip() or "Other"
        note = self.note.text.strip()
        append_row(kind, cat, amt, note)
        self.amount.text = ""; self.note.text = ""
        self.refresh_today()

    def refresh_today(self):
        self.list_area.clear_widgets()
        rows = read_all()
        today = datetime.date.today().isoformat()
        total_inc = total_exp = 0.0
        for r in rows:
            if r["date"] == today:
                amt = float(r["amount"])
                if r["type"] == "income": total_inc += amt
                else: total_exp += amt
                color = (0,0.6,0,1) if r["type"]=="income" else (0.85,0,0,1)
                self.list_area.add_widget(Label(
                    text=f"{r['date']}  {r['type'].upper():7s}  {r['category']}: {amt:.2f}  {r['note']}",
                    size_hint_y=None, height=28, color=color))
        bal = total_inc - total_exp
        self.total_label.text = f"Today  Income: {total_inc:.2f}  Expense: {total_exp:.2f}  Balance: {bal:.2f}"

class ChartsTab(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=10, spacing=8, **kwargs)
        top = GridLayout(cols=4, size_hint_y=None, height=40, spacing=6)
        today = datetime.date.today()
        self.year_in = TextInput(text=str(today.year), multiline=False)
        self.month_in = TextInput(text=str(today.month), multiline=False)
        refresh_btn = Button(text="Refresh")
        export_btn = Button(text="Export CSV")
        top.add_widget(Label(text="Year")); top.add_widget(self.year_in)
        top.add_widget(Label(text="Month")); top.add_widget(self.month_in)
        self.add_widget(top)
        second = GridLayout(cols=2, size_hint_y=None, height=40, spacing=6)
        second.add_widget(refresh_btn); second.add_widget(export_btn)
        self.add_widget(second)
        refresh_btn.bind(on_release=lambda *_: self.draw())
        export_btn.bind(on_release=lambda *_: self.export_csv())
        self.chart_box = BoxLayout(orientation="vertical", spacing=8)
        self.add_widget(self.chart_box)
        self.draw()

    def draw(self):
        self.chart_box.clear_widgets()
        rows = read_all()
        try:
            y = int(self.year_in.text); m = int(self.month_in.text)
        except ValueError:
            self.chart_box.add_widget(Label(text="Invalid year/month")); return
        rows = month_filter(rows, y, m)
        by_cat = defaultdict(float)
        total_income = total_expense = 0.0
        for r in rows:
            amt = float(r["amount"])
            if r["type"] == "income": total_income += amt
            else: total_expense += amt; by_cat[r["category"]] += amt
        info = Label(text=f"{y}-{m:02d}  Income: {total_income:.2f}  Expense: {total_expense:.2f}  Balance: {total_income-total_expense:.2f}", size_hint_y=None, height=28)
        self.chart_box.add_widget(info)
        if by_cat:
            cats = list(by_cat.keys()); vals = [by_cat[c] for c in cats]
            fig1, ax1 = plt.subplots(); ax1.bar(cats, vals); ax1.set_title("Expenses by Category (Bar)"); ax1.set_ylabel("Amount"); ax1.tick_params(axis='x', labelrotation=30)
            self.chart_box.add_widget(FigureCanvasKivyAgg(fig1))
            fig2, ax2 = plt.subplots(); ax2.pie(vals, labels=cats, autopct="%1.1f%%"); ax2.set_title("Expenses by Category (Pie)")
            self.chart_box.add_widget(FigureCanvasKivyAgg(fig2))
        else:
            self.chart_box.add_widget(Label(text="No expenses for selected month"))

    def export_csv(self):
        rows = read_all()
        try:
            y = int(self.year_in.text); m = int(self.month_in.text)
        except ValueError:
            return
        sel = month_filter(rows, y, m)
        out = f"export_{y}_{m:02d}.csv"
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["date","type","category","amount","note"])
            for r in sel:
                w.writerow([r["date"], r["type"], r["category"], r["amount"], r["note"]])

class ReportsTab(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=10, spacing=8, **kwargs)
        self.add_widget(Label(text="Export Today's PDF Report"))
        btn = Button(text="Export PDF")
        btn.bind(on_release=lambda *_: self.export_today_pdf())
        self.add_widget(btn)
        self.status = Label(text="")
        self.add_widget(self.status)

    def export_today_pdf(self):
        rows = read_all()
        today = datetime.date.today().isoformat()
        todays = [r for r in rows if r["date"] == today]
        pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", size=14)
        pdf.cell(190, 10, "Daily Budget Report", ln=1, align="C")
        pdf.set_font("Arial", size=11)
        total_inc = total_exp = 0.0
        for r in todays:
            amt = float(r["amount"])
            if r["type"] == "income": total_inc += amt
            else: total_exp += amt
            pdf.cell(190, 8, f"{r['date']}  {r['type'].upper():7s}  {r['category']:<12s} {amt:>10.2f}  {r['note']}", ln=1)
        pdf.ln(4)
        pdf.cell(190, 8, f"Total Income: {total_inc:.2f}", ln=1)
        pdf.cell(190, 8, f"Total Expense: {total_exp:.2f}", ln=1)
        pdf.cell(190, 8, f"Balance: {total_inc-total_exp:.2f}", ln=1)
        out = f"report_{today}.pdf"
        pdf.output(out); self.status.text = f"Saved: {out}"

class SettingsTab(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=10, spacing=8, **kwargs)
        self.theme_btn = ToggleButton(text="Toggle Dark Mode", size_hint_y=None, height=44)
        self.theme_btn.bind(on_release=self.toggle)
        self.add_widget(self.theme_btn)
    def toggle(self, *_):
        Window.clearcolor = (0.10,0.10,0.11,1) if Window.clearcolor==(1,1,1,1) else (1,1,1,1)

class Root(TabbedPanel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_default_tab = False
        self.add_widget(HomeTab(text="Home"))
        self.add_widget(ChartsTab(text="Charts"))
        self.add_widget(ReportsTab(text="Reports"))
        self.add_widget(SettingsTab(text="Settings"))

class UltimateBudgetApp(App):
    def build(self):
        ensure_csv()
        return Root()

if __name__ == "__main__":
    UltimateBudgetApp().run()
