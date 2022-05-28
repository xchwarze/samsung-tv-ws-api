import sys
import logging

sys.path.append('../')

from samsungtvws import SamsungTVWS

# Increase debug level
logging.basicConfig(level=logging.INFO)

# Normal constructor
tv = SamsungTVWS('192.168.xxx.xxx')

# Set all mats to this type
target_matte_type = 'none'

# Is art mode supported?
if not tv.art().supported():
    logging.error('Art mode not supported')
    sys.exit(1)

# List available mats for displaying art
matte_types = [matte_type for elem in tv.art().get_matte_list() for matte_type in elem.values()]
if target_matte_type not in matte_types:
    logging.error('Invalid matte type: {}'.format(target_matte_type))
    sys.exit(1)

# List the art available on the device
available_art = tv.art().available()

for art in available_art:
    if art['matte_id'] != target_matte_type:
        logging.info("Setting matte to %s for %s", target_matte_type, art['content_id'])
        tv.art().change_matte(art['content_id'], target_matte_type)
