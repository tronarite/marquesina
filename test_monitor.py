import monitor
from pathlib import Path
from tempfile import TemporaryDirectory


def test_load_config_requires_cine_url(tmp_path=None):
    with TemporaryDirectory() as directory:
        config_path = Path(directory) / "config.json"
        config_path.write_text('{"telegram_bot_token": "x"}', encoding="utf-8")
        original = monitor.CONFIG_PATH
        monitor.CONFIG_PATH = config_path
        try:
            try:
                monitor.load_config()
                assert False, "deberia fallar sin cine_url"
            except SystemExit:
                pass
        finally:
            monitor.CONFIG_PATH = original


def test_parse_movies_flags_advance_sale_and_day_count():
    html = """
    <div class="col-12 col-sm-4 col-lg-2 mb-5"><div class="card"><a href="pelicula.php?id=abc123">
    <div class="position-relative"><img src="imagenes/ventaanticipada.png"></div>
    <img class="card-img-top img-fluid" alt="PELI PREVENTA" src="poster1.jpg"></a>
    <select><option value="dia0">Viernes, 18 de Septiembre del 2026</option></select></div>
    <div class="col-12 col-sm-4 col-lg-2 mb-5"><div class="card"><a href="pelicula.php?id=def456">
    <img class="card-img-top img-fluid" alt="PELI NORMAL" src="poster2.jpg"></a>
    <select>
    <option value="dia0">Sabado, 12 de Septiembre del 2026</option>
    <option value="dia1">Domingo, 13 de Septiembre del 2026</option>
    <option value="dia2">Lunes, 14 de Septiembre del 2026</option>
    <option value="dia3">Martes, 15 de Septiembre del 2026</option>
    </select></div>
    """
    movies = monitor.parse_movies(html)
    by_title = {m["title"]: m for m in movies}
    assert by_title["PELI PREVENTA"]["advance_sale"] is True
    assert by_title["PELI PREVENTA"]["day_count"] == 1
    assert by_title["PELI NORMAL"]["advance_sale"] is False
    assert by_title["PELI NORMAL"]["day_count"] == 4


def test_find_closing_soon_ignores_a_catalog_wide_batch_stall():
    # Regresion: CineCiudad publica las sesiones por lotes. Cuando el lote
    # no se actualiza, TODA la cartelera comparte la misma ultima fecha
    # visible, cercana a hoy. Eso no significa que todas terminen: nadie
    # deberia avisarse porque nadie se queda corta frente al resto.
    import datetime

    soon = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    movies = [
        {"title": "A", "last_show_date": soon, "advance_sale": False},
        {"title": "B", "last_show_date": soon, "advance_sale": False},
        {"title": "C", "last_show_date": soon, "advance_sale": False},
    ]
    assert monitor.find_closing_soon(movies, 3) == []


def test_find_closing_soon_flags_the_movie_that_falls_behind_the_pack():
    import datetime

    ceiling = (datetime.date.today() + datetime.timedelta(days=8)).isoformat()
    soon = (datetime.date.today() + datetime.timedelta(days=2)).isoformat()
    movies = [
        {"title": "SIGUE 1", "last_show_date": ceiling, "advance_sale": False},
        {"title": "SIGUE 2", "last_show_date": ceiling, "advance_sale": False},
        {"title": "SE VA", "last_show_date": soon, "advance_sale": False},
    ]
    result = monitor.find_closing_soon(movies, 3)
    assert [m["title"] for m in result] == ["SE VA"]


def test_find_closing_soon_waits_until_within_the_threshold():
    import datetime

    ceiling = (datetime.date.today() + datetime.timedelta(days=20)).isoformat()
    far = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
    movies = [
        {"title": "SIGUE", "last_show_date": ceiling, "advance_sale": False},
        {"title": "TERMINA LEJOS", "last_show_date": far, "advance_sale": False},
    ]
    assert monitor.find_closing_soon(movies, 3) == []


def test_find_closing_soon_ignores_advance_sale_movies():
    import datetime

    ceiling = (datetime.date.today() + datetime.timedelta(days=8)).isoformat()
    soon = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    movies = [
        {"title": "SIGUE", "last_show_date": ceiling, "advance_sale": False},
        {"title": "PREVENTA", "last_show_date": soon, "advance_sale": True},
    ]
    assert monitor.find_closing_soon(movies, 3) == []


def test_movies_now_showing_detects_presale_transition():
    previous_movies = {
        "DUNE": {"title": "DUNE", "advance_sale": True},
        "SPIDER-MAN": {"title": "SPIDER-MAN", "advance_sale": False},
    }
    movies = [
        {"title": "DUNE", "advance_sale": False},
        {"title": "SPIDER-MAN", "advance_sale": False},
        {"title": "PELI NUEVA", "advance_sale": False},
    ]
    result = monitor.movies_now_showing(movies, previous_movies)
    assert [m["title"] for m in result] == ["DUNE"]


def test_subscribers_roundtrip():
    original = monitor.SUBSCRIBERS_PATH
    with TemporaryDirectory() as directory:
        monitor.SUBSCRIBERS_PATH = Path(directory) / "subscribers.json"
        assert monitor.load_subscribers() == []
        assert monitor.add_subscriber(123) is True
        assert monitor.add_subscriber(123) is False
        assert monitor.load_subscribers() == ["123"]
        assert monitor.remove_subscriber(123) is True
        assert monitor.load_subscribers() == []
    monitor.SUBSCRIBERS_PATH = original


if __name__ == "__main__":
    test_load_config_requires_cine_url()
    test_parse_movies_flags_advance_sale_and_day_count()
    test_find_closing_soon_ignores_a_catalog_wide_batch_stall()
    test_find_closing_soon_flags_the_movie_that_falls_behind_the_pack()
    test_find_closing_soon_waits_until_within_the_threshold()
    test_find_closing_soon_ignores_advance_sale_movies()
    test_movies_now_showing_detects_presale_transition()
    test_subscribers_roundtrip()
    print("ok")
