import tkinter as tk
from tkinter import ttk, messagebox
import http.client
import json
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# API Key ve URL'ler
API_KEY = "0W4Cfu16ffYGvo2uMXGIv3:6gvgAckRulrAWFk4dSpDqi"
CURRENCY_URL = "/economy/allCurrency"
GOLD_URL = "/economy/goldPrice"

# Döviz ve altın verilerini API'den çekme fonksiyonları
def dovizcekme(api_key):
    conn = http.client.HTTPSConnection("api.collectapi.com")
    headers = {
        "authorization": f"apikey {api_key}",
        "content-type": "application/json"
    }
    conn.request("GET", CURRENCY_URL, headers=headers)
    response = conn.getresponse()
    if response.status == 200:
        data = response.read()
        return json.loads(data)
    else:
        print("Döviz verilerini çekerken hata oluştu:", response.status, response.reason)
        return None

def altincekme(api_key):
    conn = http.client.HTTPSConnection("api.collectapi.com")
    headers = {
        "authorization": f"apikey {api_key}",
        "content-type": "application/json"
    }
    conn.request("GET", GOLD_URL, headers=headers)
    response = conn.getresponse()
    if response.status == 200:
        data = response.read()
        return json.loads(data)
    else:
        print("Altın verilerini çekerken hata oluştu:", response.status, response.reason)
        return None

# Veritabanı oluşturma ve kontrol
def veritabanı():
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tür TEXT,
            miktar REAL,
            tarih TEXT,
            kaldırıldı INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# Varlık ekleme
def varlıkgir(asset_type, amount):
    if amount == '0':
        messagebox.showerror("Hata", f"Sıfır değer olarak girilemez")
        return
    
    try:
        amount = float(amount)
        if amount <= 0:
            messagebox.showerror("Hata", "Miktar sıfırdan büyük olmalıdır.")
            return
    except ValueError:
        messagebox.showerror("Hata", "Geçerli bir miktar girin.")
        return

    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (tür, miktar, tarih)
        VALUES (?, ?, datetime('now'))
    ''', (asset_type, amount))
    conn.commit()
    conn.close()
    messagebox.showinfo("Başarılı", "Varlık eklendi!")
    varlıkyükle()

# Varlık kaldırma
def varlıkkaldır():
    selected_item = assets_listbox.selection()
    if not selected_item:
        messagebox.showwarning("Uyarı", "Lütfen kaldırmak istediğiniz varlığı seçin.")
        return

    item_id = assets_listbox.item(selected_item[0])['values'][0]
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE transactions SET kaldırıldı=1 WHERE id=?', (item_id,))
        conn.commit()
        messagebox.showinfo("Başarılı", "Varlık kaldırıldı.")
        varlıkyükle()
    except sqlite3.Error as e:
        conn.rollback()
        messagebox.showerror("Hata", "Varlık kaldırılırken bir hata oluştu: " + str(e))
    finally:
        conn.close()

# Varlıkları yükleme
def varlıkyükle():
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, tür, miktar, tarih FROM transactions WHERE kaldırıldı=0')
    rows = cursor.fetchall()
    conn.close()

    for row in assets_listbox.get_children():
        assets_listbox.delete(row)

    for row in rows:
        assets_listbox.insert("", "end", values=row)

# Tüm varlıkları gösterme
def tüm_varlıkları_yükle():
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, tür, miktar, tarih, kaldırıldı FROM transactions')
    rows = cursor.fetchall()
    conn.close()

    tüm_varlıklar_penceresi = tk.Toplevel()
    tüm_varlıklar_penceresi.title("Tüm Varlıklar")

    cols = ('ID', 'Varlık Türü', 'Miktar', 'Tarih', 'Kaldırıldı')
    tüm_varlıklar_listbox = ttk.Treeview(tüm_varlıklar_penceresi, columns=cols, show='headings')

    for col in cols:
        tüm_varlıklar_listbox.heading(col, text=col)
        tüm_varlıklar_listbox.column(col, width=100)

    for row in rows:
        tüm_varlıklar_listbox.insert("", "end", values=row)

    tüm_varlıklar_listbox.pack(fill="both", expand=True)

# Varlıkları hesaplama
def varlıklarıhesapla():
    total_try = 0
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT tür, miktar FROM transactions WHERE kaldırıldı=0')
    rows = cursor.fetchall()
    conn.close()

    doviz_data = dovizcekme(API_KEY)
    altin_data = altincekme(API_KEY)

    if doviz_data and altin_data:
        for row in rows:
            asset_type = row[0]
            amount = row[1]

            if asset_type == 'TRY':
                total_try += amount
            else:
                for currency in doviz_data['result']:
                    if currency['code'] == asset_type:
                        total_try += amount * float(currency['selling'])
                        break
                for gold in altin_data['result']:
                    if gold['name'].lower() == asset_type.lower():
                        total_try += amount * float(gold['selling'])
                        break

    return total_try

# Varlık grafiği oluşturma
def varlık_grafiği():
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT tarih, tür, miktar FROM transactions WHERE kaldırıldı=0')
    rows = cursor.fetchall()
    conn.close()

    tarih_dict = {}
    doviz_data = dovizcekme(API_KEY)
    altin_data = altincekme(API_KEY)

    if not doviz_data or not altin_data:
        return

    for row in rows:
        tarih, tür, miktar = row
        if tarih not in tarih_dict:
            tarih_dict[tarih] = 0

        if tür == 'TRY':
            tarih_dict[tarih] += miktar
        else:
            for currency in doviz_data['result']:
                if currency['code'] == tür:
                    tarih_dict[tarih] += miktar * float(currency['selling'])
                    break
            for gold in altin_data['result']:
                if gold['name'].lower() == tür.lower():
                    tarih_dict[tarih] += miktar * float(gold['selling'])
                    break

    tarih_listesi = list(tarih_dict.keys())
    değer_listesi = list(tarih_dict.values())

    fig, ax = plt.subplots()
    ax.plot(tarih_listesi, değer_listesi, marker='o')
    ax.set_xlabel("Tarih")
    ax.set_ylabel("Değer (TRY)")
    ax.set_title("Zaman İçerisinde Varlık Değeri")

    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.get_tk_widget().pack(fill="both", expand=True)
    canvas.draw()

# Kullanıcı arayüzü
window = tk.Tk()
window.title("Varlık Yönetim Sistemi")

currency_names = []
currency_data = dovizcekme(API_KEY)
gold_data = altincekme(API_KEY)

if currency_data:
    for currency in currency_data['result']:
        currency_names.append(currency['code'])

if gold_data:
    for gold in gold_data['result']:
        currency_names.append(gold['name'].lower())

# Döviz ve miktar girişi
frame = tk.Frame(window)
frame.pack(pady=10)

label_asset_type = tk.Label(frame, text="Varlık Türü:")
label_asset_type.grid(row=0, column=0, padx=5)

entry_asset_type = ttk.Combobox(frame, values=currency_names)
entry_asset_type.grid(row=0, column=1, padx=5)

label_amount = tk.Label(frame, text="Miktar:")
label_amount.grid(row=1, column=0, padx=5)

entry_amount = tk.Entry(frame)
entry_amount.grid(row=1, column=1, padx=5)

button_add = tk.Button(frame, text="Ekle", command=lambda: varlıkgir(entry_asset_type.get(), entry_amount.get()))
button_add.grid(row=2, column=0, columnspan=2, pady=10)

# Varlık listesi
cols = ('ID', 'Varlık Türü', 'Miktar', 'Tarih')
assets_listbox = ttk.Treeview(window, columns=cols, show='headings')
for col in cols:
    assets_listbox.heading(col, text=col)
    assets_listbox.column(col, width=100)
assets_listbox.pack(fill="both", expand=True, pady=10)

button_remove = tk.Button(window, text="Kaldır", command=varlıkkaldır)
button_remove.pack(pady=5)

button_calculate = tk.Button(window, text="Toplam Değer (TRY)", command=lambda: messagebox.showinfo("Toplam Değer", f"Toplam Değer: {varlıklarıhesapla()} TRY"))
button_calculate.pack(pady=5)

button_all_assets = tk.Button(window, text="Tüm Varlıkları Göster", command=tüm_varlıkları_yükle)
button_all_assets.pack(pady=5)

button_graph = tk.Button(window, text="Varlık Grafiği", command=varlık_grafiği)
button_graph.pack(pady=5)

veritabanı()
varlıkyükle()
window.mainloop()
