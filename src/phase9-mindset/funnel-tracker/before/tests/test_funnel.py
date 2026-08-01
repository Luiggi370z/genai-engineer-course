from src.funnel import Funnel


def test_identifies_top_of_funnel_leak():
    # tons of apps, almost no screens -> resume/targeting is the leak
    f = Funnel(applications=100, screens=3, technicals=2, onsites=1, offers=0)
    assert f.leaking_stage() == "applications->screens"
    assert "resume" in f.prescription()


def test_identifies_onsite_leak():
    # good top of funnel, but onsites never convert
    f = Funnel(applications=100, screens=30, technicals=20, onsites=10, offers=0)
    assert f.leaking_stage() == "onsites->offers"


def test_healthy_funnel_has_no_leak():
    f = Funnel(applications=100, screens=20, technicals=12, onsites=7, offers=3)
    assert f.leaking_stage() is None
    assert "healthy" in f.prescription().lower()
