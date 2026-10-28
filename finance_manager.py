"""Finance logic for FinTrack.

This module contains no GUI or terminal input/output. It can be used by NiceGUI,
a command-line interface, automated tests, or another interface in the future.
"""

from __future__ import annotations

from datetime import date, datetime
import json
import math
from pathlib import Path
from typing import Any


class Transaction:
    """One income or expense transaction."""

    def __init__(
        self,
        description: str,
        amount: float,
        transaction_type: str,
        category: str,
        transaction_date: date,
    ) -> None:
        self.description = description
        self.amount = float(amount)
        self.transaction_type = transaction_type
        self.category = category
        self.transaction_date = transaction_date

    def __str__(self) -> str:
        return (
            f"{self.description} | {self.amount:.2f} | "
            f"{self.transaction_type} | {self.category} | {self.transaction_date}"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert this object into JSON-compatible values."""
        return {
            "description": self.description,
            "amount": self.amount,
            "transaction_type": self.transaction_type,
            "category": self.category,
            "transaction_date": self.transaction_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Transaction":
        """Recreate a transaction from the existing JSON file format."""
        return cls(
            description=str(data["description"]),
            amount=float(data["amount"]),
            transaction_type=str(data["transaction_type"]),
            category=str(data["category"]),
            transaction_date=date.fromisoformat(str(data["transaction_date"])),
        )


class FinanceManager:
    """Manage transactions and monthly budgets stored in JSON files."""

    def __init__(
        self,
        transactions_path: str | Path | None = None,
        budget_path: str | Path | None = None,
    ) -> None:
        project_folder = Path(__file__).resolve().parent
        self.transactions_path = Path(transactions_path) if transactions_path else project_folder / "transactions.json"
        self.budget_path = Path(budget_path) if budget_path else project_folder / "budget.json"

        self.transaction_list: list[Transaction] = []
        self.budgets: dict[str, float] = {}
        self.load_warning: str | None = None
        self.budget_warning: str | None = None
        self._transactions_write_blocked = False
        self._budgets_write_blocked = False

        self.load_transactions()
        self.load_budgets()
        self.recalculate_totals()

    def save_transactions(self) -> None:
        """Save transactions atomically to avoid leaving a half-written file."""
        if self._transactions_write_blocked:
            raise OSError(
                "Saving is paused because transactions.json has invalid data. Back up and repair the file first."
            )
        self.transactions_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.transactions_path.with_suffix(self.transactions_path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps([item.to_dict() for item in self.transaction_list], indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(self.transactions_path)

    def load_transactions(self) -> None:
        """Load valid transaction records without silently overwriting corrupt data."""
        if not self.transactions_path.exists():
            # Start empty instead of inserting invented income/expense examples.
            self.transaction_list = []
            return

        try:
            raw_data = json.loads(self.transactions_path.read_text(encoding="utf-8"))
            if not isinstance(raw_data, list):
                self.load_warning = "transactions.json must contain a JSON list. The file was not overwritten."
                self._transactions_write_blocked = True
                self.transaction_list = []
                return

            loaded: list[Transaction] = []
            skipped = 0
            for item in raw_data:
                try:
                    if not isinstance(item, dict):
                        raise ValueError("Transaction record must be an object")
                    transaction = Transaction.from_dict(item)
                    if (
                        not transaction.description.strip()
                        or not transaction.category.strip()
                        or transaction.transaction_type not in {"Income", "Expense"}
                        or not math.isfinite(transaction.amount)
                        or transaction.amount <= 0
                    ):
                        raise ValueError("Transaction values are invalid")
                    loaded.append(transaction)
                except (KeyError, TypeError, ValueError, OverflowError):
                    skipped += 1

            self.transaction_list = loaded
            if skipped:
                self._transactions_write_blocked = True
                self.load_warning = (
                    f"Skipped {skipped} invalid transaction record(s). "
                    "Check transactions.json if you need to recover them."
                )
        except (json.JSONDecodeError, OSError) as error:
            self._transactions_write_blocked = True
            self.load_warning = (
                "Could not read transactions.json. The file was left untouched to protect your data. "
                f"Details: {error}"
            )
            self.transaction_list = []

    def load_budgets(self) -> None:
        """Load monthly budgets from the JSON object in budget.json."""
        if not self.budget_path.exists():
            self.budgets = {}
            return

        try:
            raw_data = json.loads(self.budget_path.read_text(encoding="utf-8"))
            if not isinstance(raw_data, dict):
                self.budget_warning = "budget.json must contain a JSON object. The file was not overwritten."
                self._budgets_write_blocked = True
                self.budgets = {}
                return

            valid_budgets: dict[str, float] = {}
            for month, amount in raw_data.items():
                try:
                    self._validate_month(month)
                    value = float(amount)
                    if not math.isfinite(value) or value <= 0:
                        raise ValueError
                    valid_budgets[month] = value
                except (TypeError, ValueError, OverflowError):
                    self._budgets_write_blocked = True
                    self.budget_warning = "Some invalid monthly budget entries were ignored."
            self.budgets = valid_budgets
        except (json.JSONDecodeError, OSError) as error:
            self._budgets_write_blocked = True
            self.budget_warning = (
                "Could not read budget.json. The file was left untouched to protect your data. "
                f"Details: {error}"
            )
            self.budgets = {}

    def save_budgets(self) -> None:
        if self._budgets_write_blocked:
            raise OSError(
                "Saving is paused because budget.json has invalid data. Back up and repair the file first."
            )
        self.budget_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.budget_path.with_suffix(self.budget_path.suffix + ".tmp")
        temporary_path.write_text(json.dumps(self.budgets, indent=2), encoding="utf-8")
        temporary_path.replace(self.budget_path)

    @staticmethod
    def _validate_month(year_month: str) -> str:
        month = str(year_month).strip()
        parsed = datetime.strptime(month, "%Y-%m")
        if parsed.strftime("%Y-%m") != month:
            raise ValueError("Month must use YYYY-MM format, for example 2026-10.")
        return month

    def add_transaction(
        self,
        description: str,
        amount: float | str,
        transaction_type: str,
        category: str,
        transaction_date: date | str | None = None,
    ) -> Transaction:
        """Validate and save a transaction supplied by a GUI or other caller."""
        clean_description = str(description).strip()
        clean_category = str(category).strip().capitalize()
        clean_type = str(transaction_type).strip().capitalize()

        if not clean_description:
            raise ValueError("Description cannot be empty.")
        if not clean_category:
            raise ValueError("Category cannot be empty.")
        if clean_type not in {"Income", "Expense"}:
            raise ValueError("Transaction type must be Income or Expense.")

        try:
            clean_amount = float(amount)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("Enter a valid amount.") from error
        if not math.isfinite(clean_amount) or clean_amount <= 0:
            raise ValueError("Amount must be a finite number greater than zero.")

        if transaction_date is None or transaction_date == "":
            clean_date = date.today()
        elif isinstance(transaction_date, date):
            clean_date = transaction_date
        else:
            try:
                clean_date = date.fromisoformat(str(transaction_date).strip())
            except ValueError as error:
                raise ValueError("Date must use YYYY-MM-DD format.") from error

        transaction = Transaction(
            clean_description, clean_amount, clean_type, clean_category, clean_date
        )
        self.transaction_list.append(transaction)
        try:
            self.save_transactions()
        except OSError:
            self.transaction_list.pop()
            raise
        self.recalculate_totals()
        return transaction

    def delete_transaction(self, index: int) -> Transaction:
        """Delete a transaction by its current list index and return it."""
        if not isinstance(index, int) or index < 0 or index >= len(self.transaction_list):
            raise ValueError("Select a valid transaction to delete.")

        removed = self.transaction_list.pop(index)
        try:
            self.save_transactions()
        except OSError:
            self.transaction_list.insert(index, removed)
            self.recalculate_totals()
            raise
        self.recalculate_totals()
        return removed

    def search_transactions(self, query: str) -> list[Transaction]:
        """Case-insensitive partial search across description and category."""
        clean_query = str(query).strip().casefold()
        if not clean_query:
            return list(self.transaction_list)
        return [
            item for item in self.transaction_list
            if clean_query in item.description.casefold()
            or clean_query in item.category.casefold()
            or clean_query in item.transaction_type.casefold()
        ]

    def recalculate_totals(self) -> dict[str, float]:
        """Recalculate totals from the source of truth: the transaction list."""
        self.total_income = sum(
            item.amount for item in self.transaction_list if item.transaction_type == "Income"
        )
        self.total_expense = sum(
            item.amount for item in self.transaction_list if item.transaction_type == "Expense"
        )
        self.balance = self.total_income - self.total_expense
        return self.financial_summary()

    def calc_total_income(self) -> float:
        self.total_income = sum(
            item.amount for item in self.transaction_list if item.transaction_type == "Income"
        )
        return self.total_income

    def calc_total_expense(self) -> float:
        self.total_expense = sum(
            item.amount for item in self.transaction_list if item.transaction_type == "Expense"
        )
        return self.total_expense

    def calc_net_balance(self) -> float:
        self.balance = self.calc_total_income() - self.calc_total_expense()
        return self.balance

    def financial_summary(self) -> dict[str, float]:
        income = getattr(self, "total_income", None)
        expense = getattr(self, "total_expense", None)
        if income is None or expense is None:
            income = self.calc_total_income()
            expense = self.calc_total_expense()
        self.balance = income - expense
        return {
            "income": float(income),
            "expense": float(expense),
            "balance": float(self.balance),
        }

    def category_expenses(self) -> dict[str, float]:
        """Return expense totals grouped by category."""
        totals: dict[str, float] = {}
        for transaction in self.transaction_list:
            if transaction.transaction_type == "Expense":
                totals[transaction.category] = totals.get(transaction.category, 0.0) + transaction.amount
        return dict(sorted(totals.items(), key=lambda pair: pair[1], reverse=True))

    def show_highest_spending(self) -> Transaction | None:
        """Return the largest single expense, or None if there are no expenses."""
        expenses = [item for item in self.transaction_list if item.transaction_type == "Expense"]
        return max(expenses, key=lambda item: item.amount, default=None)

    def expenses_for_month(self, year_month: str) -> float:
        month = self._validate_month(year_month)
        return sum(
            item.amount
            for item in self.transaction_list
            if item.transaction_type == "Expense"
            and item.transaction_date.strftime("%Y-%m") == month
        )

    def set_monthly_budget(self, year_month: str, amount: float | str) -> bool:
        """Set a budget. Return True if an existing budget was replaced."""
        month = self._validate_month(year_month)
        try:
            value = float(amount)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("Enter a valid budget amount.") from error
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Budget must be a finite amount greater than zero.")

        replaced = month in self.budgets
        previous = self.budgets.get(month)
        self.budgets[month] = value
        try:
            self.save_budgets()
        except OSError:
            if previous is None:
                self.budgets.pop(month, None)
            else:
                self.budgets[month] = previous
            raise
        return replaced

    def show_monthly_budget(self) -> dict[str, float]:
        """Return a copy of all saved monthly budgets."""
        return dict(sorted(self.budgets.items()))
