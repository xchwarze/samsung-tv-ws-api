import logging
import sys
from pprint import pprint
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from samsungtvws import SamsungTVWS
from samsungtvws.exceptions import ResponseError, ConnectionFailure

TV_IP = "192.168.x.x"
TIMEOUT = 5

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("art-debug")


def main() -> None:
    tv = SamsungTVWS(TV_IP, timeout=TIMEOUT)

    try:
        art = tv.art()

        log.info("Checking art mode support...")
        supported = art.supported()
        log.info("Supported: %s", supported)
        if not supported:
            return

        log.info("API version:")
        print(art.get_api_version())

        log.info("Current art mode:")
        print(art.get_artmode())

        log.info("Available matte list:")
        mattes = art.get_matte_list()
        pprint(mattes)

        log.info("Available artworks:")
        available = art.available()
        log.info("Art count: %d", len(available))
        if available:
            pprint(available[0])

        log.info("Toggling art mode ON")
        art.set_artmode(True)

        log.info("Toggling art mode OFF")
        art.set_artmode(False)

        if available:
            art_id = available[0]["content_id"]
            log.info("Testing change_matte on %s", art_id)
            art.change_matte(art_id, "none")

        log.info("ALL BASIC ART CALLS OK")

    except ResponseError as e:
        log.error("API error: %s", e)
    except ConnectionFailure as e:
        log.error("Connection failure: %s", e)
    except Exception as e:
        log.exception("Unexpected error")
    finally:
        try:
            tv.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
