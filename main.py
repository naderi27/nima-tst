import os
import sqlite3
from datetime import datetime
import flet as ft

# تنظیم مسیر امن و استاندارد برای ذخیره دیتابیس در اندروید، ویندوز و لینوکس
data_dir = os.environ.get("FLET_APP_STORAGE_DATA", os.path.expanduser("~"))
os.makedirs(data_dir, exist_ok=True)
DB_NAME = os.path.join(data_dir, "my_accounting_mobile.db")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            date TEXT,
            debt REAL DEFAULT 0,
            paid REAL DEFAULT 0,
            FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

def get_shamsi_date():
    g_y, g_m, g_d = datetime.now().year, datetime.now().month, datetime.now().day
    g_days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if (g_y % 4 == 0 and g_y % 100 != 0) or (g_y % 400 == 0):
        g_days_in_month[1] = 29
    gy, gm, gd = g_y - 1600, g_m - 1, g_d - 1
    g_day_no = 365 * gy + gy // 4 - gy // 100 + gy // 400 + sum(g_days_in_month[:gm]) + gd
    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053
    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461
    if j_day_no >= 365:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365
    if j_day_no < 186:
        jm, jd = 1 + j_day_no // 31, 1 + (j_day_no % 31)
    else:
        jm, jd = 7 + (j_day_no - 186) // 30, 1 + ((j_day_no - 186) % 30)
    return f"{jy}/{jm:02d}/{jd:02d}"

def main(page: ft.Page):
    page.title = "دفتر حساب نیما"
    page.rtl = True
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.padding = 15
    page.scroll = ft.ScrollMode.AUTO

    try:
        init_db()
    except Exception as err:
        page.add(ft.Text(f"خطا در پایگاه داده: {err}", color="red"))
        page.update()
        return

    name_field = ft.TextField(label="نام مشتری جدید یا موجود", text_align=ft.TextAlign.RIGHT, expand=True)
    date_field = ft.TextField(label="تاریخ (شمسی)", value=get_shamsi_date(), text_align=ft.TextAlign.CENTER, width=130)
    debt_field = ft.TextField(label="بدهی/خرید", value="0", text_align=ft.TextAlign.RIGHT, width=120)
    paid_field = ft.TextField(label="پرداخت/واریز", value="0", text_align=ft.TextAlign.RIGHT, width=120)
    
    search_field = ft.TextField(
        label="جستجوی نام مشتری...",
        text_align=ft.TextAlign.RIGHT,
        prefix_icon=getattr(ft.icons, "SEARCH", None)
    )
    
    customers_list_view = ft.Column()
    totals_text = ft.Text("", weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_900)

    detail_dialog_content = ft.Column(scroll=ft.ScrollMode.AUTO, height=350)
    
    def close_dialog(e):
        detail_dialog.open = False
        page.update()

    detail_dialog = ft.AlertDialog(
        title=ft.Text("ریز تراکنش‌ها", weight=ft.FontWeight.BOLD),
        content=detail_dialog_content,
        actions=[ft.TextButton("بستن", on_click=close_dialog)]
    )
    page.overlay.append(detail_dialog)

    def show_details(cid, cname):
        detail_dialog.title = ft.Text(f"ریز حساب: {cname}", weight=ft.FontWeight.BOLD, color=ft.colors.INDIGO)
        detail_dialog_content.controls.clear()
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, date, debt, paid FROM transactions WHERE customer_id = ? ORDER BY id DESC", (cid,))
        txs = c.fetchall()
        conn.close()

        if not txs:
            detail_dialog_content.controls.append(ft.Text("هیچ تراکنشی ثبت نشده است."))
        else:
            for tid, tdate, tdebt, tpaid in txs:
                detail_dialog_content.controls.append(
                    ft.Container(
                        padding=8,
                        margin=ft.margin.only(bottom=5),
                        bgcolor=ft.colors.GREY_100,
                        border_radius=8,
                        content=ft.Row([
                            ft.Column([
                                ft.Text(f"تاریخ: {tdate}", size=12),
                                ft.Text(f"خرید: {tdebt:,.0f} | واریز: {tpaid:,.0f}", weight=ft.FontWeight.BOLD),
                            ]),
                            ft.IconButton(
                                icon=ft.icons.DELETE_OUTLINE,
                                icon_color="red",
                                icon_size=18,
                                tooltip="حذف این تراکنش",
                                on_click=lambda e, t_id=tid, cust_id=cid, cust_name=cname: delete_transaction(t_id, cust_id, cust_name)
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    )
                )
        
        detail_dialog.open = True
        page.update()

    def delete_transaction(tid, cid, cname):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("DELETE FROM transactions WHERE id = ?", (tid,))
        conn.commit()
        conn.close()
        load_data()
        show_details(cid, cname)
        page.snack_bar = ft.SnackBar(ft.Text("تراکنش حذف شد."), bgcolor="red")
        page.snack_bar.open = True
        page.update()

    def load_data(search_query=""):
        customers_list_view.controls.clear()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        if search_query:
            c.execute("""
                SELECT c.id, c.name, 
                       IFNULL(SUM(t.debt), 0), 
                       IFNULL(SUM(t.paid), 0),
                       IFNULL(MAX(t.date), '-')
                FROM customers c
                LEFT JOIN transactions t ON c.id = t.customer_id
                WHERE c.name LIKE ?
                GROUP BY c.id, c.name
                ORDER BY c.name
            """, (f"%{search_query}%",))
        else:
            c.execute("""
                SELECT c.id, c.name, 
                       IFNULL(SUM(t.debt), 0), 
                       IFNULL(SUM(t.paid), 0),
                       IFNULL(MAX(t.date), '-')
                FROM customers c
                LEFT JOIN transactions t ON c.id = t.customer_id
                GROUP BY c.id, c.name
                ORDER BY c.name
            """)
            
        rows = c.fetchall()
        sum_debt = 0
        sum_paid = 0

        for row in rows:
            c_id, name, t_debt, t_paid, last_date = row
            balance = t_debt - t_paid
            sum_debt += t_debt
            sum_paid += t_paid
            
            card = ft.Card(
                content=ft.Container(
                    padding=12,
                    ink=True,
                    on_click=lambda e, cid=c_id, cname=name: show_details(cid, cname),
                    content=ft.Column([
                        ft.Row([
                            ft.Text(name, weight=ft.FontWeight.BOLD, size=16, color=ft.colors.INDIGO_700),
                            ft.Text(f"مانده: {balance:,.0f} تومان", weight=ft.FontWeight.BOLD, 
                                    color=ft.colors.RED_700 if balance > 0 else ft.colors.GREEN_700)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(),
                        ft.Row([
                            ft.Text(f"کل خرید: {t_debt:,.0f} | کل پرداخت: {t_paid:,.0f}", size=11, color=ft.colors.GREY_700),
                            ft.IconButton(
                                icon=ft.icons.DELETE,
                                icon_color="red",
                                tooltip="حذف مشتری",
                                on_click=lambda e, cid=c_id, cname=name: delete_cust(cid, cname)
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    ])
                )
            )
            customers_list_view.controls.append(card)

        total_bal = sum_debt - sum_paid
        totals_text.value = f"کل بدهی: {sum_debt:,.0f} | کل پرداخت: {sum_paid:,.0f} | مانده کل: {total_bal:,.0f}"
        page.update()

    def save_clicked(e):
        name = name_field.value.strip()
        date = date_field.value.strip()
        try:
            debt = float(debt_field.value.strip() or 0)
            paid = float(paid_field.value.strip() or 0)
        except ValueError:
            page.snack_bar = ft.SnackBar(ft.Text("مبالغ باید عدد باشند!"))
            page.snack_bar.open = True
            page.update()
            return

        if not name:
            page.snack_bar = ft.SnackBar(ft.Text("لطفاً نام مشتری را وارد کنید."))
            page.snack_bar.open = True
            page.update()
            return

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id FROM customers WHERE name = ?", (name,))
        res = c.fetchone()
        if res:
            cust_id = res[0]
        else:
            c.execute("INSERT INTO customers (name) VALUES (?)", (name,))
            cust_id = c.lastrowid

        c.execute("INSERT INTO transactions (customer_id, date, debt, paid) VALUES (?, ?, ?, ?)",
                  (cust_id, date, debt, paid))
        conn.commit()
        conn.close()

        name_field.value = ""
        debt_field.value = "0"
        paid_field.value = "0"
        date_field.value = get_shamsi_date()
        
        load_data()
        page.snack_bar = ft.SnackBar(ft.Text("تراکنش با موفقیت ثبت شد."), bgcolor="green")
        page.snack_bar.open = True
        page.update()

    def delete_cust(cid, cname):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("DELETE FROM customers WHERE id = ?", (cid,))
        c.execute("DELETE FROM transactions WHERE customer_id = ?", (cid,))
        conn.commit()
        conn.close()
        load_data()
        page.snack_bar = ft.SnackBar(ft.Text(f"مشتری {cname} حذف شد."), bgcolor="red")
        page.snack_bar.open = True
        page.update()

    search_field.on_change = lambda e: load_data(search_field.value.strip())
    
    # دکمه سازگار با تمام نسخه‌های Flet
    btn_class = getattr(ft, "ElevatedButton", getattr(ft, "FilledButton", ft.TextButton))
    save_btn = btn_class(
        "ثبت تراکنش",
        icon=ft.icons.SAVE,
        on_click=save_clicked,
        bgcolor=ft.colors.BLUE,
        color=ft.colors.WHITE
    )

    page.add(
        ft.Text("دفتر حساب نیما (نسخه موبایل)", size=20, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE),
        ft.Divider(),
        name_field,
        ft.Row([debt_field, paid_field], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Row([date_field, save_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Divider(),
        search_field,
        totals_text,
        ft.Divider(),
        customers_list_view
    )
    
    load_data()

if __name__ == "__main__":
    if hasattr(ft, "app"):
        try:
            ft.app(target=main)
        except TypeError:
            ft.app(main)



