from datetime import datetime
import os
import shutil
import sqlite3
import flet as ft

# متغیر سراسری برای مسیر دیتابیس (بعداً در تابع main مقداردهی می‌شود)
DB_FILENAME = "nima_accounting.db"


def get_db_path(page: ft.Page):
  # اگر برنامه روی موبایل (اندروید/آی‌اواس) اجرا شود، مسیر امن را می‌گیرد
  try:
    if page.web:
      return DB_FILENAME
    # بررسی اینکه آیا پلتفرم موبایل است
    storage_path = page.get_persistent_storage_path()
    if storage_path:
      return os.path.join(storage_path, "nima_accounting.db")
  except Exception:
    pass
  return DB_FILENAME


def init_db(db_path):
  conn = sqlite3.connect(db_path)
  c = conn.cursor()
  c.execute(
      """
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """
  )
  c.execute(
      """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            date TEXT,
            debt REAL DEFAULT 0,
            paid REAL DEFAULT 0,
            note TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    """
  )
  conn.commit()
  conn.close()


def get_persian_date():
  return datetime.now().strftime("%Y/%m/%d")


def main(page: ft.Page):
  page.title = "دفتر حساب نیما (نسخه موبایل)"
  page.rtl = True
  page.theme_mode = ft.ThemeMode.LIGHT
  page.vertical_alignment = ft.MainAxisAlignment.START
  page.padding = 10
  page.scroll = ft.ScrollMode.AUTO

  # تعیین مسیر درست دیتابیس برای اندروید یا ویندوز
  db_path = get_db_path(page)
  init_db(db_path)

  customer_input = ft.TextField(
      label="نام مشتری جدید یا موجود",
      expand=True,
      border_radius=8,
      prefix_icon=ft.Icons.PERSON,
  )
  debt_input = ft.TextField(
      label="بدهی/خرید",
      value="0",
      keyboard_type=ft.KeyboardType.NUMBER,
      expand=True,
      border_radius=8,
  )
  paid_input = ft.TextField(
      label="پرداخت/واریز",
      value="0",
      keyboard_type=ft.KeyboardType.NUMBER,
      expand=True,
      border_radius=8,
  )
  date_input = ft.TextField(
      label="تاریخ (شمسی)",
      value=get_persian_date(),
      expand=True,
      border_radius=8,
  )
  note_input = ft.TextField(
      label="یادداشت (اختیاری)", expand=True, border_radius=8
  )

  search_input = ft.TextField(
      label="جستجوی نام مشتری...",
      prefix_icon=ft.Icons.SEARCH,
      border_radius=8,
  )

  summary_text = ft.Text(
      "کل بدهی: 0 | کل پرداخت: 0 | مانده کل: 0",
      weight=ft.FontWeight.BOLD,
      color=ft.Colors.BLUE_900,
  )
  customers_list_view = ft.Column(spacing=10)

  def show_snack(text, color=ft.Colors.GREEN):
    snack = ft.SnackBar(content=ft.Text(text), bgcolor=color)
    page.overlay.append(snack)
    snack.open = True
    page.update()

  def backup_database(e):
    try:
      backup_name = f"nima_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
      backup_path = os.path.join(os.getcwd(), backup_name)
      shutil.copy(db_path, backup_path)
      show_snack(f"پشتیبان با موفقیت ذخیره شد:\n{backup_name}")
    except Exception as ex:
      show_snack(f"خطا در پشتیبان‌گیری: {ex}", ft.Colors.RED)

  def open_customer_details(cid, cname):
    details_list = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)

    conn_t = sqlite3.connect(db_path)
    trans = conn_t.execute(
        "SELECT date, debt, paid, note FROM transactions WHERE customer_id = ?"
        " ORDER BY id DESC",
        (cid,),
    ).fetchall()
    conn_t.close()

    if not trans:
      details_list.controls.append(ft.Text("هیچ تراکنشی ثبت نشده است."))
    else:
      for t in trans:
        t_date, t_debt, t_paid, t_note = t
        details_list.controls.append(
            ft.Card(
                content=ft.Container(
                    padding=10,
                    content=ft.Column([
                        ft.Row(
                            [
                                ft.Text(
                                    f"تاریخ: {t_date}",
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    f"خرید: {t_debt:,.0f} | پرداخت:"
                                    f" {t_paid:,.0f}",
                                    size=12,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        (
                            ft.Text(f"یادداشت: {t_note}", size=12)
                            if t_note
                            else ft.Container()
                        ),
                    ]),
                )
            )
        )

    def close_dlg(e):
      dlg.open = False
      page.update()

    dlg = ft.AlertDialog(
        title=ft.Text(f"ریزحساب: {cname}"),
        content=ft.Container(content=details_list, width=400, height=300),
        actions=[ft.TextButton("بستن", on_click=close_dlg)],
    )

    page.dialog = dlg
    dlg.open = True
    page.update()

  def load_data(search_query=""):
    customers_list_view.controls.clear()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    if search_query:
      c.execute(
          """
                SELECT c.id, c.name, 
                       COALESCE(SUM(t.debt), 0), 
                       COALESCE(SUM(t.paid), 0)
                FROM customers c
                LEFT JOIN transactions t ON c.id = t.customer_id
                WHERE c.name LIKE ?
                GROUP BY c.id, c.name
            """,
          (f"%{search_query}%",),
      )
    else:
      c.execute("""
            SELECT c.id, c.name, 
                   COALESCE(SUM(t.debt), 0), 
                   COALESCE(SUM(t.paid), 0)
            FROM customers c
            LEFT JOIN transactions t ON c.id = t.customer_id
            GROUP BY c.id, c.name
        """)

    rows = c.fetchall()
    total_all_debt = 0
    total_all_paid = 0

    for row in rows:
      c_id, name, total_debt, total_paid = row
      balance = total_debt - total_paid
      total_all_debt += total_debt
      total_all_paid += total_paid

      def delete_customer(e, cid=c_id):
        conn_del = sqlite3.connect(db_path)
        conn_del.execute("DELETE FROM transactions WHERE customer_id = ?", (cid,))
        conn_del.execute("DELETE FROM customers WHERE id = ?", (cid,))
        conn_del.commit()
        conn_del.close()
        load_data()
        show_snack("مشتری و تراکنش‌هایش حذف شدند.", ft.Colors.RED)

      card = ft.Card(
          content=ft.Container(
              padding=15,
              content=ft.Column([
                  ft.Row(
                      [
                          ft.Text(
                              name,
                              weight=ft.FontWeight.BOLD,
                              size=16,
                              color=ft.Colors.INDIGO_900,
                          ),
                          ft.IconButton(
                              icon=ft.Icons.DELETE,
                              icon_color=ft.Colors.RED_400,
                              on_click=delete_customer,
                          ),
                      ],
                      alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                  ),
                  ft.Row(
                      [
                          ft.Text(
                              f"مانده: {balance:,.0f} تومان",
                              weight=ft.FontWeight.BOLD,
                              color=(
                                  ft.Colors.RED
                                  if balance > 0
                                  else ft.Colors.GREEN
                              ),
                          ),
                      ],
                      alignment=ft.MainAxisAlignment.END,
                  ),
                  ft.Divider(),
                  ft.Row(
                      [
                          ft.Text(
                              f"کل بدهی: {total_debt:,.0f} | کل پرداخت:"
                              f" {total_paid:,.0f}",
                              size=12,
                              color=ft.Colors.GREY_700,
                          ),
                          ft.TextButton(
                              "ریزحساب",
                              icon=ft.Icons.LIST_ALT,
                              icon_color=ft.Colors.INDIGO_700,
                              on_click=lambda e, cid=c_id, cname=name: open_customer_details(
                                  cid, cname
                              ),
                          ),
                      ],
                      alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                  ),
              ]),
          )
      )

      customers_list_view.controls.append(card)

    conn.close()
    total_balance = total_all_debt - total_all_paid
    summary_text.value = (
        f"کل بدهی: {total_all_debt:,.0f} | کل پرداخت: {total_all_paid:,.0f} |"
        f" مانده کل: {total_balance:,.0f}"
    )
    page.update()

  def add_transaction(e):
    c_name = customer_input.value.strip()
    if not c_name:
      show_snack("لطفا نام مشتری را وارد کنید!", ft.Colors.RED)
      return

    try:
      debt = float(debt_input.value) if debt_input.value else 0
      paid = float(paid_input.value) if paid_input.value else 0
    except ValueError:
      show_snack("مبلغ باید عدد باشد!", ft.Colors.RED)
      return

    date_val = date_input.value
    note_val = note_input.value.strip()

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("SELECT id FROM customers WHERE name = ?", (c_name,))
    res = c.fetchone()
    if res:
      customer_id = res[0]
    else:
      c.execute("INSERT INTO customers (name) VALUES (?)", (c_name,))
      customer_id = c.lastrowid

    c.execute(
        """
            INSERT INTO transactions (customer_id, date, debt, paid, note)
            VALUES (?, ?, ?, ?, ?)
        """,
        (customer_id, date_val, debt, paid, note_val),
    )

    conn.commit()
    conn.close()

    customer_input.value = ""
    debt_input.value = "0"
    paid_input.value = "0"
    note_input.value = ""
    date_input.value = get_persian_date()

    load_data()
    show_snack("تراکنش با موفقیت ثبت شد!")

  submit_btn = ft.ElevatedButton(
      "ثبت تراکنش",
      icon=ft.Icons.ADD,
      on_click=add_transaction,
      color=ft.Colors.WHITE,
      bgcolor=ft.Colors.BLUE_700,
      expand=True,
  )

  backup_btn = ft.ElevatedButton(
      "پشتیبان‌گیری",
      icon=ft.Icons.SAVE,
      on_click=backup_database,
      color=ft.Colors.WHITE,
      bgcolor=ft.Colors.GREEN_700,
  )

  search_input.on_change = lambda e: load_data(search_input.value)

  page.add(
      ft.Row(
          [
              ft.Text(
                  "دفتر حساب نیما",
                  size=18,
                  weight=ft.FontWeight.BOLD,
                  color=ft.Colors.BLUE_900,
              ),
              backup_btn,
          ],
          alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
      ),
      ft.Divider(),
      customer_input,
      ft.Row([debt_input, paid_input]),
      ft.Row([date_input, note_input]),
      submit_btn,
      ft.Divider(),
      search_input,
      summary_text,
      ft.Divider(),
      customers_list_view,
  )

  load_data()


if __name__ == "__main__":
  ft.app(main)
