"""NiceGUI dashboard for the Personal Finance Analyzer.

Run with: python gui.py
Local browser: http://127.0.0.1:8080

For secure phone access, keep the app on localhost and use Tailscale Serve;
see README.md. Direct LAN access is available by setting FINTRACK_HOST=0.0.0.0.
"""

from datetime import date
import os
from pathlib import Path

from nicegui import ui

from finance_manager import FinanceManager


# IMPORTANT: the public demo uses only this isolated fictional dataset.
# Never replace these paths with your personal app's JSON files.
DEMO_DATA_DIR = Path(__file__).resolve().parent / "demo_data"
manager = FinanceManager(
    transactions_path=DEMO_DATA_DIR / "transactions.json",
    budget_path=DEMO_DATA_DIR / "budget.json",
)
CURRENT_PAGE = {"name": "Overview"}

# A small amount of CSS gives the dashboard its visual identity. Most layout is
# still made from ordinary NiceGUI components and Tailwind utility classes.
ui.colors(primary="#6658E8", secondary="#16A085", accent="#F59E0B")
ui.page_title("FinTrack | Public Demo")
ui.add_head_html(
    """
    <style>
      body { background: #f5f7fb; color: #182230; }
      .fintrack-sidebar { background: #171a2b; color: #f8fafc; }
      .fintrack-card { border: 1px solid #e8ebf2; border-radius: 18px;
                       box-shadow: 0 6px 24px rgba(21, 29, 54, .045); }
      .fintrack-muted { color: #718096; }
      .fintrack-nav { border-radius: 10px; }
      .fintrack-nav:hover { background: rgba(255,255,255,.09); }
      .fintrack-table { border-radius: 14px; overflow: hidden; }
      .fintrack-card { box-sizing: border-box; }
      .q-card { box-shadow: none; }
      @media (max-width: 640px) {
        .fintrack-sidebar { width: 68px !important; flex: 0 0 68px !important; padding: 10px 6px !important; gap: 14px !important; }
        .fintrack-brand-text, .fintrack-workspace-label, .fintrack-footer-note { display: none !important; }
        .fintrack-sidebar .fintrack-nav { width: 52px; min-width: 52px; min-height: 52px; margin: 0 auto; padding: 0 !important; }
        .fintrack-sidebar .fintrack-nav .q-btn__content > span.block { display: none !important; }
        .fintrack-sidebar .fintrack-nav .q-icon { margin: 0 !important; }
        .fintrack-main-content { padding: 12px !important; }
        .fintrack-page-title { font-size: 1.5rem !important; line-height: 1.9rem !important; }
        .fintrack-card { min-width: 0 !important; padding: 12px !important; }
        .fintrack-form-grid { grid-template-columns: minmax(0, 1fr) !important; }
      }
    </style>
    """
)


def money(value: float) -> str:
    return f"₹{value:,.2f}"


def current_month() -> str:
    return date.today().strftime("%Y-%m")


def transaction_rows(query: str = "") -> list[dict]:
    filtered = manager.search_transactions(query)
    rows = []
    for transaction in filtered:
        # The index is used internally so duplicate descriptions can still be
        # selected/deleted safely. It is intentionally not a visible column.
        index = next(i for i, item in enumerate(manager.transaction_list) if item is transaction)
        rows.append({
            "_index": index,
            "description": transaction.description,
            "type": transaction.transaction_type,
            "category": transaction.category,
            "amount": money(transaction.amount),
            "date": transaction.transaction_date.isoformat(),
        })
    return rows


def transaction_columns() -> list[dict]:
    return [
        {"name": "description", "label": "Description", "field": "description", "align": "left"},
        {"name": "type", "label": "Type", "field": "type", "align": "left"},
        {"name": "category", "label": "Category", "field": "category", "align": "left"},
        {"name": "amount", "label": "Amount", "field": "amount", "align": "right"},
        {"name": "date", "label": "Date", "field": "date", "align": "left"},
    ]


def metric_card(title: str, value: str, icon: str, detail: str, icon_color: str) -> None:
    with ui.card().classes("fintrack-card flex-1 min-w-[190px] p-5"):
        with ui.row().classes("w-full items-center justify-between no-wrap"):
            with ui.column().classes("gap-1"):
                ui.label(title).classes("text-sm fintrack-muted")
                ui.label(value).classes("text-2xl font-bold text-slate-900")
                ui.label(detail).classes("text-xs fintrack-muted")
            with ui.element("div").classes(f"rounded-xl p-3 {icon_color}"):
                ui.icon(icon).classes("text-xl")


def show_page(page_name: str) -> None:
    """Rebuild the central content area for the selected navigation page."""
    CURRENT_PAGE["name"] = page_name
    content.clear()

    with content:
        with ui.card().classes("w-full border-l-4 border-violet-500 bg-violet-50 p-3"):
            ui.label("PUBLIC DEMO — fictional sample data only").classes("font-semibold text-violet-950")
            ui.label("This is a shared demo workspace. Do not enter real financial or personal information; changes may be visible to other visitors and may reset when the demo is redeployed.").classes("text-sm text-violet-900")
        with ui.row().classes("w-full items-start justify-between gap-4"):
            with ui.column().classes("gap-1"):
                ui.label(page_name).classes("text-3xl font-bold text-slate-900 fintrack-page-title")
                descriptions = {
                    "Overview": "A clear picture of where your money is going.",
                    "Transactions": "Add, find, review, and remove transactions.",
                    "Budgets": "Set a monthly spending limit and track your progress.",
                }
                ui.label(descriptions[page_name]).classes("fintrack-muted")
            with ui.row().classes("items-center gap-2"):
                ui.label(date.today().strftime("%d %b %Y")).classes("text-sm fintrack-muted")
                ui.button(icon="refresh", on_click=lambda: show_page(CURRENT_PAGE["name"])) \
                    .props("flat round color=grey-8")

        if manager.load_warning:
            with ui.card().classes("w-full border-l-4 border-amber-500 bg-amber-50"):
                ui.label(manager.load_warning).classes("text-amber-900 text-sm")
        if manager.budget_warning and page_name == "Budgets":
            with ui.card().classes("w-full border-l-4 border-amber-500 bg-amber-50"):
                ui.label(manager.budget_warning).classes("text-amber-900 text-sm")

        if page_name == "Overview":
            render_overview()
        elif page_name == "Transactions":
            render_transactions()
        else:
            render_budgets()


def render_overview() -> None:
    summary = manager.financial_summary()
    this_month = current_month()
    this_month_expenses = manager.expenses_for_month(this_month)
    this_month_budget = manager.budgets.get(this_month)
    if this_month_budget:
        budget_detail = f"{money(this_month_expenses)} spent of {money(this_month_budget)} this month"
    else:
        budget_detail = "No budget set for this month"

    with ui.row().classes("w-full gap-4 flex-wrap"):
        metric_card("Total income", money(summary["income"]), "south_west", "All recorded income", "bg-emerald-100 text-emerald-700")
        metric_card("Total expenses", money(summary["expense"]), "north_east", "All recorded expenses", "bg-rose-100 text-rose-700")
        metric_card("Net balance", money(summary["balance"]), "account_balance_wallet", "Income minus expenses", "bg-violet-100 text-violet-700")
        metric_card("This month", money(this_month_expenses), "calendar_month", budget_detail, "bg-amber-100 text-amber-700")

    with ui.row().classes("w-full items-stretch gap-4 flex-wrap"):
        with ui.card().classes("fintrack-card flex-1 min-w-[320px] p-5"):
            ui.label("Expenses by category").classes("text-lg font-semibold")
            ui.label("See which categories account for your spending.").classes("text-sm fintrack-muted")
            categories = manager.category_expenses()
            if categories:
                ui.echart({
                    "tooltip": {"trigger": "item", "formatter": "{b}: ₹{c} ({d}%)"},
                    "legend": {"bottom": 0, "left": "center"},
                    "series": [{
                        "name": "Expenses",
                        "type": "pie",
                        "radius": ["42%", "70%"],
                        "avoidLabelOverlap": True,
                        "itemStyle": {"borderRadius": 8, "borderColor": "#ffffff", "borderWidth": 3},
                        "label": {"show": False},
                        "emphasis": {"label": {"show": True, "fontSize": 14, "fontWeight": "bold"}},
                        "data": [{"name": key, "value": round(value, 2)} for key, value in categories.items()],
                    }],
                }).classes("w-full h-72")
            else:
                with ui.column().classes("w-full items-center justify-center py-12 gap-2"):
                    ui.icon("pie_chart_outline").classes("text-4xl text-slate-300")
                    ui.label("No expense data yet").classes("font-medium text-slate-600")
                    ui.label("Add an expense to see your category breakdown.").classes("text-sm fintrack-muted")

        with ui.card().classes("fintrack-card flex-1 min-w-[320px] p-5"):
            ui.label("Quick actions").classes("text-lg font-semibold")
            ui.label("Jump straight to a common task.").classes("text-sm fintrack-muted mb-3")
            ui.button("Add a transaction", icon="add", on_click=lambda: show_page("Transactions")) \
                .props("unelevated color=primary") .classes("w-full")
            ui.button("Manage monthly budgets", icon="savings", on_click=lambda: show_page("Budgets")) \
                .props("outline color=primary") .classes("w-full")
            highest = manager.show_highest_spending()
            ui.separator().classes("my-2")
            ui.label("Largest single expense").classes("text-sm fintrack-muted")
            if highest:
                ui.label(highest.description).classes("text-base font-semibold")
                ui.label(f"{money(highest.amount)} · {highest.category}").classes("text-sm text-rose-700")
            else:
                ui.label("No expenses recorded yet.").classes("text-sm fintrack-muted")

    with ui.card().classes("fintrack-card w-full p-5"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Recent transactions").classes("text-lg font-semibold")
            ui.button("View all", icon="arrow_forward", on_click=lambda: show_page("Transactions")) \
                .props("flat color=primary")
        recent = list(reversed(manager.transaction_list[-5:]))
        if recent:
            rows = []
            all_items = manager.transaction_list
            for transaction in recent:
                index = next(i for i, item in enumerate(all_items) if item is transaction)
                rows.append({
                    "_index": index,
                    "description": transaction.description,
                    "type": transaction.transaction_type,
                    "category": transaction.category,
                    "amount": money(transaction.amount),
                    "date": transaction.transaction_date.isoformat(),
                })
            ui.table(columns=transaction_columns(), rows=rows, row_key="_index", pagination=5) \
                .classes("w-full fintrack-table")
        else:
            ui.label("Your transactions will appear here after you add the first one.").classes("fintrack-muted py-5")


def render_transactions() -> None:
    with ui.card().classes("fintrack-card w-full p-5"):
        ui.label("Add transaction").classes("text-lg font-semibold")
        ui.label("Try adding fictional transactions. Demo changes are shared with visitors and may reset on redeploy.").classes("text-sm fintrack-muted mb-2")
        with ui.grid(columns=2).classes("w-full gap-4 fintrack-form-grid"):
            description = ui.input("Description", placeholder="e.g. Groceries").classes("w-full")
            amount = ui.number("Amount (₹)", value=None, min=0.01, format="%.2f").classes("w-full")
            transaction_type = ui.select(["Expense", "Income"], value="Expense", label="Transaction type").classes("w-full")
            category = ui.input("Category", placeholder="e.g. Food, Salary").classes("w-full")
            transaction_date = ui.input("Date", value=date.today().isoformat(), placeholder="YYYY-MM-DD") \
                .props("hint='Use YYYY-MM-DD' persistent-hint").classes("w-full")

        def add_transaction() -> None:
            try:
                manager.add_transaction(
                    description.value or "",
                    amount.value,
                    transaction_type.value or "Expense",
                    category.value or "",
                    transaction_date.value or date.today().isoformat(),
                )
            except (ValueError, OSError) as error:
                ui.notify(str(error), type="negative")
                return
            ui.notify("Transaction added and saved.", type="positive")
            show_page("Transactions")

        ui.button("Add transaction", icon="add", on_click=add_transaction) \
            .props("unelevated color=primary")

    with ui.card().classes("fintrack-card w-full p-5"):
        with ui.row().classes("w-full items-center justify-between flex-wrap"):
            with ui.column().classes("gap-1"):
                ui.label("Transaction history").classes("text-lg font-semibold")
                ui.label(f"{len(manager.transaction_list)} transaction(s) saved").classes("text-sm fintrack-muted")
            search_box = ui.input(placeholder="Search description, category, or type...").props("clearable rounded outlined") \
                .classes("w-full sm:w-80")

        table = ui.table(columns=transaction_columns(), rows=transaction_rows(), row_key="_index", pagination=8) \
            .classes("w-full fintrack-table")

        def update_search() -> None:
            table.rows = transaction_rows(search_box.value or "")
            table.update()

        search_box.on("update:model-value", lambda _: update_search())

        with ui.row().classes("w-full items-end gap-3 mt-4"):
            options = {
                index: f"{item.description} · {item.transaction_type} · {item.transaction_date.isoformat()} · {money(item.amount)}"
                for index, item in enumerate(manager.transaction_list)
            }
            delete_choice = ui.select(options, label="Select a transaction to delete") \
                .classes("flex-1 min-w-[240px]")

            def delete_selected() -> None:
                if delete_choice.value is None:
                    ui.notify("Choose a transaction first.", type="warning")
                    return
                try:
                    removed = manager.delete_transaction(int(delete_choice.value))
                except (ValueError, OSError) as error:
                    ui.notify(str(error), type="negative")
                    return
                ui.notify(f"Deleted: {removed.description}", type="positive")
                show_page("Transactions")

            ui.button("Delete selected", icon="delete", on_click=delete_selected) \
                .props("outline color=negative")


def render_budgets() -> None:
    month_now = current_month()
    this_month_expense = manager.expenses_for_month(month_now)
    this_month_budget = manager.budgets.get(month_now)

    with ui.row().classes("w-full gap-4 flex-wrap"):
        metric_card("Current month", month_now, "calendar_month", "Budget period", "bg-violet-100 text-violet-700")
        metric_card("Spent this month", money(this_month_expense), "shopping_bag", "Expenses dated this month", "bg-rose-100 text-rose-700")
        remaining = (this_month_budget - this_month_expense) if this_month_budget is not None else None
        metric_card("Budget remaining", money(remaining) if remaining is not None else "Not set", "savings", "For the current month", "bg-emerald-100 text-emerald-700")

    with ui.card().classes("fintrack-card w-full p-5"):
        ui.label("Set monthly budget").classes("text-lg font-semibold")
        ui.label("Use YYYY-MM for the month. Saving an existing month updates its budget.").classes("text-sm fintrack-muted mb-3")
        with ui.row().classes("w-full items-end gap-4 flex-wrap"):
            month_input = ui.input("Month", value=month_now, placeholder="YYYY-MM").classes("flex-1 min-w-[180px]")
            budget_input = ui.number("Budget amount (₹)", value=None, min=0.01, format="%.2f") \
                .classes("flex-1 min-w-[180px]")

            def save_budget() -> None:
                try:
                    replaced = manager.set_monthly_budget(month_input.value or "", budget_input.value)
                except (ValueError, OSError) as error:
                    ui.notify(str(error), type="negative")
                    return
                message = "Monthly budget updated." if replaced else "Monthly budget saved."
                ui.notify(message, type="positive")
                show_page("Budgets")

            ui.button("Save budget", icon="save", on_click=save_budget) \
                .props("unelevated color=primary")

    with ui.card().classes("fintrack-card w-full p-5"):
        ui.label("Monthly budgets").classes("text-lg font-semibold")
        budgets = manager.show_monthly_budget()
        if not budgets:
            ui.label("No budgets yet. Set your first monthly budget above.").classes("fintrack-muted py-4")
        else:
            rows = []
            for month, budget_amount in budgets.items():
                spent = manager.expenses_for_month(month)
                remaining_amount = budget_amount - spent
                rows.append({
                    "month": month,
                    "budget": money(budget_amount),
                    "spent": money(spent),
                    "remaining": money(remaining_amount),
                    "status": "Over budget" if remaining_amount < 0 else "Within budget",
                })
            ui.table(
                columns=[
                    {"name": "month", "label": "Month", "field": "month", "align": "left"},
                    {"name": "budget", "label": "Budget", "field": "budget", "align": "right"},
                    {"name": "spent", "label": "Spent", "field": "spent", "align": "right"},
                    {"name": "remaining", "label": "Remaining", "field": "remaining", "align": "right"},
                    {"name": "status", "label": "Status", "field": "status", "align": "left"},
                ],
                rows=rows,
                row_key="month",
                pagination=8,
            ).classes("w-full fintrack-table")


# Main application shell: fixed sidebar + a central page that is refreshed on navigation.
with ui.row().classes("w-full min-h-screen no-wrap gap-0"):
    with ui.column().classes("fintrack-sidebar w-60 min-h-screen p-5 gap-6 shrink-0"):
        with ui.row().classes("items-center gap-3 no-wrap"):
            with ui.element("div").classes("rounded-xl bg-violet-500 p-2"):
                ui.icon("account_balance_wallet").classes("text-2xl text-white")
            with ui.column().classes("gap-0"):
                ui.label("FinTrack").classes("text-xl font-bold text-white")
                ui.label("Personal finance").classes("text-xs text-slate-300 fintrack-brand-text")
        ui.separator().classes("bg-slate-600")
        ui.label("WORKSPACE").classes("text-xs font-semibold tracking-widest text-slate-400 fintrack-workspace-label")
        for page_name, icon_name in [
            ("Overview", "dashboard"),
            ("Transactions", "receipt_long"),
            ("Budgets", "savings"),
        ]:
            ui.button(
                page_name,
                icon=icon_name,
                on_click=lambda name=page_name: show_page(name),
            ).props("flat no-caps align=left").classes("w-full text-white fintrack-nav justify-start")
        ui.space()
        ui.separator().classes("bg-slate-600")
        ui.label("PUBLIC DEMO · Fictional data only · Shared demo workspace").classes("text-xs text-slate-300 fintrack-footer-note")

    with ui.column().classes("fintrack-main-content flex-1 min-w-0 p-5 md:p-9 gap-5"):
        content = ui.column().classes("w-full max-w-7xl mx-auto gap-6")

show_page("Overview")

def server_options() -> dict:
    """Read server settings from environment variables.

    Defaults to localhost so the finance dashboard is not exposed to other
    devices unless the user explicitly opts into LAN access. For direct HTTPS,
    set BOTH FINTRACK_SSL_CERTFILE and FINTRACK_SSL_KEYFILE to valid certificate
    and private-key paths. Tailscale Serve can provide trusted HTTPS without
    configuring certificate files in this app.
    """
    default_host = "0.0.0.0" if os.getenv("PORT") else "127.0.0.1"
    host = os.getenv("FINTRACK_HOST", default_host).strip() or default_host
    port_text = os.getenv("FINTRACK_PORT", os.getenv("PORT", "8080")).strip() or "8080"
    try:
        port = int(port_text)
    except ValueError as error:
        raise RuntimeError("FINTRACK_PORT must be an integer, for example 8080.") from error
    if not 1 <= port <= 65535:
        raise RuntimeError("FINTRACK_PORT must be between 1 and 65535.")

    certfile = os.getenv("FINTRACK_SSL_CERTFILE", "").strip()
    keyfile = os.getenv("FINTRACK_SSL_KEYFILE", "").strip()
    if bool(certfile) != bool(keyfile):
        raise RuntimeError(
            "For direct HTTPS, set both FINTRACK_SSL_CERTFILE and "
            "FINTRACK_SSL_KEYFILE. For a simpler private HTTPS setup, see "
            "the Tailscale Serve instructions in README.md."
        )

    options = {
        "host": host,
        "port": port,
        "title": "FinTrack | Public Demo",
        "reload": False,
    }
    if certfile and keyfile:
        if not Path(certfile).is_file():
            raise RuntimeError(f"SSL certificate file was not found: {certfile}")
        if not Path(keyfile).is_file():
            raise RuntimeError(f"SSL private key file was not found: {keyfile}")
        options["ssl_certfile"] = certfile
        options["ssl_keyfile"] = keyfile
    return options


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(**server_options())
