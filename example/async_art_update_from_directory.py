#!/usr/bin/env python3
# fully async example program to monitor a folder and upload/display on Frame TV

import sys
import logging
import os
import random
import json
import asyncio
import time
import argparse

from samsungtvws.async_art import SamsungTVAsyncArt

SIGINT = 2
SIGTERM = 15

logging.basicConfig(level=logging.INFO)


def parseargs():
    # Add command line argument parsing
    parser = argparse.ArgumentParser(description='Async Upload images to Samsung TV.')
    parser.add_argument('ip', action="store", type=str, default=None, help='ip address of TV (default: %(default)s))')
    parser.add_argument('--folder', action="store", type=str, default="./images", help='folder to load images from (default: %(default)s))')
    parser.add_argument('--update', action="store", type=int, default=0, help='random update period (mins) 0=off (default: %(default)s))')
    parser.add_argument('-F','--favourite', action='store_true', default=False, help='include favourites in rotation (default: %(default)s))')
    parser.add_argument('-D','--debug', action='store_true', default=False, help='Debug mode (default: %(default)s))')
    return parser.parse_args()
    
class monitor_and_display:
    
    def __init__(self, ip, folder, period=5, random_update=1440, include_fav=False):
        self.log = logging.getLogger('Main.'+__class__.__name__)
        self.debug = self.log.getEffectiveLevel() <= logging.DEBUG
        self.ip = ip
        self.folder = folder
        self.period = period
        self.random_update = random_update*60   #minutes
        self.include_fav = include_fav
        self.upload_list_path = './uploaded_files.json'
        self.uploaded_files = {}
        self.fav = []
        self._exit = False
        self.start = time.time()
        self.files_changed = False
        self.tv = SamsungTVAsyncArt(host=self.ip, port=8002)
        try:
            #doesn't work in Windows
            asyncio.get_running_loop().add_signal_handler(SIGINT, self.close)
            asyncio.get_running_loop().add_signal_handler(SIGTERM, self.close)
        except Exception:
            pass
        
    async def start_monitoring(self):
        await self.tv.start_listening()
        await self.select_artwork()
        
    def close(self):
        self.log.info('SIGINT/SIGTERM received, exiting')
        os._exit(1)
        
    async def do_random_update(self):
        if self.random_update > 0 and len(self.uploaded_files.keys()) > 1 and time.time() - self.start > self.random_update:
            self.log.info('doing random update, after {} minutes'.format(self.random_update//60))
            if self.include_fav:
                self.log.info('updating favourites')
                self.fav = await self.tv.available('MY-C0004')
            self.files_changed = True
   
    def read_upload_list(self):
        if os.path.isfile(self.upload_list_path):
            with open(self.upload_list_path, 'r') as f:
                uploaded_files = json.load(f)
        else:
            uploaded_files = {}
        return uploaded_files
        
    def write_upload_list(self):
        with open(self.upload_list_path, 'w') as f:
            json.dump(self.uploaded_files, f)
            
    def read_file(self, filename):
        try:
            with open(filename, 'rb') as f:
                file_data = f.read()
            file_type = os.path.splitext(filename)[1][1:] 
            return file_data, file_type
        except Exception as e:
            self.log.error('error reading file: {}, {}'.format(filename, e))
        return None, None
        
    async def upload_files(self, filenames):
        for filename in filenames:
            path = os.path.join(self.folder, filename)
            file_data, file_type = self.read_file(path)
            if file_data and self.tv.art_mode:
                self.log.info('uploading : {} to tv'.format(filename))
                self.uploaded_files[filename] = {'content_id': await self.tv.upload(file_data, file_type=file_type), 'modified': self.get_last_updated(filename)}
                self.log.info('uploaded : {} to tv as {}'.format(filename, self.uploaded_files[filename]['content_id']))
                self.write_upload_list()
            
    async def delete_files_from_tv(self, files):
        if self.tv.art_mode:
            self.log.info('removing files from tv : {}'.format(files))
            await self.tv.delete_list(files)
            self.uploaded_files = {k:v for k, v in self.uploaded_files.items() if v.get('content_id') is not None and v.get('content_id') not in files}
            self.write_upload_list()
        
    def get_last_updated(self, filename):
        return os.path.getmtime(os.path.join(self.folder, filename))
        
    async def remove_files(self, files):
        TV_files = [f['content_id'] for f in await self.tv.available('MY-C0002')]
        files_removed = [v.get('content_id') for k, v in self.uploaded_files.items() if (v.get('content_id') is not None and k not in files)]
        #delete images from tv
        if files_removed:
            await self.delete_files_from_tv(files_removed)
            self.files_changed = True
            
    async def add_files(self, files):
        new_files = [f for f in files if f not in self.uploaded_files.keys()]
        #upload new files
        if new_files:
            self.log.info('adding files to tv : {}'.format(new_files))
            #wait for files to arrive
            await asyncio.sleep(5 * len(new_files))
            await self.upload_files(new_files)
            self.files_changed = True
            
    async def update_files(self, files):
        modified_files = [f for f in files if f in self.uploaded_files.keys() and self.uploaded_files.get(f, {}).get('modified') != self.get_last_updated(f)]
        #delete old file and upload new:
        if modified_files:
            self.log.info('updating files on tv : {}'.format(modified_files))
            #wait for files to arrive
            await asyncio.sleep(5 * len(modified_files))
            files_to_delete = [v.get('content_id') for k, v in self.uploaded_files.items() if (k in modified_files and v.get('content_id') is not None)]
            await self.delete_files_from_tv(files_to_delete)
            await self.upload_files(modified_files)
            self.files_changed = True 
    
    async def monitor_dir(self):
        while not self._exit:
            try:
                if not os.path.exists(self.folder):
                    self.log.warning('folder {} does not exist'.format(self.folder))
                elif self.tv.art_mode:
                    self.log.info('checking directory: {}'.format(self.folder))
                    files = [f for f in os.listdir(self.folder) if os.path.isfile(os.path.join(self.folder, f))]
                    #delete images from tv
                    await self.remove_files(files)
                    #upload new files
                    await self.add_files(files)
                    #check for modified files
                    await self.update_files(files)
                    #random update if enabled
                    await self.do_random_update()
                else:
                    self.log.info('artmode or tv is off')
            except Exception as e:
                self.log.warning("error in monitor_dir: {}".format(e))
            await asyncio.sleep(self.period)

    async def select_artwork(self):
        self.uploaded_files = self.read_upload_list()
        asyncio.create_task(self.monitor_dir())
        while not self._exit:
            try:
                if self.files_changed and self.tv.art_mode and self.uploaded_files.keys():
                    self.start = time.time()
                    content_id = random.choice([v['content_id'] for v in self.uploaded_files.values()] + [f['content_id'] for f in self.fav])
                    self.log.info('selecting tv art: content_id: {}'.format(content_id))
                    await self.tv.select_image(content_id)
                    self.files_changed = False
            except Exception as e:
                self.log.warning("error in select_artwork: {}".format(e))
                self.files_changed = False
            await asyncio.sleep(self.period)
            
async def main():
    global log
    log = logging.getLogger('Main')
    args = parseargs()
    if args.debug:
        log.setLevel(logging.DEBUG)
        log.info('Debug mode')
    
    mon = monitor_and_display(args.ip, os.path.normpath(args.folder), period=5, random_update=args.update, include_fav=args.favourite)
    await mon.start_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        os._exit(1)