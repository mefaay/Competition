from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_session import Session
from flask import Response
import json
import sqlite3
import pycountry



app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

YONETICI_ADI = "admin"
YONETICI_SIFRE = "12345"

def veritabani_baglantisi_kur():
    conn = sqlite3.connect('pentatlon.db')
    return conn

def ulkeler_ve_bayraklar():
    ulkeler = list(pycountry.countries)
    ulke_isimleri = [ulke.name for ulke in ulkeler]
    return ulke_isimleri

def yas_kategorilerini_getir():
    conn = veritabani_baglantisi_kur()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT yas_kategorisi FROM sporcu")  # Sporcu tablosundan yaş kategorilerini çek
    yas_kategorileri = cursor.fetchall()
    conn.close()
    return yas_kategorileri


def tablolari_olustur():
    conn = veritabani_baglantisi_kur()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS musabaka (
            id INTEGER PRIMARY KEY,
            adi TEXT,
            branslar TEXT,
            baslama_tarihi TEXT,
            bitis_tarihi TEXT,
            musabaka_ili TEXT
        )
    """)

    cursor.execute('''
       CREATE TABLE IF NOT EXISTS sporcu (
           id INTEGER PRIMARY KEY,
           musabaka_id INTEGER,
           adi_soyadi TEXT,
           ulkesi TEXT,
           kulubu TEXT,
           lazer_run_sonucu TEXT,
           yuzme_sonucu TEXT,
           eskrim_sonucu TEXT,
           obs_sonucu TEXT,
           toplam_puani TEXT    ,
           yas_kategorisi TEXT,
           FOREIGN KEY (musabaka_id) REFERENCES musabaka(id)
       )
    ''')
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS kulup (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kulup_adi TEXT,
                yetkili_unvan TEXT,
                yetkili_ad_soyad TEXT,
                yetkili_iletisim_numarasi TEXT,
                kulup_eposta TEXT,
                kulup_iban TEXT,
                kulup_il TEXT
            )
            ''')

    conn.commit()
    conn.close()


@app.route('/')
def ana_sayfa():
    return render_template('ana_sayfa.html')


@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        conn = veritabani_baglantisi_kur()
        cursor = conn.cursor()

        # Toplam müsabaka sayısını al
        cursor.execute("SELECT COUNT(*) FROM musabaka")
        toplam_musabaka = cursor.fetchone()[0]

        # Toplam sporcu sayısını al
        cursor.execute("SELECT COUNT(*) FROM sporcu")
        toplam_sporcu = cursor.fetchone()[0]

        # Toplam kulüp sayısını al
        cursor.execute("SELECT COUNT(*) FROM kulup")
        toplam_kulup = cursor.fetchone()[0]

        # Müsabaka bilgilerini al
        cursor.execute("SELECT * FROM musabaka")
        musabakalar = cursor.fetchall()

        # Tüm sporcu bilgilerini al
        cursor.execute("SELECT * FROM sporcu ORDER BY id DESC LIMIT 10")   # Bu satırı değiştirdik.
        sporcular = cursor.fetchall()

        # Kulüp bilgilerini al
        cursor.execute("SELECT * FROM kulup")
        kulupler = cursor.fetchall()

        musabaka_sporculari = {}
        for musabaka in musabakalar:
            musabaka_id = musabaka[0]
            cursor.execute("SELECT * FROM sporcu WHERE musabaka_id = ? ORDER BY id DESC LIMIT 10", (musabaka_id,))
            musabaka_sporculari[musabaka_id] = cursor.fetchall()

        conn.close()
        return render_template('dashboard.html', musabakalar=musabakalar, musabaka_sporculari=musabaka_sporculari,
                               toplam_musabaka=toplam_musabaka, toplam_sporcu=toplam_sporcu, toplam_kulup=toplam_kulup,
                               kulupler=kulupler, sporcular=sporcular)  # sporcular değişkenini burada gönderdik.

    return redirect(url_for('ana_sayfa'))


@app.route('/cikis')
def cikis():
    session.pop('loggedin', None)
    return redirect(url_for('ana_sayfa'))

@app.route('/yonetici_girisi', methods=['GET', 'POST'])
def yonetici_girisi():
    if request.method == 'POST':
        kullanici_adi = request.form['kullanici_adi']
        sifre = request.form['sifre']
        if kullanici_adi == YONETICI_ADI and sifre == YONETICI_SIFRE:
            session['loggedin'] = True
            return redirect(url_for('dashboard'))
        else:
            flash("Yanlış kullanıcı adı veya şifre!", "danger")  # Hata mesajını oluşturun
            return redirect(url_for('ana_sayfa'))  # Kullanıcıyı ana sayfaya yönlendirin
    return render_template('yonetici_girisi.html')

@app.route('/musabaka_ekle', methods=['GET', 'POST'])
def musabaka_ekle():
    # Yönetici girişi kontrolü
    if 'loggedin' not in session:
        return redirect(url_for('ana_sayfa'))
    if request.method == 'POST':
        adi = request.form['adi']
        branslar = request.form['branslar']
        baslama_tarihi = request.form['baslama_tarihi']
        bitis_tarihi = request.form['bitis_tarihi']
        musabaka_ili = request.form['musabaka_ili']

        conn = veritabani_baglantisi_kur()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO musabaka (adi, branslar, baslama_tarihi, bitis_tarihi, musabaka_ili) VALUES (?, ?, ?, ?, ?)", (adi, branslar, baslama_tarihi, bitis_tarihi, musabaka_ili))
        conn.commit()
        conn.close()

        return redirect(url_for('musabakalar'))

    return render_template('musabaka_ekle.html')


@app.route('/musabakalar', methods=['GET'])
def musabakalar():
    # Yönetici girişi kontrolü
    if 'loggedin' not in session:
        return redirect(url_for('ana_sayfa'))
    conn = veritabani_baglantisi_kur()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM musabaka")
    musabakalar = cursor.fetchall()
    conn.close()

    yas_kategorileri = yas_kategorilerini_getir()  # Yaş kategorilerini çek

    return render_template('musabakalar.html', musabakalar=musabakalar, yas_kategorileri=yas_kategorileri)


@app.route('/musabaka_guncelle/<int:musabaka_id>', methods=['GET', 'POST'])
def musabaka_guncelle(musabaka_id):
    # Yönetici girişi kontrolü
    if 'loggedin' not in session:
        return redirect(url_for('ana_sayfa'))
    conn = veritabani_baglantisi_kur()
    cursor = conn.cursor()

    if request.method == 'POST':
        yeni_adi = request.form['yeni_adi']
        yeni_brans = request.form['branslar']
        yeni_baslama_tarihi = request.form['baslama_tarihi']
        yeni_bitis_tarihi = request.form['bitis_tarihi']
        yeni_musabaka_ili = request.form['musabaka_ili']
        cursor.execute("UPDATE musabaka SET adi = ?, branslar = ?, baslama_tarihi = ?, bitis_tarihi = ?, musabaka_ili = ? WHERE id = ?",
                       (yeni_adi, yeni_brans, yeni_baslama_tarihi, yeni_bitis_tarihi, yeni_musabaka_ili, musabaka_id))
        conn.commit()
        conn.close()
        return redirect(url_for('musabakalar'))

    cursor.execute("SELECT * FROM musabaka WHERE id = ?", (musabaka_id,))
    musabaka = cursor.fetchone()
    conn.close()

    return render_template('musabaka_guncelle.html', musabaka=musabaka)



@app.route('/musabaka_sil/<int:musabaka_id>', methods=['GET'])
def musabaka_sil(musabaka_id):
    # Yönetici girişi kontrolü
    if 'loggedin' not in session:
        return redirect(url_for('ana_sayfa'))
    conn = veritabani_baglantisi_kur()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM musabaka WHERE id=?", (musabaka_id,))
    cursor.execute("DELETE FROM sporcu WHERE musabaka_id=?", (musabaka_id,))

    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))


@app.route('/sporcu_ekle', methods=['GET', 'POST'])
def sporcu_ekle():
    # Yönetici girişi kontrolü
    if 'loggedin' not in session:
        return redirect(url_for('ana_sayfa'))
    if request.method == 'POST':
        musabaka_id = request.form['musabaka_id']
        adi_soyadi = request.form['adi_soyadi']
        ulkesi = request.form['ulkesi']
        kulubu = request.form['kulubu']
        lazer_run_sonucu = request.form['lazer_run_sonucu']
        yuzme_sonucu = request.form['yuzme_sonucu']
        eskrim_sonucu = request.form['eskrim_sonucu']
        obs_sonucu = request.form['obs_sonucu']
        toplam_puani = request.form['toplam_puani']
        yas_kategorisi = request.form['yas_kategorisi']

        conn = veritabani_baglantisi_kur()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sporcu (musabaka_id, adi_soyadi, ulkesi, kulubu, lazer_run_sonucu, yuzme_sonucu, eskrim_sonucu, obs_sonucu, toplam_puani, yas_kategorisi)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (musabaka_id, adi_soyadi, ulkesi, kulubu, lazer_run_sonucu, yuzme_sonucu, eskrim_sonucu, obs_sonucu,
              toplam_puani, yas_kategorisi))
        conn.commit()
        conn.close()

        return redirect(url_for('sporcu_listesi'))

    # GET talebi için:
    ulke_isimleri = ulkeler_ve_bayraklar()

    conn = veritabani_baglantisi_kur()
    cursor = conn.cursor()
    cursor.execute("SELECT id, adi FROM musabaka")
    musabakalar = cursor.fetchall()
    cursor.execute("SELECT kulup_adi FROM kulup")
    kulupler = [kulup[0] for kulup in cursor.fetchall()]
    conn.close()

    return render_template('sporcu_ekle.html', musabakalar=musabakalar, ulke_isimleri=ulke_isimleri, kulupler=kulupler)



@app.route('/musabaka_detay/<int:musabaka_id>', methods=['GET', 'POST'])
def musabaka_detay(musabaka_id):
    # Yönetici girişi kontrolü
    if 'loggedin' not in session:
        return redirect(url_for('ana_sayfa'))
    conn = veritabani_baglantisi_kur()
    cursor = conn.cursor()

    # Seçilen müsabakayla ilgili bilgileri çek
    cursor.execute("SELECT * FROM musabaka WHERE id = ?", (musabaka_id,))
    musabaka = cursor.fetchone()

    # Seçilen müsabakanın sporcularını çek
    cursor.execute("SELECT * FROM sporcu WHERE musabaka_id = ?", (musabaka_id,))
    sporcular = cursor.fetchall()

    if request.method == 'POST':
        yas_kategorisi = request.form.get('yas_kategorisi')
        if yas_kategorisi == 'Tümü':
            cursor.execute("SELECT * FROM sporcu WHERE musabaka_id = ?", (musabaka_id,))
        else:
            cursor.execute("SELECT * FROM sporcu WHERE musabaka_id = ? AND yas_kategorisi = ?", (musabaka_id, yas_kategorisi))
        sporcular = cursor.fetchall()

    conn.close()
    return render_template('musabaka_detay.html', musabaka=musabaka, sporcular=sporcular)


@app.route('/sporcular', methods=['GET', 'POST'])
def sporcu_listesi():
    # Yönetici girişi kontrolü
    if 'loggedin' not in session:
        return redirect(url_for('ana_sayfa'))
    if request.method == 'GET':
        yas_kategorisi = request.args.get('yas_kategorisi', None)
        if yas_kategorisi:
            print("Filtrelenen yaş kategorisi:", yas_kategorisi)
            conn = veritabani_baglantisi_kur()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sporcu WHERE yas_kategorisi=?", (yas_kategorisi,))
            sporcular = cursor.fetchall()
            conn.close()
            return render_template('sporcu_listesi.html', sporcular=sporcular)

        # Yeni bir GET talebi ise ve yas_kategorisi belirtilmemişse, tüm sporcuları getir
        conn = veritabani_baglantisi_kur()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sporcu")
        sporcular = cursor.fetchall()
        conn.close()
        return render_template('sporcu_listesi.html', sporcular=sporcular)

    return render_template('sporcu_listesi.html', sporcular=[])

@app.context_processor
def inject_country_flags():
    bayrak_dizin = "static/bayraklar"  # Bayrak dosyalarının bulunduğu dizin

    ulkeler = list(pycountry.countries)
    ulke_isimleri = [ulke.name for ulke in ulkeler]  # Mevcut ülke isimlerini alıyoruz

    ulke_bayraklari = {}

    for ulke_adi in ulke_isimleri:
        ulke = pycountry.countries.get(name=ulke_adi)
        if ulke:
            ulke_kodu = ulke.alpha_2.lower()  # Ülke kodunu alıyoruz (örneğin: tr)
            bayrak_dosya_adi = f"{ulke_kodu}.png"  # Bayrak dosya adını oluşturuyoruz (örneğin: tr.png)
            ulke_bayraklari[ulke_adi] = {
                "bayrak_url": f"/{bayrak_dizin}/{bayrak_dosya_adi}",
                "ulke_adi": ulke_adi  # Ülke adını kaydediyoruz
            }

    return dict(ulke_bayraklari=ulke_bayraklari)

def ulke_isimlerini_al():
    ulkeler = list(pycountry.countries)
    ulke_isimleri = [ulke.name for ulke in ulkeler]
    return ulke_isimleri


@app.route('/live')
def live_results():
    # Veritabanına bağlan
    conn = sqlite3.connect('pentatlon.db')
    cursor = conn.cursor()

    # Müsabaka ve yaş kategorisi filtrelerini al
    selected_musabaka = request.args.get('musabaka')
    selected_yas_kategorisi = request.args.get('yas_kategorisi')

    # SQL sorgusunu ve parametrelerini oluştur
    query = "SELECT * FROM sporcu"
    params = []

    if selected_musabaka or selected_yas_kategorisi:
        filters = []
        if selected_musabaka:
            filters.append("musabaka.adi = ?")
            params.append(selected_musabaka)
        if selected_yas_kategorisi:
            filters.append("sporcu.yas_kategorisi = ?")
            params.append(selected_yas_kategorisi)
        query += " JOIN musabaka ON sporcu.musabaka_id = musabaka.id WHERE " + " AND ".join(filters)

    cursor.execute(query, params)
    sporcular = cursor.fetchall()

    # Tüm müsabakaları sorgula (dropdown için)
    cursor.execute("SELECT DISTINCT adi FROM musabaka")
    musabakalar = cursor.fetchall()
    musabaka_options = "\n".join(['<option value="{}">{}</option>'.format(m[0], m[0]) for m in musabakalar])

    conn.close()

    # Sporcuları toplam puanlarına göre büyükten küçüğe sırala
    sporcular.sort(key=lambda sporcu: float(sporcu[9]), reverse=True)

    # Sonuçları live.html şablonuyla renderle
    return render_template('live.html', sporcular=sporcular, musabaka_options=musabaka_options)



@app.route('/static/<path:filename>')
def send_static(filename):
    return send_from_directory('static', filename)


@app.route('/sporcu_duzenle/<int:sporcu_id>', methods=['GET', 'POST'])
def sporcu_duzenle(sporcu_id):
    # Yönetici girişi kontrolü
    if 'loggedin' not in session:
        return redirect(url_for('ana_sayfa'))
    # Sporcu bilgilerini veritabanından çek
    conn = veritabani_baglantisi_kur()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sporcu WHERE id = ?", (sporcu_id,))
    sporcu = cursor.fetchone()

    # Ülke isimleri listesi
    ulke_isimleri = ulke_isimlerini_al()

    # Kulüp isimleri listesi
    cursor.execute("SELECT kulup_adi FROM kulup")
    kulupler = [row[0] for row in cursor.fetchall()]

    if request.method == 'POST':
        adi_soyadi = request.form['adi_soyadi']
        ulkesi = request.form['ulkesi']
        kulubu = request.form['kulubu']
        yas_kategorisi = request.form['yas_kategorisi']
        lazer_run_sonucu = request.form['lazer_run_sonucu']
        yuzme_sonucu = request.form['yuzme_sonucu']
        eskrim_sonucu = request.form['eskrim_sonucu']
        obs_sonucu = request.form['obs_sonucu']
        toplam_puani = request.form['toplam_puani']

        cursor.execute("""
            UPDATE sporcu
            SET adi_soyadi = ?, ulkesi = ?, kulubu = ?, yas_kategorisi = ?,
                lazer_run_sonucu = ?, yuzme_sonucu = ?, eskrim_sonucu = ?,
                obs_sonucu = ?, toplam_puani = ?
            WHERE id = ?
        """, (adi_soyadi, ulkesi, kulubu, yas_kategorisi, lazer_run_sonucu,
              yuzme_sonucu, eskrim_sonucu, obs_sonucu, toplam_puani, sporcu_id))

        conn.commit()
        conn.close()

        return redirect(url_for('sporcu_listesi'))

    return render_template('sporcu_duzenle.html', sporcu=sporcu, ulke_isimleri=ulke_isimleri, kulupler=kulupler)



@app.route('/sporcu_sil/<int:sporcu_id>', methods=['GET', 'POST'])
def sporcu_sil(sporcu_id):
    # Yönetici girişi kontrolü
    if 'loggedin' not in session:
        return redirect(url_for('ana_sayfa'))
    conn = veritabani_baglantisi_kur()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM sporcu WHERE id=?", (sporcu_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('sporcu_listesi'))


@app.route('/kulup_ekle', methods=['GET', 'POST'])
def kulup_ekle():
    # Yönetici girişi kontrolü
    if 'loggedin' not in session:
        return redirect(url_for('ana_sayfa'))
    if request.method == 'POST':
        kulup_adi = request.form.get('kulup_adi')
        yetkili_unvan = request.form.get('yetkili_unvan')
        yetkili_ad_soyad = request.form.get('yetkili_ad_soyad')
        yetkili_iletisim_numarasi = request.form.get('yetkili_iletisim_numarasi')
        kulup_eposta = request.form.get('kulup_eposta')
        kulup_iban = request.form.get('kulup_iban')
        kulup_il = request.form.get('kulup_il')

        with veritabani_baglantisi_kur() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO kulup (kulup_adi, yetkili_unvan, yetkili_ad_soyad, yetkili_iletisim_numarasi, kulup_eposta, kulup_iban, kulup_il)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
            kulup_adi, yetkili_unvan, yetkili_ad_soyad, yetkili_iletisim_numarasi, kulup_eposta, kulup_iban, kulup_il))
            conn.commit()

        return redirect(url_for('kulupleri_listele'))

    return render_template('kulup_ekle.html')


@app.route('/kulupleri_listele')
def kulupleri_listele():
    # Yönetici girişi kontrolü
    if 'loggedin' not in session:
        return redirect(url_for('ana_sayfa'))
    conn = veritabani_baglantisi_kur()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM kulup")
    kulupler = cursor.fetchall()
    conn.close()
    return render_template('kulupleri_listele.html', kulupler=kulupler)


@app.route('/kulup_guncelle/<int:id>', methods=['GET', 'POST'])
def kulup_guncelle(id):
    # Yönetici girişi kontrolü
    if 'loggedin' not in session:
        return redirect(url_for('ana_sayfa'))
    conn = veritabani_baglantisi_kur()
    cursor = conn.cursor()

    if request.method == 'POST':
        kulup_adi = request.form.get('kulup_adi')
        yetkili_unvan = request.form.get('yetkili_unvan')
        yetkili_ad_soyad = request.form.get('yetkili_ad_soyad')
        yetkili_iletisim_numarasi = request.form.get('yetkili_iletisim_numarasi')
        kulup_eposta = request.form.get('kulup_eposta')
        kulup_iban = request.form.get('kulup_iban')
        kulup_il = request.form.get('kulup_il')

        cursor.execute('''
            UPDATE kulup
            SET kulup_adi = ?, yetkili_unvan = ?, yetkili_ad_soyad = ?, yetkili_iletisim_numarasi = ?, kulup_eposta = ?, kulup_iban = ?, kulup_il = ?
            WHERE id = ?
        ''', (
            kulup_adi, yetkili_unvan, yetkili_ad_soyad, yetkili_iletisim_numarasi, kulup_eposta, kulup_iban, kulup_il, id))
        conn.commit()
        conn.close()
        return redirect(url_for('kulupleri_listele'))

    cursor.execute("SELECT * FROM kulup WHERE id = ?", (id,))
    kulup = cursor.fetchone()
    conn.close()

    return render_template('kulup_guncelle.html', kulup=kulup)


@app.route('/kulup_sil/<int:id>', methods=['GET'])
def kulup_sil(id):
    # Yönetici girişi kontrolü
    if 'loggedin' not in session:
        return redirect(url_for('ana_sayfa'))
    with veritabani_baglantisi_kur() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM kulup WHERE id = ?", (id,))
        conn.commit()
    return redirect(url_for('kulupleri_listele'))


@app.route('/kulup_detay/<int:id>')
def kulup_detay(id):
    # Yönetici girişi kontrolü
    if 'loggedin' not in session:
        return redirect(url_for('ana_sayfa'))
    conn = veritabani_baglantisi_kur()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM kulup WHERE id = ?", (id,))
    kulup = cursor.fetchone()
    conn.close()
    return render_template('kulup_detay.html', kulup=kulup)


if __name__ == '__main__':
    tablolari_olustur()
    app.run(debug=True)
