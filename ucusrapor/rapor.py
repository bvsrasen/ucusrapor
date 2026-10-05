"""Sonuçları Excel dosyasına ve grafiklere yazar."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from ucusrapor.degerlendirme import ERKEN_S, GEC_S
from ucusrapor.okuma import irtifa

KALIN = Font(name="Calibri", size=10, bold=True)
NORMAL = Font(name="Calibri", size=10)
BASLIK = Font(name="Calibri", size=13, bold=True)
GRI = PatternFill("solid", fgColor="E7E6E6")
RENK = {"zamanında": "E2EFDA", "erken": "F8CBAD", "geç": "FFE699", "açılmadı": "D9D9D9"}
ince = Side(style="thin", color="BFBFBF")
CERCEVE = Border(left=ince, right=ince, top=ince, bottom=ince)

MAVI, KIRMIZI, YESIL = "#2a78d6", "#d64541", "#1b9e5a"


def _sayfa(wb, ad, baslik, df, ilk=False):
    ws = wb.active if ilk else wb.create_sheet()
    ws.title = ad
    ws.cell(row=1, column=1, value=baslik).font = BASLIK
    for j, b in enumerate(df.columns, start=1):
        c = ws.cell(row=3, column=j, value=b)
        c.font, c.fill, c.border = KALIN, GRI, CERCEVE
        c.alignment = Alignment(wrap_text=True, vertical="center")
        # Sütun en uzun değer sığacak kadar geniş, ama çok uzun notlar için sınırlı
        degerler = [round(x, 2) if isinstance(x, float) else x for x in df.iloc[:, j - 1]]
        uzunluk = max(len(str(x)) for x in [b] + degerler)
        ws.column_dimensions[get_column_letter(j)].width = max(10, min(60, uzunluk + 2))
    for i, satir in enumerate(df.itertuples(index=False), start=4):
        for j, deger in enumerate(satir, start=1):
            if isinstance(deger, float) and np.isnan(deger):
                deger = None
            c = ws.cell(row=i, column=j, value=round(deger, 2) if isinstance(deger, float) else deger)
            c.font, c.border = NORMAL, CERCEVE
            if df.columns[j - 1] == "durum" and deger in RENK:
                c.fill = PatternFill("solid", fgColor=RENK[deger])
    ws.freeze_panes = "A4"


def excel_yaz(yol, ozet, tablo, ucuslar):
    wb = Workbook()
    _sayfa(wb, "Özet", "Algoritmaların 12 gerçek uçuştaki sonucu", ozet, ilk=True)
    _sayfa(wb, "Uçuş uçuş", f"Süreler kalkıştan itibaren. Gecikme: paraşüt komutu - gerçek tepe anı. "
           f"Zamanında: -{ERKEN_S:g} s ile +{GEC_S:g} s arası.", tablo)
    _sayfa(wb, "Uçuşlar", "Kullanılan uçuşlar (NCSU High-Powered Rocketry Club, AirbrakesV2)", ucuslar)
    wb.save(yol)


def ucus_grafigi(yol, ad, d, o, kararlar):
    """Bir uçuşun irtifası, gerçek tepe noktası ve algoritmaların karar anları."""
    t = d["t_s"].to_numpy() - o["kalkis_s"]
    k = np.searchsorted(t, 0.0)
    h = irtifa(d["basinc_pa"], d["basinc_pa"].iloc[:k].mean())
    son = o["tepe_s"] - o["kalkis_s"] + 8
    m = (t > -1) & (t < son)

    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(t[m], h[m], color=MAVI, lw=1, label="basınçtan irtifa (ham)")
    ax.axvline(o["tepe_s"] - o["kalkis_s"], color="black", ls="--", lw=1, label="gerçek tepe noktası")
    if o["motor_bitisi_s"] is not None:
        ax.axvline(o["motor_bitisi_s"] - o["kalkis_s"], color="black", ls=":", lw=1.2, zorder=5, label="motor bitişi")
    for (isim, an), renk in zip(kararlar.items(), [KIRMIZI, YESIL, "#9467bd", "#ff7f0e"]):
        if an is not None and an - o["kalkis_s"] < son:
            ax.axvline(an - o["kalkis_s"], color=renk, lw=2, label=f"{isim}: {an - o['tepe_s']:+.1f} s")
    ax.set_xlabel("kalkıştan itibaren süre (s)")
    ax.set_ylabel("irtifa (m)")
    ax.set_title(ad, loc="left", fontsize=10)
    ax.grid(alpha=0.3, lw=0.5)
    for k_ in ("top", "right"):
        ax.spines[k_].set_visible(False)
    ax.legend(fontsize=8, frameon=False, loc="lower center")
    fig.tight_layout()
    fig.savefig(yol, dpi=120)
    plt.close(fig)


def gecikme_grafigi(yol, tablo):
    """Her algoritma için uçuş başına gecikme; yeşil bant zamanında aralığı."""
    isimler = list(dict.fromkeys(tablo["algoritma"]))[::-1]
    fig, ax = plt.subplots(figsize=(8, 0.55 * len(isimler) + 1.2))
    ax.axvspan(-ERKEN_S, GEC_S, color=YESIL, alpha=0.12, lw=0)
    ax.axvline(0, color="black", lw=0.8)
    for y, isim in enumerate(isimler):
        g = tablo[tablo["algoritma"] == isim]["gecikme_s"].dropna().to_numpy()
        renk = [YESIL if -ERKEN_S <= x <= GEC_S else KIRMIZI for x in g]
        ax.scatter(g, np.full(len(g), y) + np.linspace(-0.15, 0.15, len(g)), c=renk, s=22, zorder=3)
    ax.set_yticks(range(len(isimler)))
    ax.set_yticklabels(isimler, fontsize=9)
    ax.set_xlabel("paraşüt komutu - gerçek tepe anı (s); negatif = tepeden önce")
    ax.grid(axis="x", alpha=0.3, lw=0.5)
    for k_ in ("top", "right"):
        ax.spines[k_].set_visible(False)
    fig.tight_layout()
    fig.savefig(yol, dpi=120)
    plt.close(fig)
