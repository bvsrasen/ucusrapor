"""
UçuşRapor - Standart Excel raporu ve dashboard üretimi.

Gereksinim karşılıkları:
    FR-06  Standart şablonda Excel raporu   -> excel_raporu_olustur()
    FR-07  İrtifa-zaman ve ivme-zaman grafikleri
    FR-08  Veri kalitesi özeti

Rapordaki metrikler Excel FORMÜLLERİ ile 'Temiz Veri' sayfasından hesaplanır;
yanlarındaki "Python doğrulama" sütunu aynı metriğin Python ile hesaplanan
değeridir. İki bağımsız hesabın örtüşmesi, raporun doğruluğunun kanıtıdır.
"""

from datetime import datetime

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference, ScatterChart, Series
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .isleme import DURUM_ADLARI

# --- Görsel kimlik ---
LACIVERT = "1F3864"
MAVI = "2E75B6"
ACIK_MAVI = "DDEBF7"
GRI = "F2F2F2"
YESIL = "E2EFDA"
KIRMIZI = "FCE4D6"
YAZI = "Arial"

BASLIK_FONT = Font(name=YAZI, size=18, bold=True, color="FFFFFF")
ALT_BASLIK_FONT = Font(name=YAZI, size=11, italic=True, color="FFFFFF")
BOLUM_FONT = Font(name=YAZI, size=12, bold=True, color=LACIVERT)
TABLO_BASLIK_FONT = Font(name=YAZI, size=10, bold=True, color="FFFFFF")
NORMAL = Font(name=YAZI, size=10)
KALIN = Font(name=YAZI, size=10, bold=True)
NOT_FONT = Font(name=YAZI, size=9, italic=True, color="595959")

INCE = Side(style="thin", color="BFBFBF")
KENARLIK = Border(left=INCE, right=INCE, top=INCE, bottom=INCE)


def _tablo_basligi(ws, satir, sutun_baslangic, basliklar, renk=MAVI):
    for i, metin in enumerate(basliklar):
        h = ws.cell(row=satir, column=sutun_baslangic + i, value=metin)
        h.font = TABLO_BASLIK_FONT
        h.fill = PatternFill("solid", fgColor=renk)
        h.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        h.border = KENARLIK


def _hucre(ws, satir, sutun, deger, font=NORMAL, fmt=None, fill=None, hizala="left"):
    c = ws.cell(row=satir, column=sutun, value=deger)
    c.font = font
    c.border = KENARLIK
    c.alignment = Alignment(horizontal=hizala, vertical="center", wrap_text=True)
    if fmt:
        c.number_format = fmt
    if fill:
        c.fill = PatternFill("solid", fgColor=fill)
    return c


# ---------------------------------------------------------------------------
# Sayfa: Temiz Veri
# ---------------------------------------------------------------------------
def _temiz_veri_sayfasi(wb, df):
    ws = wb.create_sheet("Temiz Veri")
    basliklar = ["Uçuş zamanı (s)", "Zaman (ms)", "İrtifa (m)", "Basınç (hPa)",
                 "İvme X (g)", "İvme Y (g)", "İvme Z (g)", "Toplam ivme (g)",
                 "Sıcaklık (°C)", "Durum", "Durum adı", "Kaynak satır"]
    _tablo_basligi(ws, 1, 1, basliklar, renk=LACIVERT)

    for i, r in enumerate(df.itertuples(index=False), start=2):
        ws.cell(row=i, column=1, value=round(r.ucus_zamani_s, 1))
        ws.cell(row=i, column=2, value=int(r.zaman_ms))
        ws.cell(row=i, column=3, value=round(float(r.irtifa_m), 2))
        ws.cell(row=i, column=4, value=round(float(r.basinc_hPa), 2))
        ws.cell(row=i, column=5, value=round(float(r.ivme_x_g), 3))
        ws.cell(row=i, column=6, value=round(float(r.ivme_y_g), 3))
        ws.cell(row=i, column=7, value=round(float(r.ivme_z_g), 3))
        ws.cell(row=i, column=8, value=f"=SQRT(E{i}^2+F{i}^2+G{i}^2)")
        ws.cell(row=i, column=9, value=round(float(r.sicaklik_C), 2))
        ws.cell(row=i, column=10, value=int(r.durum))
        ws.cell(row=i, column=11, value=r.durum_adi)
        ws.cell(row=i, column=12, value=int(r.kaynak_satir))

    son = len(df) + 1
    formatlar = {1: "0.0", 2: "0", 3: "#,##0.00", 4: "0.00", 5: "0.000", 6: "0.000",
                 7: "0.000", 8: "0.000", 9: "0.00", 10: "0", 12: "0"}
    for sutun, fmt in formatlar.items():
        for (c,) in ws.iter_rows(min_row=2, max_row=son, min_col=sutun, max_col=sutun):
            c.number_format = fmt
            c.font = NORMAL
    for (c,) in ws.iter_rows(min_row=2, max_row=son, min_col=11, max_col=11):
        c.font = NORMAL

    genislikler = [15, 11, 11, 12, 10, 10, 10, 14, 12, 8, 20, 12]
    for i, g in enumerate(genislikler, start=1):
        ws.column_dimensions[get_column_letter(i)].width = g
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:L{son}"
    return ws, son


# ---------------------------------------------------------------------------
# Sayfa: Veri Kalitesi
# ---------------------------------------------------------------------------
def _veri_kalitesi_sayfasi(wb, kayitlar):
    ws = wb.create_sheet("Veri Kalitesi")
    ws["A1"] = "Veri Kalitesi Günlüğü"
    ws["A1"].font = Font(name=YAZI, size=14, bold=True, color=LACIVERT)
    ws["A2"] = "Ham log dosyasında tespit edilen her sorun ve sistemin yaptığı müdahale."
    ws["A2"].font = NOT_FONT

    basliklar = ["Kaynak satır", "Zaman (ms)", "Sorun tipi", "Sütun", "Orijinal değer", "Yapılan işlem"]
    _tablo_basligi(ws, 4, 1, basliklar, renk=LACIVERT)
    for i, k in enumerate(kayitlar, start=5):
        _hucre(ws, i, 1, k["kaynak_satir"], hizala="center")
        _hucre(ws, i, 2, k["zaman_ms"], fmt="0", hizala="center")
        _hucre(ws, i, 3, k["tip"])
        _hucre(ws, i, 4, k["sutun"], hizala="center")
        _hucre(ws, i, 5, k["orijinal_deger"] if k["orijinal_deger"] != "" else "(boş)", hizala="center")
        _hucre(ws, i, 6, k["islem"])

    for sutun, g in zip("ABCDEF", [12, 12, 20, 14, 15, 48]):
        ws.column_dimensions[sutun].width = g
    ws.freeze_panes = "A5"
    son = max(5, len(kayitlar) + 4)
    ws.auto_filter.ref = f"A4:F{son}"
    return ws, son


# ---------------------------------------------------------------------------
# Sayfa: Uçuş Olayları
# ---------------------------------------------------------------------------
def _ucus_olaylari_sayfasi(wb, son):
    ws = wb.create_sheet("Uçuş Olayları")
    ws["A1"] = "Uçuş Olayları Zaman Çizelgesi (FSM Aşamaları)"
    ws["A1"].font = Font(name=YAZI, size=14, bold=True, color=LACIVERT)
    ws["A2"] = "Tüm değerler 'Temiz Veri' sayfasından formüllerle hesaplanır. Zaman, kalkış anına (t=0) göredir."
    ws["A2"].font = NOT_FONT

    _tablo_basligi(ws, 4, 1, ["Kod", "Aşama", "Başlangıç (s)", "Başlangıç irtifası (m)", "Süre (s)"], renk=LACIVERT)
    A = f"'Temiz Veri'!$A$2:$A${son}"
    C = f"'Temiz Veri'!$C$2:$C${son}"
    J = f"'Temiz Veri'!$J$2:$J${son}"
    for kod, ad in DURUM_ADLARI.items():
        r = 5 + kod
        _hucre(ws, r, 1, kod, hizala="center")
        _hucre(ws, r, 2, ad)
        _hucre(ws, r, 3, f"=IFERROR(INDEX({A},MATCH({kod},{J},0)),\"-\")", fmt="0.0", hizala="center")
        _hucre(ws, r, 4, f"=IFERROR(INDEX({C},MATCH({kod},{J},0)),\"-\")", fmt="#,##0.0", hizala="center")
        if kod < 7:
            sure = f"=IFERROR(C{r + 1}-C{r},\"-\")"
        else:
            sure = f"=IFERROR(MAX({A})-C{r}+0.1,\"-\")"
        _hucre(ws, r, 5, sure, fmt="0.0", hizala="center")
    # Rampada bekleme negatif zamanlıdır; süresi kalkışa kadar geçen süredir
    for sutun, g in zip("ABCDE", [8, 24, 16, 22, 12]):
        ws.column_dimensions[sutun].width = g
    return ws


# ---------------------------------------------------------------------------
# Sayfa: Özet (Dashboard)
# ---------------------------------------------------------------------------
def _ozet_sayfasi(ws, son, vk_son, metrikler, sonuc, bilgi):
    ws.sheet_view.showGridLines = False
    for sutun, g in zip("ABCDEFGHIJKLMN", [2, 34, 14, 10, 16, 16, 2, 12, 12, 12, 12, 12, 12, 12]):
        ws.column_dimensions[sutun].width = g

    # Başlık bandı
    ws.merge_cells("B1:N1")
    ws.merge_cells("B2:N2")
    ws["B1"] = "UÇUŞRAPOR  |  Roket Uçuş Test Raporu"
    ws["B2"] = f"Kaynak: {bilgi['kaynak']}   •   Rapor tarihi: {bilgi['tarih']}   •   İşlem süresi: {bilgi['sure']:.2f} s"
    for hucre, font in (("B1", BASLIK_FONT), ("B2", ALT_BASLIK_FONT)):
        ws[hucre].font = font
        ws[hucre].alignment = Alignment(horizontal="left", vertical="center", indent=1)
    for r in (1, 2):
        for c in range(2, 15):
            ws.cell(row=r, column=c).fill = PatternFill("solid", fgColor=LACIVERT)
    ws.row_dimensions[1].height = 34
    ws.row_dimensions[2].height = 20

    if bilgi.get("simule"):
        ws.merge_cells("B3:N3")
        ws["B3"] = ("ℹ Bu rapor AKANA uçuş profiline dayalı SİMÜLE veri ile üretilmiştir; "
                    "sistem gerçek aviyonik log formatıyla çalışacak şekilde tasarlanmıştır.")
        ws["B3"].font = NOT_FONT

    # --- Uçuş metrikleri ---
    ws["B5"] = "Uçuş Metrikleri"
    ws["B5"].font = BOLUM_FONT
    _tablo_basligi(ws, 6, 2, ["Metrik", "Değer", "Birim", "Python doğrulama", "Kontrol"])

    A = f"'Temiz Veri'!$A$2:$A${son}"
    C = f"'Temiz Veri'!$C$2:$C${son}"
    H = f"'Temiz Veri'!$H$2:$H${son}"
    J = f"'Temiz Veri'!$J$2:$J${son}"
    kalkis = f"INDEX({A},MATCH(1,{J},0))"

    def egim(aralik):
        a, b = aralik[0] + 2, aralik[1] + 2  # DataFrame indeksi -> Excel satırı
        return f"=-SLOPE('Temiz Veri'!$C${a}:$C${b},'Temiz Veri'!$A${a}:$A${b})"

    satirlar = [
        ("Maksimum irtifa (apogee)", f"=MAX({C})", "m", "maks_irtifa_m", "#,##0.0"),
        ("Apogee zamanı", f"=INDEX({A},MATCH(MAX({C}),{C},0))", "s", "apogee_zamani_s", "0.0"),
        ("Maksimum toplam ivme", f"=MAX({H})", "g", "maks_ivme_g", "0.00"),
        ("Maksimum ivme zamanı", f"=INDEX({A},MATCH(MAX({H}),{H},0))", "s", "maks_ivme_zamani_s", "0.0"),
        ("Motor yanma süresi", f"=INDEX({A},MATCH(3,{J},0))-{kalkis}", "s", "yanma_suresi_s", "0.0"),
        ("Sürüklenme paraşütü açılışı", f"=INDEX({A},MATCH(5,{J},0))", "s", "suruklenme_parasutu_s", "0.0"),
        ("Ana paraşüt açılışı", f"=INDEX({A},MATCH(6,{J},0))", "s", "ana_parasut_s", "0.0"),
        ("Ana paraşüt açılış irtifası", f"=INDEX({C},MATCH(6,{J},0))", "m", "ana_parasut_irtifa_m", "#,##0.0"),
        ("Toplam uçuş süresi", f"=INDEX({A},MATCH(7,{J},0))-{kalkis}", "s", "ucus_suresi_s", "0.0"),
        ("İniş hızı – sürüklenme paraşütü", egim(metrikler["_suruklenme_aralik"]), "m/s",
         "suruklenme_inis_hizi_ms", "0.0"),
        ("İniş hızı – ana paraşüt", egim(metrikler["_ana_aralik"]), "m/s", "ana_parasut_inis_hizi_ms", "0.0"),
    ]
    for i, (ad, formul, birim, anahtar, fmt) in enumerate(satirlar):
        r = 7 + i
        dolgu = GRI if i % 2 else None
        _hucre(ws, r, 2, ad, font=KALIN, fill=dolgu)
        _hucre(ws, r, 3, formul, fmt=fmt, hizala="right", fill=dolgu, font=Font(name=YAZI, size=11, bold=True, color=LACIVERT))
        _hucre(ws, r, 4, birim, hizala="center", fill=dolgu)
        _hucre(ws, r, 5, round(metrikler[anahtar], 4), fmt=fmt, hizala="right", fill=dolgu)
        _hucre(ws, r, 6, f'=IF(ABS(C{r}-E{r})<0.05,"✓ Tutarlı","✗ Fark var")', hizala="center", fill=dolgu)
    m_son = 7 + len(satirlar) - 1
    ws.conditional_formatting.add(
        f"F7:F{m_son}", FormulaRule(formula=[f'LEFT(F7,1)="✓"'], fill=PatternFill("solid", fgColor=YESIL),
                                    font=Font(name=YAZI, color="375623", bold=True)))
    ws.conditional_formatting.add(
        f"F7:F{m_son}", FormulaRule(formula=[f'LEFT(F7,1)="✗"'], fill=PatternFill("solid", fgColor=KIRMIZI),
                                    font=Font(name=YAZI, color="C00000", bold=True)))
    ws.cell(row=m_son + 1, column=2,
            value="Değer sütunu Excel formülleriyle, 'Python doğrulama' sütunu UçuşRapor betiğiyle bağımsız hesaplanır.").font = NOT_FONT

    # --- Veri kalitesi özeti ---
    vk = m_son + 3
    ws.cell(row=vk, column=2, value="Veri Kalitesi Özeti").font = BOLUM_FONT
    _tablo_basligi(ws, vk + 1, 2, ["Gösterge", "Değer", "Yapılan işlem", "", ""])
    ws.merge_cells(start_row=vk + 1, start_column=4, end_row=vk + 1, end_column=6)
    TIP = f"'Veri Kalitesi'!$C$5:$C${vk_son}"
    vk_satirlar = [
        ("Ham log satır sayısı", sonuc.ham_satir_sayisi, "Dosyadan okunan", "0"),
        ("Temiz veri satır sayısı", f"=COUNT({A})", "Rapora giren", "0"),
        ("Duplike satır", f'=COUNTIF({TIP},"DUPLIKE_SATIR")', "Silindi", "0"),
        ("Geçersiz FSM durum kodu", f'=COUNTIF({TIP},"GECERSIZ_DURUM")', "Silindi", "0"),
        ("Eksik değer", f'=COUNTIF({TIP},"EKSIK_DEGER")', "İnterpolasyonla dolduruldu", "0"),
        ("Sensör sıçraması (aykırı değer)", f'=COUNTIF({TIP},"SENSOR_SICRAMASI")', "Düzeltildi", "0"),
        ("Kullanılabilir veri oranı", f"=C{vk + 3}/C{vk + 2}", "Temiz / ham satır", "0.0%"),
    ]
    for i, (ad, deger, islem, fmt) in enumerate(vk_satirlar):
        r = vk + 2 + i
        dolgu = GRI if i % 2 else None
        _hucre(ws, r, 2, ad, font=KALIN, fill=dolgu)
        _hucre(ws, r, 3, deger, fmt=fmt, hizala="right", fill=dolgu)
        _hucre(ws, r, 4, islem, fill=dolgu)
        _hucre(ws, r, 5, None, fill=dolgu)
        _hucre(ws, r, 6, None, fill=dolgu)
        ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=6)
    vk_grafik_ilk, vk_grafik_son = vk + 4, vk + 7  # sorun tipleri (grafik için)

    # --- Grafikler ---
    x = Reference(ws.parent["Temiz Veri"], min_col=1, min_row=2, max_row=son)
    x_maks = (int(metrikler["ucus_suresi_s"] // 25) + 1) * 25

    def cizgi_grafigi(baslik, y_baslik, sutun, renk):
        g = ScatterChart()
        g.title = baslik
        g.style = 13
        g.x_axis.title = "Kalkıştan itibaren süre (s)"
        g.y_axis.title = y_baslik
        g.height, g.width = 7.5, 17
        g.legend = None
        y = Reference(ws.parent["Temiz Veri"], min_col=sutun, min_row=1, max_row=son)
        s = Series(y, x, title_from_data=True)
        s.marker.symbol = "none"
        s.graphicalProperties.line.solidFill = renk
        s.graphicalProperties.line.width = 19050
        s.smooth = False
        g.series.append(s)
        g.x_axis.delete = False
        g.y_axis.delete = False
        g.x_axis.scaling.min = 0
        g.x_axis.scaling.max = x_maks
        g.x_axis.majorUnit = 25
        g.x_axis.number_format = "0"
        g.y_axis.number_format = "#,##0"
        g.y_axis.majorGridlines = g.y_axis.majorGridlines
        return g

    ws.cell(row=5, column=8, value="Uçuş Profili").font = BOLUM_FONT
    ws.add_chart(cizgi_grafigi("İrtifa – Zaman", "İrtifa (m)", 3, MAVI), "H6")
    ws.add_chart(cizgi_grafigi("Toplam İvme – Zaman", "İvme (g)", 8, "C00000"), "H22")

    bar = BarChart()
    bar.type = "bar"
    bar.style = 10
    bar.title = "Tespit Edilen Veri Sorunları"
    bar.height, bar.width = 6.5, 12
    bar.legend = None
    veriler = Reference(ws, min_col=3, min_row=vk_grafik_ilk, max_row=vk_grafik_son)
    kategoriler = Reference(ws, min_col=2, min_row=vk_grafik_ilk, max_row=vk_grafik_son)
    bar.add_data(veriler, titles_from_data=False)
    bar.set_categories(kategoriler)
    bar.series[0].graphicalProperties.solidFill = MAVI
    bar.x_axis.delete = False
    bar.y_axis.delete = False
    ws.add_chart(bar, f"B{vk + 10}")

    ws.freeze_panes = "A3"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def excel_raporu_olustur(df, sonuc, metrikler, cikti_yolu, bilgi):
    """Tüm sayfaları oluşturur ve Excel dosyasını kaydeder."""
    wb = Workbook()
    ozet = wb.active
    ozet.title = "Özet"

    _, son = _temiz_veri_sayfasi(wb, df)
    _, vk_son = _veri_kalitesi_sayfasi(wb, sonuc.kayitlar)
    _ucus_olaylari_sayfasi(wb, son)
    _ozet_sayfasi(ozet, son, vk_son, metrikler, sonuc, bilgi)

    ozet.sheet_properties.tabColor = LACIVERT
    wb["Temiz Veri"].sheet_properties.tabColor = MAVI
    wb["Veri Kalitesi"].sheet_properties.tabColor = "C00000"
    wb["Uçuş Olayları"].sheet_properties.tabColor = "548235"
    wb.active = 0
    wb.save(cikti_yolu)
    return cikti_yolu


def rapor_bilgisi(kaynak, sure, simule):
    return {"kaynak": kaynak, "tarih": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "sure": sure, "simule": simule}
