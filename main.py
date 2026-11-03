from datetime import datetime
import os
import sqlite3
import flet as ft


def get_db_path():
  # مسیر امن مخصوص ذخیره داده در اپلیکیشن‌های اندروید و دسکتاپ
  if os.environ.get("FLET_APP_STORAGE_DATA"):
    storage_dir = os.environ.get("FLET_APP_STORAGE_DATA")
  else:
    storage_dir = os.path.dirname(os.path.abspath(__file__))

  if not os.path.exists(storage_dir):
    os.makedirs(storage_dir, exist_ok=True)

  return os.path.join(storage_dir, "my_accounting_mobile.db")


DB_NAME = get_db_path()


def init_db():
  try:
    conn = sqlite3.connect(DB_NAME)
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
                description TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers (id)
            )
        """
    )
    conn.commit()
    conn.close()
  except Exception as e:
    print(f"Database Init Error: {e}")


def main(page: ft.Page):
  page.title = "دفتر حساب نیما (نسخه موبایل)"
  page.rtl = True
  page.vertical_alignment = ft.MainAxisAlignment.START
  page.padding = 20

  try:
    init_db()
  except Exception as e:
    page.add(ft.Text(f"خطا در راه‌اندازی پایگاه داده: {e}", color="red"))
    return

  # المان‌های رابط کاربری
  title = ft.Text(
      "دفتر حساب نیما", size=22, weight=ft.FontWeight.BOLD, color="blue"
  )

  def load_data():
    # تست بارگذاری اولیه
    pass

  page.add(title, ft.Text("برنامه با موفقیت اجرا شد!", color="green"))
  page.update()


if __name__ == "__main__":
  ft.app(target=main)
