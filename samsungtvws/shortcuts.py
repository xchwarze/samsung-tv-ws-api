"""
SamsungTVWS - Samsung Smart TV WS API wrapper

Copyright (C) 2019 Xchwarze

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor,
    Boston, MA  02110-1335  USA

"""


class SamsungTVShortcuts:
	def __init__(self, remote):
		self.remote = remote

# Aspect Ratio
	def aspect_ratio(self):
		self.remote.send_key('KEY_ASPECT')

	def picture_size(self):
		self.remote.send_key('KEY_PICTURE_SIZE')

	def aspect_ratio_43(self):
		self.remote.send_key('KEY_4_3')

	def aspect_ratio_169(self):
		self.remote.send_key('KEY_16_9')

	def aspect_ratio_34_alt(self):
		self.remote.send_key('KEY_EXT14')

	def aspect_ratio_169_alt(self):
		self.remote.send_key('KEY_EXT15')

# Auto Arc Keys
	def auto_arc_c_force_aging(self):
		self.remote.send_key('KEY_AUTO_ARC_C_FORCE_AGING')

	def auto_arc_caption_eng(self):
		self.remote.send_key('KEY_AUTO_ARC_CAPTION_ENG')

	def auto_arc_usbjack_inspect(self):
		self.remote.send_key('KEY_AUTO_ARC_USBJACK_INSPECT')

	def auto_arc_reset(self):
		self.remote.send_key('KEY_AUTO_ARC_RESET')

	def auto_arc_lna_on(self):
		self.remote.send_key('KEY_AUTO_ARC_LNA_ON')

	def auto_arc_lna_off(self):
		self.remote.send_key('KEY_AUTO_ARC_LNA_OFF')

	def auto_arc_anynet_mode_ok(self):
		self.remote.send_key('KEY_AUTO_ARC_ANYNET_MODE_OK')

	def auto_arc_anynet_auto_start(self):
		self.remote.send_key('KEY_AUTO_ARC_ANYNET_AUTO_START')

	def auto_arc_caption_on(self):
		self.remote.send_key('KEY_AUTO_ARC_CAPTION_ON')

	def auto_arc_caption_off(self):
		self.remote.send_key('KEY_AUTO_ARC_CAPTION_OFF')

	def auto_arc_pip_double(self):
		self.remote.send_key('KEY_AUTO_ARC_PIP_DOUBLE')

	def auto_arc_pip_large(self):
		self.remote.send_key('KEY_AUTO_ARC_PIP_LARGE')

	def auto_arc_pip_left_top(self):
		self.remote.send_key('KEY_AUTO_ARC_PIP_LEFT_TOP')

	def auto_arc_pip_right_top(self):
		self.remote.send_key('KEY_AUTO_ARC_PIP_RIGHT_TOP')

	def auto_arc_pip_left_bottom(self):
		self.remote.send_key('KEY_AUTO_ARC_PIP_LEFT_BOTTOM')

	def auto_arc_pip_ch_change(self):
		self.remote.send_key('KEY_AUTO_ARC_PIP_CH_CHANGE')

	def auto_arc_autocolor_success(self):
		self.remote.send_key('KEY_AUTO_ARC_AUTOCOLOR_SUCCESS')

	def auto_arc_autocolor_fail(self):
		self.remote.send_key('KEY_AUTO_ARC_AUTOCOLOR_FAIL')

	def auto_arc_jack_ident(self):
		self.remote.send_key('KEY_AUTO_ARC_JACK_IDENT')

	def auto_arc_caption_kor(self):
		self.remote.send_key('KEY_AUTO_ARC_CAPTION_KOR')

	def auto_arc_antenna_air(self):
		self.remote.send_key('KEY_AUTO_ARC_ANTENNA_AIR')

	def auto_arc_antenna_cable(self):
		self.remote.send_key('KEY_AUTO_ARC_ANTENNA_CABLE')

	def auto_arc_antenna_satellite(self):
		self.remote.send_key('KEY_AUTO_ARC_ANTENNA_SATELLITE')

# Channel Keys
	def channel_up(self):
		self.remote.send_key('KEY_CHUP')

	def channel_down(self):
		self.remote.send_key('KEY_CHDOWN')

	def previous_channel(self):
		self.remote.send_key('KEY_PRECH')

	def favorite_channels(self):
		self.remote.send_key('KEY_FAVCH')

	def channel_list(self):
		self.remote.send_key('KEY_CH_LIST')

	def channel(self, ch):
		for c in str(ch):
			self.digit(c)
		self.enter()

	def digit(self, d):
		self.remote.send_key("KEY_" + d)

	def auto_program(self):
		self.remote.send_key('KEY_AUTO_PROGRAM')

	def magic_channel(self):
		self.remote.send_key('KEY_MAGIC_CHANNEL')

# Color Keys
	def green(self):
		self.remote.send_key('KEY_GREEN')

	def yellow(self):
		self.remote.send_key('KEY_YELLOW')

	def cyan(self):
		self.remote.send_key('KEY_CYAN')

	def red(self):
		self.remote.send_key('KEY_RED')

	# To preserve compatibility with older versions of Samsung TV WS
	def blue(self):
		self.remote.send_key("KEY_BLUE")

# Direction Keys
	def navigation_up(self):
		self.remote.send_key('KEY_UP')

	def navigation_down(self):
		self.remote.send_key('KEY_DOWN')

	def navigation_left(self):
		self.remote.send_key('KEY_LEFT')

	def navigation_right(self):
		self.remote.send_key('KEY_RIGHT')

	def navigation_returnback(self):
		self.remote.send_key('KEY_RETURN')

	def navigation_enter(self):
		self.remote.send_key('KEY_ENTER')

	# To preserve compatibility with older versions of Samsung TV WS
	def up(self):
		self.remote.send_key("KEY_UP")

	def down(self):
		self.remote.send_key("KEY_DOWN")

	def left(self):
		self.remote.send_key("KEY_LEFT")

	def right(self):
		self.remote.send_key("KEY_RIGHT")

	def enter(self, count=1):
		self.remote.send_key("KEY_ENTER")

	def back(self):
		self.remote.send_key("KEY_RETURN")

# Extended Keys
	def ext1(self):
		self.remote.send_key('KEY_EXT1')

	def ext2(self):
		self.remote.send_key('KEY_EXT2')

	def ext3(self):
		self.remote.send_key('KEY_EXT3')

	def ext4(self):
		self.remote.send_key('KEY_EXT4')

	def ext5(self):
		self.remote.send_key('KEY_EXT5')

	def ext6(self):
		self.remote.send_key('KEY_EXT6')

	def ext7(self):
		self.remote.send_key('KEY_EXT7')

	def ext8(self):
		self.remote.send_key('KEY_EXT8')

	def ext11(self):
		self.remote.send_key('KEY_EXT11')

	def ext12(self):
		self.remote.send_key('KEY_EXT12')

	def ext13(self):
		self.remote.send_key('KEY_EXT13')

	def ext16(self):
		self.remote.send_key('KEY_EXT16')

	def ext17(self):
		self.remote.send_key('KEY_EXT17')

	def ext18(self):
		self.remote.send_key('KEY_EXT18')

	def ext19(self):
		self.remote.send_key('KEY_EXT19')

	def ext20(self):
		self.remote.send_key('KEY_EXT20')

	def ext21(self):
		self.remote.send_key('KEY_EXT21')

	def ext22(self):
		self.remote.send_key('KEY_EXT22')

	def ext23(self):
		self.remote.send_key('KEY_EXT23')

	def ext24(self):
		self.remote.send_key('KEY_EXT24')

	def ext25(self):
		self.remote.send_key('KEY_EXT25')

	def ext26(self):
		self.remote.send_key('KEY_EXT26')

	def ext27(self):
		self.remote.send_key('KEY_EXT27')

	def ext28(self):
		self.remote.send_key('KEY_EXT28')

	def ext29(self):
		self.remote.send_key('KEY_EXT29')

	def ext30(self):
		self.remote.send_key('KEY_EXT30')

	def ext31(self):
		self.remote.send_key('KEY_EXT31')

	def ext32(self):
		self.remote.send_key('KEY_EXT32')

	def ext33(self):
		self.remote.send_key('KEY_EXT33')

	def ext34(self):
		self.remote.send_key('KEY_EXT34')

	def ext35(self):
		self.remote.send_key('KEY_EXT35')

	def ext36(self):
		self.remote.send_key('KEY_EXT36')

	def ext37(self):
		self.remote.send_key('KEY_EXT37')

	def ext38(self):
		self.remote.send_key('KEY_EXT38')

	def ext39(self):
		self.remote.send_key('KEY_EXT39')

	def ext40(self):
		self.remote.send_key('KEY_EXT40')

	def ext41(self):
		self.remote.send_key('KEY_EXT41')

# Input Keys
	def source(self):
		self.remote.send_key('KEY_SOURCE')

	def component_1(self):
		self.remote.send_key('KEY_COMPONENT1')

	def component_2(self):
		self.remote.send_key('KEY_COMPONENT2')

	def av_1(self):
		self.remote.send_key('KEY_AV1')

	def av_2(self):
		self.remote.send_key('KEY_AV2')

	def av_3(self):
		self.remote.send_key('KEY_AV3')

	def s_video_1(self):
		self.remote.send_key('KEY_SVIDEO1')

	def s_video_2(self):
		self.remote.send_key('KEY_SVIDEO2')

	def s_video_3(self):
		self.remote.send_key('KEY_SVIDEO3')

	def hdmi(self):
		self.remote.send_key('KEY_HDMI')

	def hdmi_1(self):
		self.remote.send_key('KEY_HDMI1')

	def hdmi_2(self):
		self.remote.send_key('KEY_HDMI2')

	def hdmi_3(self):
		self.remote.send_key('KEY_HDMI3')

	def hdmi_4(self):
		self.remote.send_key('KEY_HDMI4')

	def fm_radio(self):
		self.remote.send_key('KEY_FM_RADIO')

	def dvi(self):
		self.remote.send_key('KEY_DVI')

	def dvr(self):
		self.remote.send_key('KEY_DVR')

	def tv(self):
		self.remote.send_key('KEY_TV')

	def analog_tv(self):
		self.remote.send_key('KEY_ANTENA')

	def digital_tv(self):
		self.remote.send_key('KEY_DTV')

# Media Keys
	def rewind(self):
		self.remote.send_key('KEY_REWIND')

	def stop(self):
		self.remote.send_key('KEY_STOP')

	def play(self):
		self.remote.send_key('KEY_PLAY')

	def fast_forward(self):
		self.remote.send_key('KEY_FF')

	def record(self):
		self.remote.send_key('KEY_REC')

	def pause(self):
		self.remote.send_key('KEY_PAUSE')

	def live(self):
		self.remote.send_key('KEY_LIVE')

	def fnkey_quick_replay(self):
		self.remote.send_key('KEY_QUICK_REPLAY')

	def fnkey_still_picture(self):
		self.remote.send_key('KEY_STILL_PICTURE')

	def fnkey_instant_replay(self):
		self.remote.send_key('KEY_INSTANT_REPLAY')

# Menus
	def menu(self):
		self.remote.send_key('KEY_MENU')

	def top_menu(self):
		self.remote.send_key('KEY_TOPMENU')

	def tools(self):
		self.remote.send_key('KEY_TOOLS')

	def home(self):
		self.remote.send_key('KEY_HOME')

	def contents(self):
		self.remote.send_key('KEY_CONTENTS')

	def guide(self):
		self.remote.send_key('KEY_GUIDE')

	def disc_menu(self):
		self.remote.send_key('KEY_DISC_MENU')

	def dvr_menu(self):
		self.remote.send_key('KEY_DVR_MENU')

	def help(self):
		self.remote.send_key('KEY_HELP')

# Misc Keys
	def three_d(self):
		self.remote.send_key('KEY_PANNEL_CHDOWN')

	def anynet(self):
		self.remote.send_key('KEY_ANYNET')

	def energy_saving(self):
		self.remote.send_key('KEY_ESAVING')

	def sleep_timer(self):
		self.remote.send_key('KEY_SLEEP')

	def dtv_signal(self):
		self.remote.send_key('KEY_DTV_SIGNAL')

# Modes
	def vcr_mode(self):
		self.remote.send_key('KEY_VCR_MODE')

	def catv_mode(self):
		self.remote.send_key('KEY_CATV_MODE')

	def dss_mode(self):
		self.remote.send_key('KEY_DSS_MODE')

	def tv_mode(self):
		self.remote.send_key('KEY_TV_MODE')

	def dvd_mode(self):
		self.remote.send_key('KEY_DVD_MODE')

	def stb_mode(self):
		self.remote.send_key('KEY_STB_MODE')

	def pc_mode(self):
		self.remote.send_key('KEY_PCMODE')

# Number Keys
	def key1(self):
		self.remote.send_key('KEY_1')

	def key2(self):
		self.remote.send_key('KEY_2')

	def key3(self):
		self.remote.send_key('KEY_3')

	def key4(self):
		self.remote.send_key('KEY_4')

	def key5(self):
		self.remote.send_key('KEY_5')

	def key6(self):
		self.remote.send_key('KEY_6')

	def key7(self):
		self.remote.send_key('KEY_7')

	def key8(self):
		self.remote.send_key('KEY_8')

	def key9(self):
		self.remote.send_key('KEY_9')

	def key0(self):
		self.remote.send_key('KEY_0')

# OSD
	def info(self):
		self.remote.send_key('KEY_INFO')

	def caption(self):
		self.remote.send_key('KEY_CAPTION')

	def clockdisplay(self):
		self.remote.send_key('KEY_CLOCK_DISPLAY')

	def setup_clock(self):
		self.remote.send_key('KEY_SETUP_CLOCK_TIMER')

	def subtitle(self):
		self.remote.send_key('KEY_SUB_TITLE')

# Other Keys
	def wheel_left(self):
		self.remote.send_key('KEY_WHEEL_LEFT')

	def wheel_right(self):
		self.remote.send_key('KEY_WHEEL_RIGHT')

	def adddel(self):
		self.remote.send_key('KEY_ADDDEL')

	def plus_100(self):
		self.remote.send_key('KEY_PLUS100')

	def ad(self):
		self.remote.send_key('KEY_AD')

	def link(self):
		self.remote.send_key('KEY_LINK')

	def turbo(self):
		self.remote.send_key('KEY_TURBO')

	def convergence(self):
		self.remote.send_key('KEY_CONVERGENCE')

	def device_connect(self):
		self.remote.send_key('KEY_DEVICE_CONNECT')

	def key_11(self):
		self.remote.send_key('KEY_11')

	def key_12(self):
		self.remote.send_key('KEY_12')

	def key_factory(self):
		self.remote.send_key('KEY_FACTORY')

	def key_3speed(self):
		self.remote.send_key('KEY_3SPEED')

	def key_rsurf(self):
		self.remote.send_key('KEY_RSURF')

	def ff_(self):
		self.remote.send_key('KEY_FF_')

	def rewind_(self):
		self.remote.send_key('KEY_REWIND_')

	def angle(self):
		self.remote.send_key('KEY_ANGLE')

	def reserved_1(self):
		self.remote.send_key('KEY_RESERVED1')

	def program(self):
		self.remote.send_key('KEY_PROGRAM')

	def bookmark(self):
		self.remote.send_key('KEY_BOOKMARK')

	def print(self):
		self.remote.send_key('KEY_PRINT')

	def clear(self):
		self.remote.send_key('KEY_CLEAR')

	def v_chip(self):
		self.remote.send_key('KEY_VCHIP')

	def repeat(self):
		self.remote.send_key('KEY_REPEAT')

	def door(self):
		self.remote.send_key('KEY_DOOR')

	def open(self):
		self.remote.send_key('KEY_OPEN')

	def dma(self):
		self.remote.send_key('KEY_DMA')

	def mts(self):
		self.remote.send_key('KEY_MTS')

	def dnie(self):
		self.remote.send_key('KEY_DNIe')

	def srs(self):
		self.remote.send_key('KEY_SRS')

	def convert_audio_mainsub(self):
		self.remote.send_key('KEY_CONVERT_AUDIO_MAINSUB')

	def mdc(self):
		self.remote.send_key('KEY_MDC')

	def sound_effect(self):
		self.remote.send_key('KEY_SEFFECT')

	def perpect_focus(self):
		self.remote.send_key('KEY_PERPECT_FOCUS')

	def caller_id(self):
		self.remote.send_key('KEY_CALLER_ID')

	def scale(self):
		self.remote.send_key('KEY_SCALE')

	def magic_bright(self):
		self.remote.send_key('KEY_MAGIC_BRIGHT')

	def w_link(self):
		self.remote.send_key('KEY_W_LINK')

	def dtv_link(self):
		self.remote.send_key('KEY_DTV_LINK')

	def application_list(self):
		self.remote.send_key('KEY_APP_LIST')

	def back_mhp(self):
		self.remote.send_key('KEY_BACK_MHP')

	def alternate_mhp(self):
		self.remote.send_key('KEY_ALT_MHP')

	def dnse(self):
		self.remote.send_key('KEY_DNSe')

	def rss(self):
		self.remote.send_key('KEY_RSS')

	def entertainment(self):
		self.remote.send_key('KEY_ENTERTAINMENT')

	def id_input(self):
		self.remote.send_key('KEY_ID_INPUT')

	def id_setup(self):
		self.remote.send_key('KEY_ID_SETUP')

	def any_view(self):
		self.remote.send_key('KEY_ANYVIEW')

	def ms(self):
		self.remote.send_key('KEY_MS')

	def more(self):
		self.remote.send_key('KEY_MORE')

	def mic(self):
		self.remote.send_key('KEY_MIC')

	def nine_seperate(self):
		self.remote.send_key('KEY_NINE_SEPERATE')

	def auto_format(self):
		self.remote.send_key('KEY_AUTO_FORMAT')

	def dnet(self):
		self.remote.send_key('KEY_DNET')

# Panel Keys
	def pannel_power(self):
		self.remote.send_key('KEY_PANNEL_POWER')

	def pannel_chup(self):
		self.remote.send_key('KEY_PANNEL_CHUP')

	def pannel_volup(self):
		self.remote.send_key('KEY_PANNEL_VOLUP')

	def pannel_voldow(self):
		self.remote.send_key('KEY_PANNEL_VOLDOW')

	def pannel_enter(self):
		self.remote.send_key('KEY_PANNEL_ENTER')

	def pannel_menu(self):
		self.remote.send_key('KEY_PANNEL_MENU')

	def pannel_source(self):
		self.remote.send_key('KEY_PANNEL_SOURCE')

# Picture Mode
	def picture_mode(self):
		self.remote.send_key('KEY_PMODE')

	def picture_mode_panorama(self):
		self.remote.send_key('KEY_PANORAMA')

	def picture_mode_dynamic(self):
		self.remote.send_key('KEY_DYNAMIC')

	def picture_mode_standard(self):
		self.remote.send_key('KEY_STANDARD')

	def picture_mode_movie(self):
		self.remote.send_key('KEY_MOVIE1')

	def picture_mode_game(self):
		self.remote.send_key('KEY_GAME')

	def picture_mode_custom(self):
		self.remote.send_key('KEY_CUSTOM')

	def picture_mode_movie_alt(self):
		self.remote.send_key('KEY_EXT9')

	def picture_mode_standard_alt(self):
		self.remote.send_key('KEY_EXT10')

# Picture in Picture
	def pip_onoff(self):
		self.remote.send_key('KEY_PIP_ONOFF')

	def pip_swap(self):
		self.remote.send_key('KEY_PIP_SWAP')

	def pip_size(self):
		self.remote.send_key('KEY_PIP_SIZE')

	def pip_channel_up(self):
		self.remote.send_key('KEY_PIP_CHUP')

	def pip_channel_down(self):
		self.remote.send_key('KEY_PIP_CHDOWN')

	def pip_small(self):
		self.remote.send_key('KEY_AUTO_ARC_PIP_SMALL')

	def pip_wide(self):
		self.remote.send_key('KEY_AUTO_ARC_PIP_WIDE')

	def pip_bottom_right(self):
		self.remote.send_key('KEY_AUTO_ARC_PIP_RIGHT_BOTTOM')

	def pip_source_change(self):
		self.remote.send_key('KEY_AUTO_ARC_PIP_SOURCE_CHANGE')

	def pip_scan(self):
		self.remote.send_key('KEY_PIP_SCAN')

# Power Keys
	def power_off(self):
		self.remote.send_key('KEY_POWEROFF')

	def power_on(self):
		self.remote.send_key('KEY_POWERON')

	def power_toggle(self):
		self.remote.send_key('KEY_POWER')

	def power (self): # to preserve compatibility
		self.remote.send_key("KEY_POWER")

# Teletext
	def teletext_mix(self):
		self.remote.send_key('KEY_TTX_MIX')

	def teletext_subface(self):
		self.remote.send_key('KEY_TTX_SUBFACE')

# Volume Keys
	def volume_up(self):
		self.remote.send_key('KEY_VOLUP')

	def volume_down(self):
		self.remote.send_key('KEY_VOLDOWN')

	def mute(self):
		self.remote.send_key('KEY_MUTE')

# Zoom
	def zoom_move(self):
		self.remote.send_key('KEY_ZOOM_MOVE')

	def zoom_in(self):
		self.remote.send_key('KEY_ZOOM_IN')

	def zoom_out(self):
		self.remote.send_key('KEY_ZOOM_OUT')

	def zoom_1(self):
		self.remote.send_key('KEY_ZOOM1')

	def zoom_2(self):
		self.remote.send_key('KEY_ZOOM2')
