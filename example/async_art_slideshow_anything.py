#!/usr/bin/env python3
# fully async example program to slideshow any art on Frame TV

'''
Instructions:
Start the program with tv ip and -u set to however many minutes you want for the slideshow period
A 'slideshow' folder will be created, whith two sub folders 'my_photos' and 'favourites'
The 'my_photos' and 'favourites' will be syncronized with the TV folders every 60 seconds.
Do not put any other files in these folders, as they will be deleted. Add or remove from them using the smarthings app,
and wait for the folder to syncronize.
The 'slideshow' folder will initially be populated with the contents of the 'favourites' folder on first run, or if you delete all the files.

To choose what artwork to be displayed in the slideshow, COPY files from 'favourites' or 'my_photos' to 'slideshow'
Any artwork you don't want to be in the slideshow, delete from the 'slideshow' folder.
If you delete files from your TV, or un-favourite them, the corresponding files will be deleted from 'slideshows' (if present)

Only artwork in the 'slideshow' folder will be shown on the TV.

The sequence is random, and the time period will resume automatically when the program is restarted
'''

import logging
import os
import shutil
import random
import asyncio
import time
import argparse

from samsungtvws.async_art import SamsungTVAsyncArt

SIGINT = 2
SIGTERM = 15

logging.basicConfig(level=logging.INFO)


def parseargs():
    # Add command line argument parsing
    parser = argparse.ArgumentParser(description='Async Slideshow Any art on Samsung TV.')
    parser.add_argument('ip', action="store", type=str, default=None, help='ip address of TV (default: %(default)s))')
    parser.add_argument('-f','--folder', action="store", type=str, default="./slideshow", help='folder to store images in (default: %(default)s))')
    parser.add_argument('-u','--update', action="store", type=int, default=2, help='random update period (mins) 0=off (default: %(default)s))')
    parser.add_argument('-D','--debug', action='store_true', default=False, help='Debug mode (default: %(default)s))')
    return parser.parse_args()
    
class slideshow:

    categories = {  'my_photos' :{'category_id':'MY-C0002', 'dir':None},
                    'favourites':{'category_id':'MY-C0004', 'dir':None}
                 }
    
    def __init__(self, ip, folder, random_update=1440):
        self.log = logging.getLogger('Main.'+__class__.__name__)
        self.debug = self.log.getEffectiveLevel() <= logging.DEBUG
        self.ip = ip
        self.folder = folder
        self.random_update = max(2,random_update)*60   #minutes
        self.period = 60
        self.my_photos_dir = os.path.join(self.folder, 'my_photos')
        self.favourites_dir = os.path.join(self.folder, 'favourites')
        self.files_on_tv = {'my_photos':set(), 'favourites':set()}
        self.api_version = 1
        self._exit = False
        self.start = time.time()
        self.tv = SamsungTVAsyncArt(host=self.ip, port=8002)
        self.categories['my_photos']['dir'] = self.my_photos_dir
        self.categories['favourites']['dir'] = self.favourites_dir
        self.log.info('check thumbnails every: {}s, slideshow rotation every: {} minutes'.format(self.period, self.random_update//60))
        try:
            #doesn't work in Windows
            asyncio.get_running_loop().add_signal_handler(SIGINT, self.close)
            asyncio.get_running_loop().add_signal_handler(SIGTERM, self.close)
        except Exception:
            pass
        
    async def start_slideshow(self):
        await self.tv.start_listening()
        await self.select_artwork()
        
    def close(self):
        self.log.info('SIGINT/SIGTERM received, exiting')
        os._exit(1)
        
    def make_directory(self, directory):
        try:
            os.makedirs(directory, exist_ok=True)
        except OSError as e:
            pass
        
    async def get_api_version(self):
        api_version = await self.tv.get_api_version()
        self.api_version = 0 if int(api_version.replace('.','')) < 4000 else 1
        
    async def get_thumbnails(self, content_ids):
        thumbnails = {}
        if self.api_version == 0:
            thumbnails = {k:v for k,v in self.tv.get_thumbnail(content_id, True).items() for content_id in content_ids}
        elif self.api_version == 1:
            thumbnails = await self.tv.get_thumbnail_list(content_ids)
        self.log.info('got {} thumbnails'.format(len(thumbnails)))
        return thumbnails
        
    async def initialize(self):
        self.make_directory(self.my_photos_dir)
        self.make_directory(self.favourites_dir)
        await self.get_api_version()
        await self.download_thmbnails()
        if not self.get_files('slideshow'):
            self.log.info('initializing slideshow from favourites')
            for file in self.get_files('favourites'):
                shutil.copy2(os.path.join(self.categories['favourites']['dir'], file), self.folder)
        await self.set_start()
                
    async def set_start(self):
        content_id = (await self.tv.get_current()).get('content_id')
        self.log.debug('got current artwork: {}'.format(content_id))
        self.start = max(time.time() - self.random_update*60, self.get_last_updated(self.get_filename(content_id)))
              
    def get_files(self, cat):
        return self.get_file_set(self.folder if cat=='slideshow' else self.categories[cat]['dir'])
        
    def get_filename(self, content_id, cat='favourites'):
        return next(iter(f for f in self.get_files(cat) if self.get_content_ids(f) == content_id), None)
        
    def get_last_updated(self, filename):
        if filename:
            return os.path.getmtime(os.path.join(self.folder, filename))
        return time.time()
        
    def set_last_updated(self, filename):
        if filename:
            path = os.path.join(self.folder, filename)
            os.utime(path, (os.path.getctime(path), time.time()))
        
    async def update_thmbnails(self, cat):
        self.log.info('checking thumbnails {}'.format(cat))
        files = self.get_files(cat)
        self.files_on_tv[cat] = {v['content_id'] for v in await self.tv.available(self.categories[cat]['category_id'])}
        self.log.debug('got content list: {}'.format(self.files_on_tv[cat]))
        new_thumbnails = self.files_on_tv[cat].difference(self.get_content_ids(files))
        self.log.info('downloading {} thumbnails'.format(len(new_thumbnails)))
        if new_thumbnails:
            photos_thumbnails = await self.get_thumbnails(new_thumbnails)
            new_thumbnails = {k:v for k,v  in photos_thumbnails.items() if k not in files}
            self.write_thumbnails(self.categories[cat]['dir'], new_thumbnails) 
            
    def remove_files(self, cat='slideshow'):
        self.log.info('checking for deleted files in {}'.format(cat))
        files = self.get_files(cat)
        if cat == 'slideshow':
            my_files_remove = self.get_content_ids(files).difference(self.files_on_tv['my_photos'].union(self.files_on_tv['favourites']))
        else:
            my_files_remove = self.get_content_ids(files).difference(self.files_on_tv[cat])
        remove_files = [os.path.join(self.folder if cat == 'slideshow' else self.categories[cat]['dir'], f) for f in files if self.get_content_ids(f) in my_files_remove]
        self.log.debug('photos to remove: {}'.format(my_files_remove))
        self.log.info('removing: {}'.format(remove_files))
        for path in remove_files:
            if os.path.exists(path):
                self.log.debug('deleting file: {}'.format(path))
                os.unlink(path)
            else:
                self.log.warning('cannot remove {} as it does not exist'.format(path))
        self.log.info('done checking for deleted files')
        
    async def download_thmbnails(self):
        await self.update_thmbnails('my_photos')
        await self.update_thmbnails('favourites')
        self.remove_files('my_photos')
        self.remove_files('favourites')
        self.remove_files('slideshow')
        
    async def do_random_update(self):
        if time.time() - self.start > self.random_update:
            self.log.info('doing random update, after {} minutes'.format(self.random_update//60))
            self.start = time.time()
            await self.download_thmbnails()
            slideshow_files = list(self.get_content_ids(self.get_files('slideshow')))
            if slideshow_files:
                content_id = random.choice(slideshow_files)
                self.log.info('selecting tv art: content_id: {}'.format(content_id))
                self.set_last_updated(self.get_filename(content_id))
                await self.tv.select_image(content_id)
            return True
        return False
            
    def write_thumbnails(self, folder, thumbnails):
        try:
            for filename, data in thumbnails.items():
                path = os.path.join(folder, filename)
                if not os.path.exists(path):
                    self.log.info('writing {}'.format(path))
                    with open(path, 'wb') as f:
                        f.write(data)
        except Exception as e:
            self.log.error('error writing file: {}, {}'.format(os.path.join(folder, filename), e))
        
    def get_file_set(self, folder):
        return {f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))}
            
    def get_content_ids(self, filenames):
        if isinstance(filenames, str):
            return os.path.splitext(filenames)[0]
        return {os.path.splitext(v)[0] for v in filenames}
        
    def get_countdown(self):
        return round(max(0,(self.random_update - (time.time() - self.start))/60), 0)

    async def select_artwork(self):
        await self.initialize()
        start = True
        while not self._exit:
            try:
                if not self.tv.is_alive():
                    self.log.warning('reconnecting websocket')
                    await self.tv.start_listening()
                if self.tv.art_mode:
                    self.log.info('time to next rotation: {} mins'.format(self.get_countdown()))
                    if not await self.do_random_update() and not start:
                        await self.download_thmbnails()
                    start = False
                else:
                    self.log.info('artmode or tv is off')
            except Exception as e:
                self.log.warning("error in select_artwork: {}".format(e))
                if self.debug:
                    self.log.exception(e)
            await asyncio.sleep(60)
            
async def main():
    global log
    log = logging.getLogger('Main')
    args = parseargs()
    if args.debug:
        log.setLevel(logging.DEBUG)
    log.debug('Debug mode')
    
    mon = slideshow(args.ip,
                    os.path.normpath(args.folder),
                    random_update=args.update)
    await mon.start_slideshow()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        os._exit(1)