#!/usr/bin/env python3
# fully async example program to monitor a folder and upload/display on Frame TV
# NOTE: install Pillow (pip install Pillow) to automatically syncronize art on TV wth uploaded_files.json.

'''
This program will read the files in a designated folder (with allowed extensions) and upload them to your TV. It keeps track of which files correspond to what
content_id on your TV by saving the data in a file called uploaded_files.json. it also keeps track of when the selected artwork was last changed.

It monitors the folder for changes every check seconds (5 by default), new files are uploaded to the TV, removed files are deleted from the TV, and if a file
is changed, the old content is removed from the TV and the new content uploaded to the TV. Content is only changed if the TV is in art mode.

if check is set to 0 seconds, the program will run once and exit. You can then run it periodically (say with a cron job).

if there is more than one file in the folder, the current artword displayed is changed every update minutes (0) by default (which means do not select any artwork),
otherwise the single file in the folder is selected to be displayed. this also only happens when the TV is in art mode.

If you have PIL installed, the initial syncronization is automatic, the first time the program is run.

If the on (-O) option is selected, the program wil exit if the TV is not on (TV or art mode).
If the sequential (-S) option is selected, then the slideshow is sequential, not random (random is the default)

Example:
    1) Your TV is used to display one image, that changes every day, you have a program that grabs the image and puts it in a folder. The image always has the same name.
       run ./async_art_update_from_folder.py <tv_ip> -f <folder_path> -c 0
       to update the image on the Tv after the script that grabs the file runs
       If you are unsure if the TV will be on when you run the program
       run ./async_art_update_from_folder.py <tv_ip> -f <folder_path> -c 0 -O
       or
       run ./async_art_update_from_folder.py <tv_ip> -f <folder_path> -c 60
       and leave it running
       
    2) You use your TV to display your own artwork, you want a slideshow that displays a random artwork every minute, but want to add/remove art from a network share
       run ./async_art_update_from_folder.py <tv_ip> -f <folder_path_to_share> -c 60 -u 1
       and leave it running. Add/remove art from the network share folder to include it/remove it from the slideshow.
       If you want an update every 15 seconds
       run ./async_art_update_from_folder.py <tv_ip> -f <folder_path_to_share> -c 15 -u 0.25
       
    3) you have artwork on the TV marked as "favourites", but want to inclue your own artwork from a folder in a random slideshow that updates once a day
       run ./async_art_update_from_folder.py <tv_ip> -f <folder_path> -c 3600 -u 1440 -F
       and leave it running. Add/remove art from the folder to include it/remove it from the slideshow.
       
    4) You have some standard art uploaded to your TV, that you slideshow from the TV, but want to add seasonal artworks to the slideshow that you change from time to time.
       run ./async_art_update_from_folder.py <tv_ip> -f <folder_path> -c 3600
       and leave it running. Add/remove art from the folder to include it/remove it from the slideshow.
       or
       run ./async_art_update_from_folder.py <tv_ip> -f <folder_path> -c 0 -O
       after updating the files in the folder
'''

import sys
import logging
import os
import io
import random
import json
import asyncio
import time
import datetime
import argparse
from signal import SIGTERM, SIGINT
HAVE_PIL = False
try:
    from PIL import Image, ImageFilter, ImageChops
    HAVE_PIL=True
except ImportError:
    pass

from samsungtvws.async_art import SamsungTVAsyncArt

logging.basicConfig(level=logging.INFO)


def parseargs():
    # Add command line argument parsing
    parser = argparse.ArgumentParser(description='Async Upload images to Samsung TV.')
    parser.add_argument('ip', action="store", type=str, default=None, help='ip address of TV (default: %(default)s))')
    parser.add_argument('-f','--folder', action="store", type=str, default="./images", help='folder to load images from (default: %(default)s))')
    parser.add_argument('-m','--matte', action="store", type=str, default="none", help='default matte to use (default: %(default)s))')
    parser.add_argument('-u','--update', action="store", type=float, default=0, help='random update period (mins) 0=off (default: %(default)s))')
    parser.add_argument('-c','--check', action="store", type=int, default=5, help='how often to check for new art 0=run once (default: %(default)s))')
    parser.add_argument('-s','--sync', action='store_false', default=True, help='automatically syncronize (needs Pil library) (default: %(default)s))')
    parser.add_argument('-S','--sequential', action='store_true', default=False, help='sequential slide show (default: %(default)s))')
    parser.add_argument('-O','--on', action='store_true', default=False, help='exit if TV is off (default: %(default)s))')
    parser.add_argument('-F','--favourite', action='store_true', default=False, help='include favourites in rotation (default: %(default)s))')
    parser.add_argument('-D','--debug', action='store_true', default=False, help='Debug mode (default: %(default)s))')
    return parser.parse_args()
    
class monitor_and_display:
    
    allowed_ext = ['jpg', 'jpeg', 'png', 'bmp', 'tif']
    
    def __init__(self, ip, folder, period=5, random_update=1440, include_fav=False, sync=True, matte='none', sequential=False, on=False):
        self.log = logging.getLogger('Main.'+__class__.__name__)
        self.debug = self.log.getEffectiveLevel() <= logging.DEBUG
        self.ip = ip
        self.folder = folder
        self.random_update = int(max(0, random_update*60))   #convert minutes to seconds
        self.period = min(max(5, period), self.random_update) if self.random_update > 0 else period
        self.include_fav = include_fav
        self.sync = sync
        self.matte = matte
        self.sequential = sequential
        self.on = on
        self.program_data_path = './uploaded_files.json'
        self.uploaded_files = {}
        self.fav = set()
        self.api_version = 0
        self.start = time.time()
        self.files_changed = False
        self.current_content_id = None
        self.tv = SamsungTVAsyncArt(host=self.ip, port=8002)
        try:
            #doesn't work in Windows
            asyncio.get_running_loop().add_signal_handler(SIGINT, self.close)
            asyncio.get_running_loop().add_signal_handler(SIGTERM, self.close)
        except Exception:
            pass
        
    async def start_monitoring(self):
        if self.on and not await self.tv.on():
            self.log.info('TV is off, exiting')
        else:
            self.log.info('Start Monitoring')
            try:
                await self.tv.start_listening()
                self.log.info('Started')
            except Exception as e:
                self.log.error('failed to connect with TV: {}'.format(e))
            if self.tv.is_alive():
                await self.check_matte()
                await self.select_artwork()
        await self.tv.close()
        
    def close(self):
        self.log.info('SIGINT/SIGTERM received, exiting')
        os._exit(1)
        
    def update_uploaded_files(self, filename, content_id):
        self.uploaded_files.pop(filename, None)
        if content_id:
            self.uploaded_files[filename] = {'content_id': content_id, 'modified':self.get_last_updated(filename)}
        
    async def get_api_version(self):
        api_version = await self.tv.get_api_version()
        self.api_version = 0 if int(api_version.replace('.','')) < 4000 else 1
        
    async def check_matte(self):
        if self.matte != 'none':
            matte = self.matte.split('_')
            mattes = await self.tv.get_matte_list(True)
            if mattes and len(matte) == 2:
                matte_types = [m['matte_type'] for m in mattes[0]]
                matte_colors = [m['color'] for m in mattes[1]]
                if matte[0] in matte_types and matte[1] in matte_colors:
                    self.log.info('using matte: {}'.format(self.matte))
                    return
                else:
                    self.log.info('Valid mattes and colors: {}'.format(mattes))
            self.log.warning('Invalid matte selected: {}. A valid matte would be shadowbox_polar for eample, using none'.format(self.matte))
            self.matte = 'none'
        
    async def get_tv_content(self, category='MY-C0002'):
        result = []
        try:
            result = [v['content_id'] for v in await self.tv.available(category)]
        except AssertionError:
            pass
        return result
        
    async def get_thumbnails(self, content_ids):
        thumbnails = {}
        if content_ids:
            if self.api_version == 0:
                thumbnails = {content_id:await self.tv.get_thumbnail(content_id) for content_id in content_ids}
            elif self.api_version == 1:
                thumbnails = {os.path.splitext(k)[0]:v for k,v in (await self.tv.get_thumbnail_list(content_ids)).items()}
        self.log.info('got {} thumbnails'.format(len(thumbnails)))
        return thumbnails
        
    def load_files(self):
        files = self.get_folder_files()
        self.log.info('loading files: {}'.format(files))
        files_images = self.get_files_dict(files)
        self.log.info('loaded: {}'.format(list(files_images.keys())))
        return files_images
        
    def get_folder_files(self):
        return [f for f in os.listdir(self.folder) if os.path.isfile(os.path.join(self.folder, f)) and self.get_file_type(os.path.join(self.folder, f)) in self.allowed_ext]
        
    def get_files_dict(self, files):
        files_images = {}
        for file in files:
            try:
                data = Image.open(os.path.join(self.folder, file))
                format = self.get_file_type(os.path.join(self.folder, file), data)
                if not (file.lower().endswith(format) or (format=='jpeg' and file.lower().endswith('jpg'))):
                    self.log.warning('file: {} is of type {}, the extension is wrong! please fix this'.format(file, format))
                files_images[file] = data
            except Exception as e:
                self.log.warning('Error loading: {}, {}'.format(file, e))
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
        
    async def get_current_artwork(self):
        try:
            content_id = (await self.tv.get_current()).get('content_id')
        except Exception:
            content_id = None
        return content_id
        
    async def initialize(self):
        await self.get_api_version()
        self.current_content_id = await self.get_current_artwork()
        self.log.info('Current artwork is: {}'.format(self.current_content_id))
        self.load_program_data()
        if HAVE_PIL and self.sync:
            self.log.info('Checking uploaded files list using PIL')
            files_images = self.load_files()
            if files_images:
                self.log.info('downloading My Photos thumbnails')
                my_photos = await self.get_tv_content('MY-C0002')
                if my_photos:
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
                                if filename not in self.uploaded_files.keys():
                                    self.update_uploaded_files(filename, my_content_id)
                                count+=len(my_photos_thumbnails)-i
                                break
                            count+=1
                    self.log.info('100% complete')
                    self.write_program_data()
                else:
                    self.log.info('no thubnails found')
            else:
                self.log.info('no files, using origional uploaded files list')
        else:
            self.log.warning('No PIL library, or syncing disabled, not updating uploaded files list')
            
    async def sync_file_list(self, files=None):
        my_photos = await self.get_tv_content('MY-C0002')
        self.uploaded_files = {k:v for k,v in self.uploaded_files.items() if v['content_id'] in my_photos and (k in files if files else True)}
        self.write_program_data()
        
    async def do_random_update(self):
        if self.random_update > 0 and (len(self.uploaded_files.keys()) > 1 or self.include_fav):
            if time.time() - self.start >= self.random_update:
                self.log.info('doing random update, after {}'.format(datetime.timedelta(seconds = self.random_update)))
                self.start = time.time()
                self.write_program_data()
                if self.include_fav:
                    self.log.info('updating favourites')
                    self.fav = set(await self.get_tv_content('MY-C0004'))
                self.files_changed = True
            else:
                self.log.info('next random update in {}'.format(datetime.timedelta(seconds = (self.random_update - (time.time() - self.start)))))
   
    def load_program_data(self):
        if os.path.isfile(self.program_data_path):
            with open(self.program_data_path, 'r') as f:
                program_data = json.load(f)
                self.uploaded_files = program_data.get('uploaded_files', program_data)
                self.start = program_data.get('last_update', time.time())
        else:
            self.uploaded_files = {}
            self.start = time.time()
        
    def write_program_data(self):
        with open(self.program_data_path, 'w') as f:
            program_data = {'last_update': self.start, 'uploaded_files': self.uploaded_files}
            json.dump(program_data, f)
            
    def read_file(self, filename):
        try:
            with open(filename, 'rb') as f:
                file_data = f.read()
            file_type = self.get_file_type(filename)
            return file_data, file_type
        except Exception as e:
            self.log.error('Error reading file: {}, {}'.format(filename, e))
        return None, None
        
    def get_file_type(self, filename, image_data=None):
        try:
            file_type = os.path.splitext(filename)[1][1:].lower()
            file_type = file_type.lower() if file_type else None
            if HAVE_PIL and file_type:
                org = file_type
                file_type = Image.open(filename).format.lower() if not image_data else image_data.format.lower()
                if file_type in['jpg', 'jpeg', 'mpo']:
                    file_type = 'jpeg'
                if not (org == file_type or (org == 'jpg' and file_type == 'jpeg')):
                    self.log.warning('file {} type changed from {} to {}'.format(filename, org, file_type))
            return file_type
        except Exception as e:
            self.log.error('Error reading file: {}, {}'.format(filename, e))
        return None
        
    async def upload_files(self, filenames):
        for filename in filenames:
            path = os.path.join(self.folder, filename)
            file_data, file_type = self.read_file(path)
            if file_data and self.tv.art_mode:
                self.log.info('uploading : {} to tv'.format(filename))
                self.update_uploaded_files(filename, await self.tv.upload(file_data, file_type=file_type, matte=self.matte, portrait_matte=self.matte))
                if self.uploaded_files.get(filename, {}).get('content_id'):
                    self.log.info('uploaded : {} to tv as {}'.format(filename, self.uploaded_files[filename]['content_id']))
                else:
                    self.log.warning('file: {} failed to upload'.format(filename))
                self.write_program_data()
            
    async def delete_files_from_tv(self, content_ids):
        if self.tv.art_mode:
            self.log.info('removing files from tv : {}'.format(content_ids))
            await self.tv.delete_list(content_ids)
            await self.sync_file_list()

    def get_last_updated(self, filename):
        return os.path.getmtime(os.path.join(self.folder, filename))
        
    async def remove_files(self, files):
        content_ids_removed = [v['content_id'] for k, v in self.uploaded_files.items() if k not in files]
        #delete images from tv
        if content_ids_removed:
            await self.delete_files_from_tv(content_ids_removed)
            self.files_changed = True
            
    async def add_files(self, files):
        new_files = [f for f in files if f not in self.uploaded_files.keys()]
        #upload new files
        if new_files:
            self.log.info('adding files to tv : {}'.format(new_files))
            await self.wait_for_files(new_files)
            await self.upload_files(new_files)
            self.files_changed = True
            
    async def update_files(self, files):
        modified_files = [f for f in files if f in self.uploaded_files.keys() and self.uploaded_files[f].get('modified') != self.get_last_updated(f)]
        #delete old file and upload new:
        if modified_files:
            self.log.info('updating files on tv : {}'.format(modified_files))
            await self.wait_for_files(modified_files)
            files_to_delete = [v['content_id'] for k, v in self.uploaded_files.items() if k in modified_files]
            await self.delete_files_from_tv(files_to_delete)
            await self.upload_files(modified_files)
            self.files_changed = True
            
    async def wait_for_files(self, files):
        #wait for files to arrive
        await asyncio.sleep(min(10, 5 * len(files)))
        
    def get_next_art(self):
        content_id = None
        content_ids = list({v['content_id'] for v in self.uploaded_files.values()}.union(self.fav))
        if content_ids:
            if self.sequential:
                try:
                    thiselem = content_ids.index(self.current_content_id)
                    idx = (thiselem + 1) % len(content_ids)
                    content_id = content_ids[idx]
                except Exception:
                    content_id = content_ids[0]
            else:
                content_id = random.choice(content_ids)
            self.current_content_id = content_id
        return content_id
    
    async def check_dir(self):
        try:
            if not os.path.exists(self.folder):
                self.log.warning('folder {} does not exist'.format(self.folder))
            elif self.tv.art_mode:
                self.log.info('checking directory: {}{}'.format(self.folder, ' every {}'.format(datetime.timedelta(seconds = self.period)) if self.period else ''))
                files = self.get_folder_files()
                await self.sync_file_list()
                #delete images from tv
                await self.remove_files(files)
                #upload new files
                await self.add_files(files)
                #check for modified files
                await self.update_files(files)
                #random update if enabled
                await self.do_random_update()
                if not self.files_changed:
                    self.log.info('no changes')
            else:
                self.log.info('artmode or tv is off')
        except Exception as e:
            self.log.warning("error in check_dir: {}".format(e))

    async def select_artwork(self):
        await self.initialize()
        while True:
            try:
                await self.check_dir()
                if self.files_changed and self.tv.art_mode and (self.uploaded_files.keys() or self.include_fav) and (self.random_update > 0 or len(self.uploaded_files.keys()) == 1):
                    content_id = self.get_next_art()
                    if content_id:
                        self.log.info('selecting tv art: content_id: {}'.format(content_id))
                        await self.tv.select_image(content_id)
                    self.files_changed = False
            except Exception as e:
                self.log.warning("error in select_artwork: {}".format(e))
                self.files_changed = False
            if self.period == 0:
                break
            await asyncio.sleep(self.period)
            
async def main():
    global log
    log = logging.getLogger('Main')
    args = parseargs()
    log.info('Program Started')
    if args.debug:
        log.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
    log.debug('Debug mode')
    
    mon = monitor_and_display(  args.ip,
                                os.path.normpath(args.folder),
                                period          = args.check,
                                random_update   = args.update,
                                include_fav     = args.favourite,
                                sync            = args.sync,
                                matte           = args.matte,
                                sequential      = args.sequential,
                                on              = args.on)
    await mon.start_monitoring()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        os._exit(1)