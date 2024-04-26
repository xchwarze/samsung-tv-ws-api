#!/usr/bin/env python3
# fully async example program to monitor a folder and upload/display on Frame TV
# NOTE: install Pillow (pip install Pillow) to automatically syncronize art on TV wth uploaded_files.json.

import sys
import logging
import os
import io
import random
import json
import asyncio
import time
import argparse
HAVE_PIL = False
try:
    from PIL import Image, ImageFilter, ImageChops
    HAVE_PIL=True
except ImportError:
    pass

from samsungtvws.async_art import SamsungTVAsyncArt

SIGINT = 2
SIGTERM = 15

logging.basicConfig(level=logging.INFO)


def parseargs():
    # Add command line argument parsing
    parser = argparse.ArgumentParser(description='Async Upload images to Samsung TV.')
    parser.add_argument('ip', action="store", type=str, default=None, help='ip address of TV (default: %(default)s))')
    parser.add_argument('-f','--folder', action="store", type=str, default="./images", help='folder to load images from (default: %(default)s))')
    parser.add_argument('-u','--update', action="store", type=int, default=0, help='random update period (mins) 0=off (default: %(default)s))')
    parser.add_argument('-c','--check', action="store", type=int, default=5, help='how often to check for new art (default: %(default)s))')
    parser.add_argument('-s','--sync', action='store_false', default=True, help='automatically syncronize (needs Pil library) (default: %(default)s))')
    parser.add_argument('-F','--favourite', action='store_true', default=False, help='include favourites in rotation (default: %(default)s))')
    parser.add_argument('-D','--debug', action='store_true', default=False, help='Debug mode (default: %(default)s))')
    return parser.parse_args()
    
class monitor_and_display:
    
    def __init__(self, ip, folder, period=5, random_update=1440, include_fav=False, sync=True):
        self.log = logging.getLogger('Main.'+__class__.__name__)
        self.debug = self.log.getEffectiveLevel() <= logging.DEBUG
        self.ip = ip
        self.folder = folder
        self.period = period
        self.random_update = random_update*60   #minutes
        self.include_fav = include_fav
        self.sync = sync
        self.upload_list_path = './uploaded_files.json'
        self.uploaded_files = {}
        self.fav = []
        self.api_version = 0
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
        
    def update_uploaded_files(self, filename, content_id):
        self.uploaded_files[filename] = {'content_id': content_id, 'modified':self.get_last_updated(filename)}
        
    async def get_api_version(self):
        api_version = await self.tv.get_api_version()
        self.api_version = 0 if int(api_version.replace('.','')) < 4000 else 1
        
    async def get_thumbnails(self, content_ids):
        thumbnails = {}
        if self.api_version == 0:
            thumbnails = {content_id:await self.tv.get_thumbnail(content_id) for content_id in content_ids}
        elif self.api_version == 1:
            thumbnails = {os.path.splitext(k)[0]:v for k,v in (await self.tv.get_thumbnail_list(content_ids)).items()}
        self.log.info('got {} thumbnails'.format(len(thumbnails)))
        return thumbnails
        
    def load_files(self):
        files = [f for f in os.listdir(self.folder) if os.path.isfile(os.path.join(self.folder, f))]
        self.log.info('loading files: {}'.format(files))
        files_images = {file:Image.open(os.path.join(self.folder, file)) for file in files}
        return files_images
        
    def are_images_equal(self, img1, img2):
        '''
        rough check if images are similar (avoid numpy which is faster)
        '''
        img1 = img1.convert('L').resize((384, 216)).filter(ImageFilter.GaussianBlur(radius=2))
        img2 = img2.convert('L').resize((384, 216)).filter(ImageFilter.GaussianBlur(radius=2))
        img3 = ImageChops.subtract(img1, img2)
        diff = sum(list(img3.getdata()))/(384*216)  #normalize
        equal_content = diff <= 0.2                 #pick a threshhold
        self.log.debug('equal_content: {}, diff: {}'.format(equal_content, diff))
        return equal_content
        
    async def initialize(self):
        await self.get_api_version()
        self.uploaded_files = self.read_upload_list()
        if HAVE_PIL and self.sync:
            self.log.info('reinitializing uploaded files list using PIL')
            files_images = self.load_files()
            if files_images:
                self.uploaded_files = {}
                self.log.info('downloading My Photos thumbnails')
                my_photos = [v['content_id'] for v in await self.tv.available('MY-C0002')]
                my_photos_thumbnails = await self.get_thumbnails(my_photos)
                self.log.info('checking thumbnails against {} files, please wait...'.format(len(files_images)))
                count = 0
                for filename, file_data in files_images.items():
                    for i, (my_content_id, my_data) in enumerate(my_photos_thumbnails.items()):
                        percent = (count*100)//(len(files_images)*len(my_photos_thumbnails))
                        if count % 10 == 0:
                            self.log.info('{}% complete'.format(percent))
                        self.log.debug('checking: {} against {}, thumbnail: {} bytes'.format(filename, my_content_id, len(my_data)))
                        if self.are_images_equal(Image.open(io.BytesIO(my_data)), file_data):
                            self.log.info('found uploaded file: {} as {}'.format(filename, my_content_id))
                            self.update_uploaded_files(filename, my_content_id)
                            count+=len(my_photos_thumbnails)-i
                            break
                        count+=1
                self.log.info('100% complete')
                self.write_upload_list()
            else:
                self.log.info('no files, using origional uploaded files list')
        else:
            self.log.warning('No PIL library, or syncing disabled, not reinitializing uploaded files list')  
        
    async def do_random_update(self):
        if self.random_update > 0 and (len(self.uploaded_files.keys()) > 1 or self.include_fav) and time.time() - self.start > self.random_update:
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
                self.update_uploaded_files(filename, await self.tv.upload(file_data, file_type=file_type))
                self.log.info('uploaded : {} to tv as {}'.format(filename, self.uploaded_files[filename]['content_id']))
                self.write_upload_list()
            
    async def delete_files_from_tv(self, content_ids):
        if self.tv.art_mode:
            self.log.info('removing files from tv : {}'.format(content_ids))
            await self.tv.delete_list(content_ids)
            self.uploaded_files = {k:v for k, v in self.uploaded_files.items() if v.get('content_id') is not None and v.get('content_id') not in content_ids}
            self.write_upload_list()
        
    def get_last_updated(self, filename):
        return os.path.getmtime(os.path.join(self.folder, filename))
        
    async def remove_files(self, files):
        TV_files = [f['content_id'] for f in await self.tv.available('MY-C0002')]
        content_ids_removed = [v.get('content_id') for k, v in self.uploaded_files.items() if (v.get('content_id') is not None and k not in files)]
        #delete images from tv
        if content_ids_removed:
            await self.delete_files_from_tv(content_ids_removed)
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
        await self.initialize()
        asyncio.create_task(self.monitor_dir())
        while not self._exit:
            try:
                if self.files_changed and self.tv.art_mode and (self.uploaded_files.keys() or self.include_fav):
                    self.start = time.time()
                    content_id = random.choice(list({v['content_id'] for v in self.uploaded_files.values()}.union({f['content_id'] for f in self.fav})))
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
    
    mon = monitor_and_display(  args.ip,
                                os.path.normpath(args.folder),
                                period=args.check,
                                random_update=args.update,
                                include_fav=args.favourite,
                                sync=args.sync)
    await mon.start_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        os._exit(1)