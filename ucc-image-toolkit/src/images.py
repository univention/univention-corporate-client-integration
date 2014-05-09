#!/usr/bin/python2.6
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
import urlparse
import contextlib
import re
import psutil
import traceback

import univention.config_registry as ucr
import univention.debug as ud
from univention.lib.i18n import Translation
_ = Translation('ucc-image-management').translate


# short cuts for logging
def log_warn(msg):
	ud.debug(ud.MODULE, ud.WARN, msg)

def log_error(msg):
	ud.debug(ud.MODULE, ud.ERROR, msg)

def log_process(msg):
	ud.debug(ud.MODULE, ud.PROCESS, msg)

def log_info(msg):
	ud.debug(ud.MODULE, ud.INFO, msg)

def _exit(msg):
	if __name__ != '__main__':
		log_error(msg)
		sys.exit(1)
	else:
		raise RuntimeError(msg)


configRegistry = ucr.ConfigRegistry()
configRegistry.load()

UCC_BASE_URL = configRegistry['ucc/image/download/url']
if UCC_BASE_URL.endswith('/'):
	# remove trailing '/'
	UCC_BASE_URL = UCC_BASE_URL[:-1]
UCC_IMAGE_DIRECTORY = configRegistry['ucc/image/path']
UCC_IMAGE_INDEX_URL = '%s/%s' % (UCC_BASE_URL, 'image-index.txt')
DEFAULT_CHUNK_SIZE = 2**13


def _dummy_progress(*args):
	pass


# helper function for wrapping the step_handler method of the Progress object
def _step_handler_wrapper(percent_fraction, total_progress, progress):
	def _step_handler(current_size, file_size):
		fraction_component = float(current_size) / file_size
		percent_component = 100.0 * fraction_component
		percent_total = total_progress + fraction_component * percent_fraction
		progress.step_handler(percent_total, percent_component)

	return _step_handler


def _free_disk_space(path):
	'''Returns the free disk space for a given path.'''
	vfs = os.statvfs(path)
	free_diskspace = vfs.f_frsize * vfs.f_bfree
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
			while True:
				compressed_data = fin.read(DEFAULT_CHUNK_SIZE)
				if not compressed_data:
					uncompressed_data = decompressor.flush()
					break

				uncompressed_data = decompressor.decompress(compressed_data)
				fout.write(uncompressed_data)
				percent = (100.0 * fin.tell()) / total_size
				progress(fin.tell(), total_size)
				del compressed_data
				del uncompressed_data

		if not keep_src_file:
			# successful decompression -> remove compressed source file
			os.remove(infile)
	finally:
		# remove extracted file in case we do not have enough space
		if os.path.exists(outfile):
			os.remove(outfile)


def _get_file_size(filename):
	'''Get the file size (in byte) for the given file at the URL specified by
	ucc/image/path via a HTTP HEAD request.'''

	url = '%s/%s' % (UCC_BASE_URL, filename)
	parts = urlparse.urlparse(url)
	if parts.scheme == 'http':
		connection = httplib.HTTPConnection(parts.hostname)
	elif parts.scheme == 'https':
		connection = httplib.HTTPSConnection(parts.hostname)
	else:
		raise httplib.error('Uknown protocol %s.' % parts.scheme)

	connection.request('HEAD', parts.path)
	response = connection.getresponse()
	if response.status >= 400:
		raise httplib.error('Could not download file (%s - %s): %s' % (response.status, httplib.responses.get(response.status, 'Unknown error'), url))
	headers = dict(response.getheaders())
	size = int(headers.get('content-length', '0'))
	return size


def _get_proxies():
	proxies = {}
	proxy_http = configRegistry.get('proxy/http')
	if proxy_http:
		proxies = {'http': proxy_http, 'https': proxy_http}
	return proxies


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
		log_info('File %s already exists, removing it for new download.' % filename)
		os.remove(outfile)

	# split progress into 50% for download and 50% for hash validation (if hash is given)
	_progress = progress
	if hash_value:
		def _progress(current_size, file_size):
			progress(0.8 * current_size, file_size)

	# download
	log_process('Downloading file %s' % filename)
	try:
		url = '%s/%s' % (UCC_BASE_URL, filename)
		log_info('Downloading %s' % url)
		_download_url(url, outfile, _progress)
	except IOError as exc:
		_exit('An error occured while downloading image %s:\n%s' % (url, exc))

	# validate hash
	if hash_value:
		def _progress(current_size, file_size):
			progress(0.2 * current_size + 0.8 * file_size, file_size)

		log_info('Validating hash value of file %s' % filename)
		digest = _sha256(outfile, _progress)
		if digest != hash_value:
			_exit('Invalid hash value for downloaded file %s! Quitting!\nHash expected: %s\nHash received: %s' % (filename, hash_value, digest))


def _run_join_script(join_script, username=None, password=None):
	'''Calls the specified join script with username and password (if specified).'''

	systemrole = configRegistry['server/role']
	is_master = systemrole == 'domaincontroller_master' or systemrole == 'domaincontroller_backup'

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
		log_process('Executing join scripts %s' % join_script)
		process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = process.communicate()

	if stdout:
		log_process('Join script output (stdout):\n%s' % stdout)
	if stderr:
		log_warn('Join script output (stderr):\n%s' % stderr)
	if process.returncode != 0:
		return False


class Progress(object):
	def __init__(self, max_steps=100):
		self.reset(max_steps)

	def reset(self, max_steps=100):
		self.max_steps = max_steps
		self.finished = False
		self.steps = 0
		self.component = _('Initializing')
		self.component_steps = 0
		self.info = ''
		self.errors = []
		self.critical = False
		self._last_logged_step = -1
		self._last_logged_component_step = -1

	def poll(self):
		return dict(
			finished=self.finished,
			steps=100 * float(self.steps) / self.max_steps,
			component=self.component,
			info=self.info,
			errors=self.errors,
			critical=self.critical,
		)

	def finish(self):
		log_process('Finished')
		self.finished = True

	def info_handler(self, info):
		log_process(info)
		self.info = info

	def error_handler(self, err):
		log_error(err)
		self.errors.append(err)

	def component_handler(self, component):
		self.component = component
		self.component_steps = 0
		log_process(component)

	def critical_handler(self, critical):
		self.critical = critical
		self.finish()

	def step_handler(self, steps, component_steps=0):
		self.steps = steps
		self.component_steps = component_steps

		# do not log every step
		if abs(self._last_logged_step - steps) < 1 and abs(self._last_logged_component_step - component_steps) < 1:
			return

		percent = min(100.0, (100.0 * steps) / self.max_steps)
		percent_component = min(100.0, (100.0 * component_steps) / self.max_steps)
		if not component_steps:
			log_process('Overall: % 6.1f%%' % percent)
		else:
			log_process('Overall: % 6.1f%%  Component: % 6.1f%%' % (percent, percent_component))

		self._last_logged_step = steps
		self._last_logged_component_step = component_steps


class UCCImage(object):
	def __init__(self, spec_url):
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
		_get_file_size(self.spec_file)  # raises an error if file does not exist
		stream = urllib.urlopen(spec_url, proxies=_get_proxies())
		self.spec = yaml.load(stream)
		stream.close()

		for i in ['version', 'description', 'id', 'hash-img', 'hash-kernel', 'hash-initrd', 'hash-md5', 'hash-reg', 'file-img', 'file-initrd', 'file-kernel', 'file-md5', 'file-reg']:
			if i not in self.spec:
				raise ValueError('Malformed spec file, missing entry %s' % i)

	@property
	def id(self):
		return self.get('id')

	@property
	def version(self):
		return str(self.get('version'))

	@property
	def description(self):
		return self.get('description')

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
			raise IOError('Not enough free diskspace to download the image!\nNeeded: %s\nAvailable: %s' % (spec['total-size'], free_diskspace))
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

	def _remove_files(self):
		def _remove(filename):
			path = os.path.join(UCC_IMAGE_DIRECTORY, filename)
			if os.path.exists(path):
				try:
					log_info('Removing file %s' % path)
					os.remove(path)
				except (IOError, OSError) as exc:
					log_warn('Ignoring removal failure of file %s: %s' % (path, exc))

		log_process('Removing all files related to image...')
		_remove(self.spec_file)
		for ikey, ivalue in self.spec.iteritems():
			if not ikey.startswith('file-'):
				continue
			_remove(ivalue)


	def download(self, validate_hash=True, progress=Progress()):
		'''Download spec file, image file and all other related images. Unpack image if necessary.'''

		try:
			# download spec file
			self._download_spec_file()

			# compute file size
			sizes = self.file_sizes
			total_progress = 0
			log_info('Need to download in total %d files and %.1f MB of data.' % (len(sizes), self.total_download_size / 1000**2))

			# download all files -> 70%
			for ikey, isize in sizes.iteritems():
				ifile = self.get('file-%s' % ikey)
				if validate_hash:
					progress.component_handler(_('Downloading and validating file %s [%.1f MB]') % (ifile, sizes[ikey] / 1000**2))
				else:
					progress.component_handler(_('Downloading file %s [%.1f MB]') % (ifile, isize / 1000**2))

				file_percent = (70.0 * isize) / self.total_download_size
				self._download_file(ikey, validate_hash, _step_handler_wrapper(file_percent, total_progress, progress))
				total_progress += file_percent

			# place join script into correct directory
			join_script_src_path = os.path.join(UCC_IMAGE_DIRECTORY, self.join_script)
			join_script_dest_path = os.path.join('/usr/lib/univention-install/', self.join_script)
			log_info('Copy join script to %s' % join_script_dest_path)
			shutil.copy(join_script_src_path, join_script_dest_path)
			subprocess.call(['/bin/chmod', 'a+x', join_script_dest_path])

			# unpack UCC image -> 30%
			progress.component_handler(_('Unpacking image file %s') % self.file)
			self._unpack(_step_handler_wrapper(30.0, total_progress, progress))
			progress.step_handler(100.0)
			progress.finish()
		except Exception as exc:
			# remove already partly downloaded files
			self._remove_files()
			# re-raise exception
			raise

	def set_root_password(self, interactive_rootpw=False):
		'''Calls ucc-image-root-password for the image'''
		cmd = ['/usr/sbin/ucc-image-root-password', '-i', self.file]
		if interactive_rootpw:
			print 'Setting root password in the downloaded image. Please enter the password:'
			cmd += ['-p']
		else:
			log_process('Setting root password in the image to the root password of the current system')

		ret = subprocess.call(cmd)
		if ret != 0:
			log_warn('Root password could not be set!')

	def run_join_script(self, username=None, password=None):
		return _run_join_script(self.join_script, username, password)


def download_ucc_image(spec_file, validate_hash=True, interactive_rootpw=False, username=None, password=None, progress=Progress()):
	'''Convenience function, given a spec file, downloads all associated files and unpacks the image.'''
	try:
		progress.reset()
		if not configRegistry['ucc/image/path']:
			_exit('The UCR variable ucc/image/path must be set!', True)

		if not os.path.exists(UCC_IMAGE_DIRECTORY):
			_exit('UCC image path %s does not exists!' % UCC_IMAGE_DIRECTORY, True)

		progress.component_handler(_('Downloading and reading img file %s') % spec_file)
		spec_url = '%s/%s' % (UCC_BASE_URL, spec_file)
		img = UCCImage(spec_url)
		img.download(validate_hash, progress)

		progress.component_handler(_('Setting root password for image %s') % img.file)
		img.set_root_password(interactive_rootpw)

		progress.component_handler(_('Running join script %s') % img.join_script)
		img.run_join_script(username, password)

		progress.component_handler(_('Finished.'))
	except (IOError, ValueError, OSError, RuntimeError, httplib.HTTPException) as exc:
		progress.error_handler(_('Image data for spec file %s could not be downloaded from server:\n%s\n') % (spec_file, exc))
		progress.critical_handler(True)
		log_error('Error downloading image data from server:\n%s' % ''.join(traceback.format_tb(sys.exc_info()[2])))


def get_local_ucc_images():
	'''Get a list of all locally installed UCC images represented by a dict with the spec-file content.'''
	def _read(spec_file):
		file_path = os.path.join(UCC_IMAGE_DIRECTORY, spec_file)
		return UCCImage(file_path)

	all_files = os.listdir(UCC_IMAGE_DIRECTORY)
	specs = [_read(i) for i in all_files if i.endswith('.spec')]
	return specs


_regWhiteSpace = re.compile(r'\s+')
def get_online_ucc_images():
	'''Get a list of all images that are available online.'''
	index = []
	stream = None
	try:
		stream = urllib.urlopen(UCC_IMAGE_INDEX_URL, proxies=_get_proxies())
		for line in stream:
			line = line.strip()
			if line.startswith('#'):
				continue

			parts = _regWhiteSpace.split(line)
			if not parts:
				continue

			# read in image spec file
			spec_url = '%s/%s' % (UCC_BASE_URL, parts[0])
			index.append(UCCImage(spec_url))
	finally:
		if stream:
			stream.close()
	return index

