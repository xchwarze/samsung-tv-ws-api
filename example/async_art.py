#!/usr/bin/env python3

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

async def main():
    args = parseargs()
    tv = SamsungTVAsyncArt(host=args.ip, port=8002)
    await tv.start_listening()
    
    #is art mode supported
    supported = await tv.supported()
    logging.info('art mode is supported: {}'.format(supported))
    
    if supported:
        try:
            #is tv on
            tv_on = await tv.on()
            logging.info('tv is on: {}'.format(tv_on))
            
            #is art mode on
            #art_mode = await tv.get_artmode()
            art_mode = tv.art_mode
            logging.info('art mode is on: {}'.format(art_mode))
            
            #check both with one call
            logging.info('tv is on and in art mode: {}'.format(await tv.is_artmode()))
            
            #get api version 4.3.4.0 is new api, 2.03 is old api
            api_version = await tv.get_api_version()
            logging.info('api version: {}'.format(api_version))
            
            # Request all art
            info = await tv.available()
            logging.info('artwork available on tv: {}'.format(info))

            # Request current art
            info = await tv.get_current()
            logging.info('current artwork: {}'.format(info))
            content_id = info['content_id']                         #example to get current content_id
            
            #get thumbnail for current artwork
            thumb = b''
            if int(api_version.replace('.','')) < 4000:             #check api version number, and use correct api call
                thumb = await tv.get_thumbnail(content_id)
            else:
                thumbs = await tv.get_thumbnail_list(content_id)    #list of content_id's or single content_id
                if thumbs:                                          #dictionary of content_id (with file type extension) and binary data
                    thumb = list(thumbs.values())[0]
                    content_id = list(thumbs.keys())[0]
            logging.info('got thumbnail for {} binary data length: {}'.format(content_id, len(thumb)))

            # Turn on art mode (FrameTV)
            #await tv.set_artmode('on')
            
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
            
            #monitor armode status
            '''
            while True:
                logging.info('art mode is on: {}'.format(tv.art_mode))
                await asyncio.sleep(5)
            '''
            await asyncio.sleep(15)
        except exceptions.ResponseError as e:
            logging.warning('ERROR: {}'.format(e)) 

    await tv.close()


asyncio.run(main())
