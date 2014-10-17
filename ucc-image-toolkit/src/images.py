#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Corporate Client
#  UCC image download tool
#
# Copyright (C) 2012-2014 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

import os
import shutil
import subprocess
import sys
import tempfile
import yaml
import urllib
import hashlib
import lzma
import httplib
import urllib2
import urlparse
import contextlib
import re
import psutil
import traceback
import time

import univention.config_registry as ucr
import univention.debug as ud
from univention.lib.i18n import Translation
_ = Translation('ucc-image-toolkit').translate


use_univention_debug = True

# short cuts for logging
def log_warn(msg):
	if use_univention_debug:
		ud.debug(ud.MODULE, ud.WARN, msg)
	else:
		sys.stdout.write(_('WARN: %s\n') % msg)

def log_error(msg):
	if use_univention_debug:
		ud.debug(ud.MODULE, ud.ERROR, msg)
	else:
		sys.stdout.write(_('ERROR: %s\n') % msg)

def log_process(msg):
	if use_univention_debug:
		ud.debug(ud.MODULE, ud.PROCESS, msg)
	else:
		sys.stdout.write('%s\n' % msg)

def log_info(msg):
	if use_univention_debug:
		ud.debug(ud.MODULE, ud.INFO, msg)

def _exit(msg, sys_exit=False):
	if not use_univention_debug and sys_exit:
		log_error(msg)
		sys.exit(1)
	raise RuntimeError(msg)


configRegistry = ucr.ConfigRegistry()
configRegistry.load()

UCC_BASE_URL = configRegistry['ucc/image/download/url']
if UCC_BASE_URL.endswith('/'):
	# remove trailing '/'
	UCC_BASE_URL = UCC_BASE_URL[:-1]
UCC_IMAGE_DIRECTORY = configRegistry['ucc/image/path']
UCC_IMAGE_INDEX_FILE = 'image-index.txt'
UCC_IMAGE_INDEX_URL = '%s/%s' % (UCC_BASE_URL, UCC_IMAGE_INDEX_FILE)
DEFAULT_CHUNK_SIZE = 2**13


def _dummy_progress(*args):
	pass


# helper function for wrapping the advance method of the Progress object
def _advance_wrapper(percent_fraction, total_progress, progress):
	def _advance(current_size, file_size):
		fraction_file = float(current_size) / file_size
		percent_file = 100.0 * fraction_file
		percent_total = total_progress + fraction_file * percent_fraction
		progress.advance(percent_total, percent_file)

	return _advance


def _free_disk_space(path):
	'''Returns the free disk space for a given path.'''
	vfs = os.statvfs(path)
	free_diskspace = vfs.f_frsize * vfs.f_bavail
	return free_diskspace


def _physical_memory():
	return (psutil.used_phymem() + psutil.avail_phymem())


def _sha256(filepath, progress=_dummy_progress):
	'''Computes the sha256 sum for the given file. Optionally with a callback
	function that receives the parameters (bytes_processed, bytes_total).'''

	file_size = os.path.getsize(filepath)
	file_hash = hashlib.sha256()
	with open(filepath, 'rb') as infile:
		while True:
			data = infile.read(DEFAULT_CHUNK_SIZE)
			if not data:
				break

			file_hash.update(data)
			progress(infile.tell(), file_size)

	return file_hash.hexdigest()


def _unxz(infile, keep_src_file=False, progress=_dummy_progress):
	'''Decompresses the given .xz file. Optionally with a callback
	function that receives the parameters (bytes_processed, bytes_total).'''

	assert infile.endswith('.xz')
	outfile = infile[:-3]
	total_size = os.path.getsize(infile)
	mem_limit = _physical_memory() / 4  # only take at maximum 25% of the physical memory!
	decompressor = lzma.LZMADecompressor()
	decompressor.reset(max_length=0, memlimit=mem_limit)

	try:
		with contextlib.nested(open(infile, 'rb'), open(outfile, 'wb')) as (fin, fout):
			counter = 0
			while True:
				compressed_data = fin.read(DEFAULT_CHUNK_SIZE)
				if not compressed_data:
					uncompressed_data = decompressor.flush()
					break

				uncompressed_data = decompressor.decompress(compressed_data)
				fout.write(uncompressed_data)
				progress(fin.tell(), total_size)
				del compressed_data
				del uncompressed_data

				# check free size on disk every N rounds
				if counter % 50 == 0:
					free_diskspace_gb = _free_disk_space(UCC_IMAGE_DIRECTORY) / 1000**3  # in GB
					if free_diskspace_gb < 0.5:
						raise IOError(_('Not enough space left on hard disk.'))
				counter += 1

		if not keep_src_file:
			# successful decompression -> remove compressed source file
			os.remove(infile)
	except (IOError, OSError) as exc:
		# remove extracted file in case we do not have enough space
		if os.path.exists(outfile):
			os.remove(outfile)
		_exit(_('Decompression of file %s failed: %s') % (infile, exc))


def _get_file_size(filename):
	'''Get the file size (in byte) for the given file at the URL specified by
	ucc/image/path via a HTTP HEAD request.'''

	url = '%s/%s' % (UCC_BASE_URL, filename)
	request = urllib2.Request(url)
	request.get_method = lambda : 'HEAD'
	try:
		response = urllib2.urlopen(request)
	except urllib2.HTTPError as exc:
		# raise an httplib error since this exception type is handled
		raise httplib.error(_('Could not download file %s: %s') % (url, exc))

	info = response.info()
	size = int(info.getheader('content-length', '0'))
	return size


def _get_proxies():
	proxies = {}
	proxy_http = configRegistry.get('proxy/http')
	if proxy_http:
		proxies = {'http': proxy_http, 'https': proxy_http}
	return proxies


# inspired from from u.m.c.modules.appcenter.util
def _install_opener():
	proxies = _get_proxies()
	if proxies:
		proxy = urllib2.ProxyHandler(proxies)
		opener = urllib2.build_opener(proxy)
		urllib2.install_opener(opener)
_install_opener()


def _download_url(url, filepath, progress=_dummy_progress):
	'''Download specified URL to the given location on the hard disk.
	Optionally with a callback function that receives the parameters (bytes_downloaded, bytes_total).'''

	def _callback_wrapper(nblocks, block_size, total_size):
		progress(min(total_size, nblocks * block_size), total_size)

	urlopener = urllib.FancyURLopener(proxies=_get_proxies())
	urlopener.retrieve(url, filepath, _callback_wrapper)


def _download_file(filename, hash_value=None, progress=_dummy_progress):
	'''Download the file at the URL specified by ucc/image/path.
	Optionally the sha256 hash sum is validated, if hash_value is specified.'''

	# remove existing file
	outfile = os.path.join(UCC_IMAGE_DIRECTORY, filename)
	if os.path.exists(outfile):
		log_info(_('File %s already exists, removing it for new download.') % filename)
		os.remove(outfile)

	# split progress into 50% for download and 50% for hash validation (if hash is given)
	_progress = progress
	if hash_value:
		def _progress(current_size, file_size):
			progress(0.8 * current_size, file_size)

	# download
	try:
		url = '%s/%s' % (UCC_BASE_URL, filename)
		_download_url(url, outfile, _progress)
	except IOError as exc:
		_exit(_('An error occured while downloading image %s:\n%s') % (url, exc))

	# validate hash
	if hash_value:
		def _progress(current_size, file_size):
			progress(0.2 * current_size + 0.8 * file_size, file_size)

		log_info(_('Validating hash value of file %s') % filename)
		digest = _sha256(outfile, _progress)
		if digest != hash_value:
			_exit(_('Invalid hash value for downloaded file %s!\nHash expected: %s\nHash received: %s') % (filename, hash_value, digest))


def _run_join_script(join_script, username=None, password=None):
	'''Calls the specified join script with username and password (if specified).'''

	systemrole = configRegistry['server/role']
	is_master = systemrole == 'domaincontroller_master' or systemrole == 'domaincontroller_backup'

	# do not execute join script on non-master systems and without specified credentials
	if not is_master and not (username and password):
		log_warn(_('Please run univention-run-join-scripts manually to execute a new join script which has been registered for this UCC image.'))
		return False

	# execute join script
	with tempfile.NamedTemporaryFile() as passwordFile:
		cmd = ['/usr/sbin/univention-run-join-scripts']
		if not is_master and username and password:
			# credentials are provided
			passwordFile.write('%s' % password)
			passwordFile.flush()
			cmd += ['-dcaccount', username, '-dcpwd', passwordFile.name]

		# if scripts are provided only execute them instead of running all join scripts
		cmd += ['--run-scripts', join_script]
		log_process(_('Executing join script %s') % join_script)
		process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = process.communicate()

	if stdout:
		log_process(_('Join script output (stdout):\n%s') % stdout)
	if stderr:
		log_warn(_('Join script output (stderr):\n%s') % stderr)
	if process.returncode != 0:
		return False


class Progress(object):
	def __init__(self, max_steps=100):
		self.progress_file = None
		self.reset(max_steps)

	def _remove_progress_file(self):
		if self.progress_file:
			try:
				# close handle
				if self._progress_file_handle:
					self._progress_file_handle.close()
					self._progress_file_handle = None

				# remove file
				log_info(_('Removing progress file: %s') % self.progress_file)
				os.remove(self.progress_file)
			except (IOError, OSError) as exc:
				log_warn(_('Failed to remove progress file %s with following error: %s') % (self.progress_file, exc))
			self.progress_file = None

	def _open_progress_file(self):
		if not self._progress_file_handle:
			self._progress_file_handle = open(self.progress_file, 'w')
			os.chmod(self.progress_file, 0644)
		self._progress_file_handle.seek(0)
		return self._progress_file_handle

	def _update_progress_file(self):
		if not self.progress_file:
			return
		percent = (100.0 * self.steps) / self.max_steps
		try:
			log_info(_('Updating progress file: %s') % self.progress_file)
			progress_file = self._open_progress_file()
			progress_file.write('%s\t%s\t%s' % (os.getpid(), percent, self.message))
			progress_file.truncate()
			progress_file.flush()
		except (IOError, OSError) as exc:
			log_warn(_('Writing progress file %s failed: %s') % (self.progress_file, exc))

	def reset(self, max_steps=100):
		self.max_steps = max_steps
		self.finished = False
		self.message = _('Initializing')
		self.steps = 0
		self.substeps = 0
		self.errors = []
		self._last_logged_step = -1
		self._last_logged_substep = -1
		self._remove_progress_file()
		self.progress_file = None
		self._progress_file_handle = None

	def finish(self):
		log_process(_('Finished'))
		self.finished = True
		self._remove_progress_file()

	def error(self, err, finish=True):
		log_error(err)
		self.errors.append(err)
		if finish:
			self.finish()

	def info(self, message):
		self.message = message
		self.substeps = 0
		log_process(message)
		self._update_progress_file()

	def advance(self, steps, substeps=-1):
		self.steps = steps
		self.substeps = substeps

		# do not log every step
		if abs(self._last_logged_step - steps) < 1 and abs(self._last_logged_substep - substeps) < 1:
			return

		percent = min(100.0, (100.0 * steps) / self.max_steps)
		if substeps < 0:
			log_process(_('Overall: % 6.1f%%') % percent)
		else:
			percent_sub = min(100.0, (100.0 * substeps) / self.max_steps)
			log_process(_('Overall: % 6.1f%%  current task: % 6.1f%%') % (percent, percent_sub))

		self._last_logged_step = steps
		self._last_logged_substep = substeps
		self._update_progress_file()


class UCCImage(object):
	def __init__(self, spec_url):
		if not spec_url.endswith(".spec"):
			spec_url += '.spec'

		self._base = os.path.dirname(spec_url)
		self._spec_file = os.path.basename(spec_url)
		self._spec_url = spec_url
		self.spec = {}
		self._read_spec_file(spec_url)
		self._total_download_size = None
		self._file_sizes = None
		if spec_url.startswith('http://') or spec_url.startswith('https://'):
			self.spec['location'] = 'online'
		else:
			self.spec['location'] = 'local'

	def _read_spec_file(self, spec_url):
		if self._spec_url.startswith('http://') or self._spec_url.startswith('https://'):
			_get_file_size(self.spec_file)  # raises an error if file does not exist
		stream = urllib.urlopen(spec_url, proxies=_get_proxies())
		self.spec = yaml.load(stream)
		stream.close()
		self.validate()

	def _fix_access_rights(self):
		log_info(_('Adjusting access rights of image files to 0644 ...'))
		files = [ivalue for ikey, ivalue in self.spec.iteritems() if ikey.startswith('file-')]
		files.append(self.spec_file)
		files.append(self.file)
		for ifile in files:
			ipath = os.path.join(UCC_IMAGE_DIRECTORY, ifile)
			if not os.path.exists(ipath):
				continue
			log_info('  chmod 0644 %s' % ifile)
			os.chmod(ipath, 0644)

	def validate(self, be_strict=False):
		# following fields are not absolutely required:
		for i in ['hash-img', 'hash-kernel', 'hash-initrd', 'hash-md5', 'hash-reg', 'file-img', 'file-initrd', 'file-kernel', 'file-md5', 'file-reg']:
			if i not in self.spec:
				raise ValueError(_('Malformed spec file %s, missing entry "%s"!') % (self.spec_file, i))

		# these fields are needed for display purposes
		for i in ['version', 'description', 'id']:
			if i not in self.spec:
				msg = _('Entry "%s" not specified in spec file %s!') % (i, self.spec_file)
				if be_strict:
					raise ValueError(msg)
				else:
					log_warn(msg)

	@property
	def id(self):
		return self.spec.get('id', '')

	@property
	def version(self):
		return str(self.get('version'))

	@property
	def description(self):
		return self.spec.get('description', self.file)

	@property
	def file(self):
		'''Image file name without .xz file ending.'''
		img_name = self.get('file-img')
		if img_name.endswith('.xz'):
			img_name = img_name[:-3]
		return img_name

	@property
	def spec_file(self):
		return self._spec_file

	@property
	def join_script(self):
		return self.get('file-reg')

	@property
	def location(self):
		return self.get('location')

	@property
	def progress_file(self):
		return '%s.progress' % self.spec_file

	@property
	def is_other_download_running(self):
		progress_file_path = os.path.join(UCC_IMAGE_DIRECTORY, self.progress_file)
		if not os.path.exists(progress_file_path):
			return False
		try:
			parts = []
			with open(progress_file_path) as progress_file:
				line = progress_file.read()
				parts = line.split('\t', 2)

			if len(parts) != 3:
				# wrong format
				return False

			# see whether process exists
			pid = int(parts[0])
			proc = psutil.Process(pid)

			# make sure that last modification time is at least 5 min ago
			file_mod_time = os.stat(progress_file_path).st_mtime
			last_time = (time.time() - file_mod_time) / 60  # time in minutes
			return last_time < 5
		except psutil.NoSuchProcess as exc:
			# process is not running anymore
			pass
		except ValueError as exc:
			# wrong format, probably PID
			pass
		except (IOError, OSError) as exc:
			log_warn(_('Failed to check whether another download process is running: %s') % exc)
		return False

	@property
	def status(self):
		'''The status of the ucc image is determined by the following states:
		downloading, installed, incomplete, available.'''

		# get the status of the UCC image
		if self.is_other_download_running:
			return 'downloading'

		files = [self.file, self.spec_file, self.join_script]
		files_exist = [os.path.exists(os.path.join(UCC_IMAGE_DIRECTORY, ifile)) for ifile in files]
		if all(files_exist):
			return 'installed'
		if any(files_exist):
			return 'incomplete'
		return 'available'

	def get(self, key):
		'''Helper function to access configuration elements of the image's spec file.'''
		return self.spec.get(key.lower(), 'NULL')

	def to_dict(self):
		return {
			'id': self.id,
			'version': self.version,
			'description': self.description,
			'file': self.file,
			'spec_file': self.spec_file,
			'location': self.location,
		}

	def __str__(self):
		return '<%s %s %s [%s]>' % (self.id, self.file, self.version, self.location)

	def __repr__(self):
		return str(self)

	@property
	def file_sizes(self):
		if not self._file_sizes:
			file_keys = ('img', 'initrd', 'md5', 'kernel', 'reg')
			sizes = {}
			for ikey in file_keys:
				file_key = 'file-%s' % ikey
				sizes[ikey] = _get_file_size(self.spec[file_key])
			self._file_sizes = sizes
		return self._file_sizes

	@property
	def total_download_size(self):
		if not self._total_download_size:
			self._total_download_size = sum(self.file_sizes.values())
		return self._total_download_size

	def has_enough_disk_space(self):
		free_diskspace = _free_disk_space(UCC_IMAGE_DIRECTORY)
		# take 110% more of needed space into account as little buffer
		return (free_diskspace > 1.1 * self.total_download_size)

	def _download_spec_file(self):
		if not self.has_enough_disk_space():
			raise IOError(_('Not enough free diskspace to download the image!\nNeeded: %s\nAvailable: %s') % (self.total_download_size, _free_disk_space(UCC_IMAGE_DIRECTORY)))
		_download_file(self.spec_file)

	def _download_file(self, key, validate_hash=True, progress=_dummy_progress):
		file_key = 'file-%s' % key
		hash_value = None
		if validate_hash:
			hash_key = 'hash-%s' % key
			hash_value = self.get(hash_key)

		_download_file(self.get(file_key), hash_value, progress)

	def _unpack(self, progress=_dummy_progress):
		img_file = self.get('file-img')
		if img_file.endswith('.xz'):
			img_path = os.path.join(UCC_IMAGE_DIRECTORY, img_file)
			_unxz(img_path, False, progress)

	def remove_files(self):
		def _remove(filename):
			path = os.path.join(UCC_IMAGE_DIRECTORY, filename)
			if os.path.exists(path):
				try:
					log_info(_('Removing file %s') % path)
					os.remove(path)
				except (IOError, OSError) as exc:
					log_warn(_('Ignoring removal failure of file %s: %s') % (path, exc))

		log_process(_('Removing all files related to image...'))
		for ikey, ivalue in self.spec.iteritems():
			if not ikey.startswith('file-'):
				continue
			_remove(ivalue)

		# remove iamge and compressed, left over image file
		_remove(self.file)
		_remove('%s.xz' % self.file)

		# remove installed join script
		join_script_path = os.path.join('/usr/lib/univention-install/', self.join_script)
		_remove(join_script_path)

		# remove spec file itself
		_remove(self.spec_file)


	def download(self, validate_hash=True, progress=Progress()):
		'''Download spec file, image file and all other related images. Unpack image if necessary.'''

		try:
			# make sure that a temporary progress file is being updated, as well
			progress.progress_file = os.path.join(UCC_IMAGE_DIRECTORY, self.progress_file)

			# download spec file
			self._download_spec_file()

			# compute file size
			sizes = self.file_sizes
			total_progress = 0
			log_info(_('Need to download in total %d files and %.1f MB of data.') % (len(sizes), self.total_download_size / 1000**2))

			# download all files -> 70%
			for ikey, isize in sizes.iteritems():
				ifile = self.get('file-%s' % ikey)
				progress.info(_('Downloading file %s [%.1f MB]') % (ifile, isize / 1000**2))

				file_percent = (70.0 * isize) / self.total_download_size
				self._download_file(ikey, validate_hash, _advance_wrapper(file_percent, total_progress, progress))
				total_progress += file_percent

			# place join script into correct directory
			join_script_src_path = os.path.join(UCC_IMAGE_DIRECTORY, self.join_script)
			join_script_dest_path = os.path.join('/usr/lib/univention-install/', self.join_script)
			log_info(_('Copy join script to %s') % join_script_dest_path)
			shutil.copy(join_script_src_path, join_script_dest_path)
			os.chmod(join_script_dest_path, 0755)

			# unpack UCC image -> 30%
			progress.info(_('Unpacking image file %s') % self.file)
			self._unpack(_advance_wrapper(30.0, total_progress, progress))
			progress.advance(100.0)
			progress.finish()

			self._fix_access_rights()
		except Exception as exc:
			# remove already partly downloaded files
			self.remove_files()
			# re-raise exception
			raise

	def set_root_password(self, interactive_rootpw=False):
		'''Calls ucc-image-root-password for the image'''
		cmd = ['/usr/sbin/ucc-image-root-password', '-i', os.path.join(UCC_IMAGE_DIRECTORY, self.file)]
		if interactive_rootpw:
			print _('Setting root password in the downloaded image. Please enter the password:')
			cmd += ['-p']
		else:
			log_process(_('Setting root password in the image to the root password of the current system'))

		ret = subprocess.call(cmd)
		log_info(str(cmd))
		if ret != 0:
			log_error(_('Root password could not be set!'))

	def run_join_script(self, username=None, password=None):
		return _run_join_script(self.join_script, username, password)


def _check_ucr_variables():
	if not configRegistry['ucc/image/path']:
		_exit(_('The UCR variable ucc/image/path must be set!'), True)

	if not os.path.exists(UCC_IMAGE_DIRECTORY):
		_exit(_('UCC image path %s does not exists!') % UCC_IMAGE_DIRECTORY, True)


def download_ucc_image(spec_file, validate_hash=True, interactive_rootpw=False, username=None, password=None, progress=Progress()):
	'''Convenience function, given a spec file, downloads all associated files and unpacks the image.'''
	try:
		_check_ucr_variables()

		progress.info(_('Downloading and reading image file %s') % spec_file)
		spec_url = '%s/%s' % (UCC_BASE_URL, spec_file)
		img = UCCImage(spec_url)
		if img.is_other_download_running:
			raise RuntimeError(_('Another process is currently downloading the UCC image %s.') % img.file)
		img.download(validate_hash, progress)

		progress.info(_('Setting root password for image %s') % img.file)
		img.set_root_password(interactive_rootpw)

		progress.info(_('Running join script %s') % img.join_script)
		img.run_join_script(username, password)

		progress.info(_('Finished.'))
	except (IOError, ValueError, OSError, RuntimeError, httplib.HTTPException) as exc:
		progress.error(_('Image data of spec file %s could not be downloaded from server:\n%s\n') % (spec_file, exc))
		log_error(_('Error downloading image data from server:\n%s') % ''.join(traceback.format_tb(sys.exc_info()[2])))


def get_local_ucc_images():
	'''Get a list of all locally installed UCC images represented by a dict with the spec-file content.'''

	_check_ucr_variables()

	def _read(spec_file):
		file_path = os.path.join(UCC_IMAGE_DIRECTORY, spec_file)
		return UCCImage(file_path)

	all_files = os.listdir(UCC_IMAGE_DIRECTORY)
	specs = [_read(i) for i in all_files if i.endswith('.spec')]
	return specs


def is_image_downloading(spec_file):
	file_path = os.path.join(UCC_IMAGE_DIRECTORY, spec_file)
	image = UCCImage(file_path)
	return image.is_other_download_running


_regWhiteSpace = re.compile(r'\s+')
def get_online_ucc_images():
	'''Get a list of all images that are available online.'''

	_check_ucr_variables()
	index = []
	stream = None
	try:
		_get_file_size(UCC_IMAGE_INDEX_FILE)  # throws a HTTPException if URL does not exist
	except httplib.HTTPException as exc:
		raise ValueError(_('No valid UCC server specified via UCR variable ucc/image/download/url. The image index file could not be opened!'))

	try:
		stream = urllib.urlopen(UCC_IMAGE_INDEX_URL, proxies=_get_proxies())
		for line in stream:
			line = line.strip()
			if line.startswith('#'):
				continue

			parts = _regWhiteSpace.split(line)
			if not parts:
				continue

			# try to read in image spec file
			try:
				spec_url = '%s/%s' % (UCC_BASE_URL, parts[0])
				index.append(UCCImage(spec_url))
			except (IOError, RuntimeError, httplib.HTTPException) as exc:
				log_warn(_('Failed to read spec file %s ... ignoring: %s') % (spec_url, exc))

	finally:
		if stream:
			stream.close()
	return index


def get_latest_online_ucc_image():
	'''Get a list of only the latest images of a kind that are available online.'''

	images = get_online_ucc_images()
	versions = {}
	for i in images:
		versions.setdefault(i.id, []).append(i)
	latest_images = []
	for iimages in versions.itervalues():
		iimages.sort(cmp=lambda x, y: -cmp(x.version, y.version))
		latest_images.append(iimages[0])
	return latest_images


def remove_ucc_image(spec_file):
	'''Remove the specified UCC image.'''

	_check_ucr_variables()
	log_process(_('Removing image %s') % spec_file)
	spec_file_path = os.path.join(UCC_IMAGE_DIRECTORY, spec_file)
	img = UCCImage(spec_file_path)
	if img.is_other_download_running:
		raise RuntimeError(_('Another process is currently downloading the UCC image %s.') % img.file)
	img.remove_files()


