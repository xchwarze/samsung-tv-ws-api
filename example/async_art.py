#!/usr/bin/env python3
# NOTE old api is 2021 and earlier Frame TV's, new api is 2022+ Frame TV's

import os
import asyncio
import logging
import argparse

from samsungtvws.async_art import SamsungTVAsyncArt
from samsungtvws import exceptions

logging.basicConfig(level=logging.INFO) #or logging.DEBUG to see messages

def parseargs():
    # Add command line argument parsing
    parser = argparse.ArgumentParser(description='Example async art Samsung Frame TV.')
    parser.add_argument('ip', action="store", type=str, default=None, help='ip address of TV (default: %(default)s))')
    return parser.parse_args()
    
async def image_callback(event, response):
    logging.info('CALLBACK: image callback: {}, {}'.format(event, response))

async def main():
    args = parseargs()
    tv = SamsungTVAsyncArt(host=args.ip, port=8002)
    await tv.start_listening()
    
    #is art mode supported
    supported = await tv.supported()
    logging.info('art mode is supported: {}'.format(supported))
    
    if supported:
        try:
            #is tv on (calls tv rest api)
            tv_on = await tv.on()
            logging.info('tv is on: {}'.format(tv_on))
            
            #is art mode on
            #art_mode = await tv.get_artmode()                  #calls websocket command to determine status
            art_mode = tv.art_mode                              #passive, listens for websocket messgages to determine art mode status
            logging.info('art mode is on: {}'.format(art_mode))
            
            #check both with one call (calls tv rest api)
            logging.info('tv is on and in art mode: {}'.format(await tv.is_artmode()))
            
            #get api version 4.3.4.0 is new api, 2.03 is old api
            api_version = await tv.get_api_version()
            logging.info('api version: {}'.format(api_version))
            
            #example callbacks
            tv.set_callback('slideshow_image_changed', image_callback)      #new api
            tv.set_callback('auto_rotation_image_changed', image_callback)  #old api
            tv.set_callback('image_selected', image_callback)
            
            # Request list of all art
            try:
                info = await tv.available()
                #info = await tv.available('MY-C0002')              #gets list of uploaded art, MY-C0004 is favourites
            except AssertionError:
                info='None'
            logging.info('artwork available on tv: {}'.format(info))

            # Request current art
            info = await tv.get_current()
            logging.info('current artwork: {}'.format(info))
            content_id = info['content_id']                         #example to get current content_id
            
            #get thumbnail for current artwork
            try:
                thumb = b''
                if int(api_version.replace('.','')) < 4000:             #check api version number, and use correct api call
                    #thumb = await tv.get_thumbnail(content_id)         #old api, just gets binary data
                    thumbs = await tv.get_thumbnail(content_id, True)   #old api, gets thumbs in same format as new api
                else:
                    thumbs = await tv.get_thumbnail_list(content_id)    #list of content_id's or single content_id
                if thumbs:                                              #dictionary of content_id (with file type extension) and binary data
                    thumb = list(thumbs.values())[0]
                    content_id = list(thumbs.keys())[0]
                logging.info('got thumbnail for {} binary data length: {}'.format(content_id, len(thumb)))
            except asyncio.exceptions.IncompleteReadError as e:
                logging.error('FAILED to get thumbnail for {}: {}'.format(content_id, e))

            # Turn on art mode
            #await tv.set_artmode('on')
            # Turn of art mode (tv ON and playing)
            #await tv.set_artmode('off')
            
            #get slideshow status, try new api, fall back to old
            '''
            try:
                info = await tv.get_slideshow_status()
            except exceptions.ResponseError:
                info = await tv.get_auto_rotation_status()
            logging.info(info)
            '''
            
            #or get slideshow status, old api fails silently on new TV's, but throws AssertionError on older ones
            try:
                info = await tv.get_auto_rotation_status()
            except AssertionError:
                info = await tv.get_slideshow_status()
            logging.info('current slideshow status: {}'.format(info))
            
            
            #upload file
            '''
            filename = "framed_IMG_0181.png"
            content_id = None
            if filename:
                with open(filename, "rb") as f:
                    file_data = f.read()
                file_type = os.path.splitext(filename)[1][1:] 
                content_id = await tv.upload(file_data, file_type=file_type)
                content_id = os.path.splitext(content_id)[0]    #remove file extension if any (eg .jpg)
                logging.info('uploaded {} to tv as {}'.format(filename, content_id))
                
            #delete art on tv
            if content_id:
                await tv.delete_list([content_id])
                logging.info('deleted from tv: {}'.format([content_id]))
            '''
            
            #set favourite.  NOTE on 2022+ TV's you can only set favourites on artstore artwork
            '''
            info = await tv.set_favourite("SAM-S10000925", "off")
            logging.info('current favourite status: {}'.format(info))
            await asyncio.sleep(5)
            info = await tv.set_favourite("SAM-S10000925", "on")
            logging.info('current favourite status: {}'.format(info))
            '''
            
            #get artmode settings (brigtness, colour temperature, sensor settings etc)
            info = await tv.get_artmode_settings('brightness')              #new api
            #info = tv.get_brightness()                                     #old api
            logging.info('current brightness setting: {}'.format(info))
            info = await tv.get_artmode_settings()
            logging.info('current artmode settings: {}'.format(info))
            
            #get rotation (landscape or portrait)
            rot = await tv.get_rotation()
            logging.info('Current Orientation: {} ({})'.format('Landscape' if rot==1 else 'Portrait' if rot==2 else 'Unknown', rot))
            
            #get matte list with color
            '''
            info = await tv.get_matte_list(True)
            logging.info('matte list: {}'.format(info))
            '''
            
            #monitor artmode status
            '''
            while True:
                logging.info('art mode is on: {}'.format(tv.art_mode))
                await asyncio.sleep(5)
            '''
            
            await asyncio.sleep(15)
        except exceptions.ResponseError as e:
            logging.warning('ERROR: {}'.format(e))
        except AssertionError as e:
            logging.warning('no data received: {}'.format(e))

    await tv.close()


asyncio.run(main())
