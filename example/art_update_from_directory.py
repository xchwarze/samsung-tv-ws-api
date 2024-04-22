#!/usr/bin/env python3
# example program to monitor a folder and upload/display on Frame TV

import sys
import logging
import os
import random
import json
import asyncio
import time
import argparse

sys.path.append('../')

from samsungtvws import SamsungTVWS

def parseargs():
    global log
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger('Main')
    # Add command line argument parsing
    parser = argparse.ArgumentParser(description='Upload images to Samsung TV.')
    parser.add_argument('ip', action="store", type=str, default=None, help='ip address of TV (default: %(default)s))')
    parser.add_argument('--folder', action="store", type=str, default="./images", help='folder to load images from (default: %(default)s))')
    parser.add_argument('--update', action="store", type=int, default=0, help='random update period (mins) 0=off (default: %(default)s))')
    parser.add_argument('-D','--debug', action='store_true', default=False, help='Debug mode (default: %(default)s))')
    return parser.parse_args()
    
class monitor_and_display:
    
    def __init__(self, ip, folder, period=5, random_update=1440):
        self.log = logging.getLogger('Main.'+__class__.__name__)
        self.debug = self.log.getEffectiveLevel() <= logging.DEBUG
        self.ip = ip
        self.folder = folder
        self.period = period
        self.random_update = random_update*60   #minutes
        self.upload_list_path = './uploaded_files.json'
        self.uploaded_files = {}
        self._exit = False
        self.art_mode = False
        self.tv_on = False
        self.start = time.time()
        self.files_changed = False
        self.tv = SamsungTVWS(self.ip)
        
    async def start_monitoring(self):
        await self.select_artwork()
        
    def art_mode_on(self):
        try:
            self.tv_on = self.tv.rest_device_info().get('device',{}).get('PowerState', 'off') == 'on'
            self.art_mode = self.tv.art().get_artmode() == 'on' if self.tv_on else False
        except Exception as e:
            self.log.warning('error getting art mode on status: {}'.format(e))
            self.art_mode = False
        return self.art_mode
        
    def do_random_update(self):
        if self.random_update > 0 and len(self.uploaded_files.keys()) > 1 and time.time() - self.start > self.random_update:
            self.log.info('doing random update, after {} minutes'.format(self.random_update//60))
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
        
    def upload_files(self, filenames):
        for filename in filenames:
            path = os.path.join(self.folder, filename)
            file_data, file_type = self.read_file(path)
            if file_data and self.art_mode_on():
                self.log.info('uploading : {} to tv'.format(filename))
                self.uploaded_files[filename] = {'content_id': self.tv.art().upload(file_data, file_type=file_type), 'modified': self.get_last_updated(filename)}
                self.log.info('uploaded : {} to tv as {}'.format(filename, self.uploaded_files[filename]['content_id']))
                self.write_upload_list()
            
    def delete_files_from_tv(self, files):
        if self.art_mode_on():
            self.log.info('removing files from tv : {}'.format(files))
            self.tv.art().delete_list(files)
            self.uploaded_files = {k:v for k, v in self.uploaded_files.items() if v.get('content_id') is not None and v.get('content_id') not in files}
            self.write_upload_list()
        
    def get_last_updated(self, filename):
        return os.path.getmtime(os.path.join(self.folder, filename))
        
    def remove_files(self, files):
        TV_files = [f['content_id'] for f in self.tv.art().available() if f['category_id'] == 'MY-C0002']
        files_removed = [v.get('content_id') for k, v in self.uploaded_files.items() if (v.get('content_id') is not None and k not in files)]
        #delete images from tv
        if files_removed:
            self.delete_files_from_tv(files_removed)
            self.files_changed = True
            
    async def add_files(self, files):
        new_files = [f for f in files if f not in self.uploaded_files.keys()]
        #upload new files
        if new_files:
            self.log.info('adding files to tv : {}'.format(new_files))
            #wait for files to arrive
            await asyncio.sleep(5 * len(new_files))
            self.upload_files(new_files)
            self.files_changed = True
            
    async def update_files(self, files):
        modified_files = [f for f in files if f in self.uploaded_files.keys() and self.uploaded_files.get(f, {}).get('modified') != self.get_last_updated(f)]
        #delete old file and upload new:
        if modified_files:
            self.log.info('updating files on tv : {}'.format(modified_files))
            #wait for files to arrive
            await asyncio.sleep(5 * len(modified_files))
            files_to_delete = [v.get('content_id') for k, v in self.uploaded_files.items() if (k in modified_files and v.get('content_id') is not None)]
            self.delete_files_from_tv(files_to_delete)
            self.upload_files(modified_files)
            self.files_changed = True 
    
    async def monitor_dir(self):
        while not self._exit:
            try:
                if not os.path.exists(self.folder):
                    self.log.warning('folder {} does not exist'.format(self.folder))
                elif self.art_mode_on():
                    self.log.info('checking directory: {}'.format(self.folder))
                    files = [f for f in os.listdir(self.folder) if os.path.isfile(os.path.join(self.folder, f))]
                    #delete images from tv
                    self.remove_files(files)
                    #upload new files
                    await self.add_files(files)
                    #check for modified files
                    await self.update_files(files)
                    #random update if enabled
                    self.do_random_update()
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
                if self.files_changed and self.art_mode and self.uploaded_files.keys():
                    self.start = time.time()
                    file = random.choice(list(self.uploaded_files.keys()))
                    self.log.info('selecting tv art: {} content_id: {}'.format(file, self.uploaded_files[file]['content_id']))
                    self.tv.art().select_image(self.uploaded_files[file]['content_id'])
                    self.files_changed = False
            except Exception as e:
                self.log.warning("error in select_artwork: {}".format(e))
                self.files_changed = False
            await asyncio.sleep(self.period)

async def main():
    global log
    args = parseargs()
    if args.debug:
        log.setLevel(logging.DEBUG)
        log.info('Debug mode')
    
    mon = monitor_and_display(args.ip, os.path.normpath(args.folder), period=5, random_update=args.update)
    await mon.start_monitoring()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("System exit Received - Exiting program")
    log.info('Program Exited')