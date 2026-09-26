from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ucusrapor.apogee import basit_barometrik, filtreli_barometrik, zaman_kilitli_barometrik
from ucusrapor.karsilastirma import saat_farkini_bul, ucus_analizi, vakum_testi
from ucusrapor.okuma import oku_ozgun
from ucusrapor.temizleme import temizle

VERI = Path(__file__).resolve().parent.parent / "veri"


def test_bozuk_ve_yarim_satirlar_atlanir(tmp_path):
    f = tmp_path / "log.csv"
    f.write_text("t_ms,basinc_pa,sicaklik_c,ax_g,ay_g,az_g,durum\n"
                 "0,101000,22,0,0,1,0\n40,1010?0,22,0,0,1,0\n80,101001,22,0,0,1,0\n120,1010")
    df, bozuk = oku_ozgun(f)
    assert len(df) == 2
    assert bozuk == [3, 5]


def test_yanlis_baslik_hata_verir(tmp_path):
    f = tmp_path / "log.csv"
    f.write_text("zaman,basinc\n0,101000\n")
    with pytest.raises(ValueError):
        oku_ozgun(f)


def test_kopya_sifir_ve_bosluk_bulunur():
    t = np.arange(0, 2000, 40)
    df = pd.DataFrame({"t_ms": t, "basinc_pa": 101000 + np.random.default_rng(1).normal(0, 3, t.size),
                       "sicaklik_c": 22.0, "ax_g": 0.0, "ay_g": 0.0, "az_g": 1.0, "durum": 0})
    df.loc[10, "basinc_pa"] = 0
    df = df.drop(index=range(20, 26))                       # 6 örnek kayıp
    df = pd.concat([df, df.iloc[[5]]]).reset_index(drop=True)  # kopya satır
    temiz, kayit, _ = temizle(df)
    tipler = [k["tip"] for k in kayit]
    assert tipler.count("KOPYA_SATIR") == 1
    assert tipler.count("SENSOR_OKUMA_HATASI") == 1
    assert tipler.count("KAYIT_BOSLUGU") == 1
    assert temiz["basinc_pa"].gt(100000).all()


def test_saat_farki_bulunur():
    t = np.arange(0, 60, 0.04)
    h = 1500 * np.sin(np.pi * t / 60)
    ozgun = pd.DataFrame({"t_s": t, "irtifa_m": h})
    tt = np.arange(0, 58, 0.05)
    ticari = pd.DataFrame({"zaman_s": tt, "irtifa_m": 1500 * np.sin(np.pi * (tt + 1.3) / 60)})
    assert saat_farkini_bul(ozgun, ticari) == pytest.approx(1.3, abs=0.05)


def test_dalgalanma_basit_algoritmayi_yaniltir_filtre_duzeltir():
    t = np.arange(0, 40, 0.04)
    h = np.where(t < 30, 3000 - 3 * (30 - t) ** 2, 3000 - 60 * (t - 30))  # tepeye yavaşça yaklaşıyor
    h = h + 12 * np.sin(2 * np.pi * 2.3 * t)                # pompa benzeri dalgalanma
    assert basit_barometrik(t, h) < 29                      # erken tetikler
    assert filtreli_barometrik(t, h) == pytest.approx(30, abs=1.0)


def test_vakum_denemeleri_ticari_tutarli():
    ref = pd.read_csv(VERI / "vakum_referans.csv")
    for _, r in ref.iterrows():
        n = int(r["deneme"])
        v = vakum_testi(VERI / f"vakum_{n}_ozgun.csv", VERI / f"vakum_{n}_ticari.csv", r["vana_acilis_s"], n)
        assert v["ozgun_basit_s"] < v["vana_acilis_s"] - 30  # mevcut algoritma çok erken
        assert abs(v["ticari_s"] - v["vana_acilis_s"]) < 1.0
        assert v["saat_farki_s"] == pytest.approx(r["ticari_saat_farki_s"], abs=0.35)


def test_ucusta_transonik_bolge_erken_tetikletir_zaman_kilidi_duzeltir():
    ref = pd.read_csv(VERI / "ucus_referans.csv").iloc[0]
    u = ucus_analizi(VERI / "ucus_ozgun.csv", ref["zemin_basinci_pa"], 20.9, ref["gercek_tepe_s"])
    tablo = u["tablo"].set_index("yontem")["tespit_s"]
    assert tablo["Basit barometrik (mevcut)"] < 8
    assert abs(tablo["Zaman kilitli + filtreli barometrik"] - ref["gercek_tepe_s"]) < 1.5
    assert u["kayip_yuzde"] < 10
