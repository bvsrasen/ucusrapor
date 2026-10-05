"""Testler gerçek uçuş kayıtlarıyla (veri/ucuslar) çalışıyor."""
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ucusrapor.algoritmalar import ALGORITMALAR, ONERILEN, ncsu_karari
from ucusrapor.degerlendirme import ucusu_degerlendir
from ucusrapor.okuma import HZ, oku_kayit, yeniden_ornekle
from ucusrapor.olaylar import olaylar
from ucusrapor.rapor import excel_yaz

KOK = Path(__file__).resolve().parent.parent
BILGI = pd.read_csv(KOK / "veri" / "ucuslar.csv")


def ucus(ad):
    return pd.read_csv(KOK / "veri" / "ucuslar" / f"{ad}.csv")


def test_tablolar_50_hz_ve_eksiksiz():
    for ad in BILGI["ucus"]:
        d = ucus(ad)
        assert np.allclose(np.diff(d["t_s"]), 1 / HZ), ad
        assert not d[["t_s", "basinc_pa", "ivme_g"]].isna().any().any(), ad
        # rampada eksenel ivme 1 g
        assert abs(d["ivme_g"].iloc[:100].median() - 1.0) < 0.05, ad


def test_referans_tepe_bildirilen_degerle_uyumlu():
    for r in BILGI.itertuples():
        o = olaylar(ucus(r.ucus))
        assert abs(o["tepe_m"] - r.bildirilen_tepe_m) < 6.0, r.ucus
        assert 1.0 < o["motor_bitisi_s"] - o["kalkis_s"] < 3.5, r.ucus


def test_basinc_darbesinde_basit_kural_erken_aciyor():
    # jackpot_launch_2: hava frenleri açılınca basınç sıçradı
    d = ucus("jackpot_launch_2")
    tepe = olaylar(d)["tepe_s"]
    assert ALGORITMALAR["Basit barometrik"](d) < tepe - 10
    assert 0 < ALGORITMALAR[ONERILEN](d) - tepe < 2


def test_onerilen_butun_ucuslarda_zamaninda():
    for ad in BILGI["ucus"]:
        satirlar, _ = ucusu_degerlendir(ad, ucus(ad))
        onerilen = next(s for s in satirlar if s["algoritma"] == ONERILEN)
        assert onerilen["durum"] == "zamanında", ad


def test_ncsu_karari_motordan_onceki_f_yi_saymiyor():
    t = np.arange(6) * 0.1
    assert ncsu_karari(t, ["F", "S", "S", "M", "C", "F"]) == pytest.approx(0.5)
    assert ncsu_karari(t, ["S"] * 6) is None


def test_kendi_kaydi_okuma(tmp_path):
    yol = tmp_path / "kayit.csv"
    yol.write_text("t_s,basinc_pa\n0,101000\n")
    with pytest.raises(ValueError):
        oku_kayit(yol)
    yol.write_text("t_s,basinc_pa,ivme_g\n0.03,101000,1\n,101002,1\n0.0,101001,1\n")
    assert list(oku_kayit(yol)["t_s"]) == [0.0, 0.03]


def test_yeniden_ornekleme_gelecegi_kullanmiyor():
    d = pd.DataFrame({"t_s": [0.0, 0.03, 0.05], "basinc_pa": [1.0, 2.0, 3.0], "ivme_g": [1.0, 1.0, 1.0]})
    y = yeniden_ornekle(d)
    # 0,02 s'de elimizde 0,00'daki örnek var, 0,03'teki henüz gelmedi;
    # 0,04 s'de en son gelen 0,03'teki örnek
    assert list(y["t_s"]) == [0.0, 0.02, 0.04]
    assert list(y["basinc_pa"]) == [1.0, 1.0, 2.0]
    # Kayıt sıfırdan başlamıyorsa çizelge kaydın ilk anından başlamalı
    d["t_s"] += 100.0
    assert list(yeniden_ornekle(d)["t_s"]) == [100.0, 100.02, 100.04]


def test_excel_raporu(tmp_path):
    satirlar, _ = ucusu_degerlendir("genesis_launch_1", ucus("genesis_launch_1"))
    tablo = pd.DataFrame(satirlar)
    excel_yaz(tmp_path / "r.xlsx", tablo.head(1), tablo, BILGI)
    assert (tmp_path / "r.xlsx").stat().st_size > 0


@pytest.mark.skipif(shutil.which("make") is None or shutil.which("gcc") is None, reason="C derleyicisi yok")
def test_c_python_ile_ayni():
    subprocess.run(["make", "-s", "-C", str(KOK / "c")], check=True)
    for ad in BILGI["ucus"]:
        yol = KOK / "veri" / "ucuslar" / f"{ad}.csv"
        with open(yol) as f:
            c = subprocess.run([str(KOK / "c" / "build" / "tepe_cli")], stdin=f, capture_output=True,
                               text=True, check=True).stdout.strip()
        assert float(c) == pytest.approx(ALGORITMALAR[ONERILEN](ucus(ad)), abs=1e-6), ad


@pytest.mark.skipif(shutil.which("make") is None or shutil.which("gcc") is None, reason="C derleyicisi yok")
def test_bozuk_olcum_atlaniyor():
    # Uçuşun ortasında bir basınç ölçümü NaN olsa da paraşüt yine açılmalı;
    # sonuç o satır hiç yokmuş gibi olmalı
    subprocess.run(["make", "-s", "-C", str(KOK / "c")], check=True)
    satirlar = (KOK / "veri" / "ucuslar" / "jackpot_launch_2.csv").read_text().splitlines()
    alanlar = satirlar[800].split(",")
    alanlar[1] = "nan"
    bozuk = satirlar[:800] + [",".join(alanlar)] + satirlar[801:]
    c = subprocess.run([str(KOK / "c" / "build" / "tepe_cli")], input="\n".join(bozuk) + "\n",
                       capture_output=True, text=True, check=True).stdout.strip()
    eksik = ucus("jackpot_launch_2").drop(index=799)
    assert float(c) == pytest.approx(ALGORITMALAR[ONERILEN](eksik), abs=1e-6)
    d = ucus("jackpot_launch_2")
    d.loc[799, "basinc_pa"] = np.nan
    assert ALGORITMALAR[ONERILEN](d) == pytest.approx(float(c), abs=1e-6)
