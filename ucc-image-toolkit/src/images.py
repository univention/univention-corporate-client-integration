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
	if __name__ != "__main__":
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
		percent = min(100.0, (100.0 * steps) / self.max_steps)
		percent_component = min(100.0, (100.0 * component_steps) / self.max_steps)
		if not component_steps:
			log_process('Overall: % 6.1f%%' % (percent, percent_component))
		else:
			log_process('Overall: % 6.1f%%  Component: % 6.1f%%' % (percent, percent_component))


class UCCImage(object):
	def __init__(self, spec_file):
		self._read_spec_file(spec_file)

	def _read_spec_file(self, spec_file):
		pass



def _dummy_progress(*args):
	pass


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

	return outfile


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
		raise httplib.error('Could not download file: %s - %s [%s]' % (response.status, httplib.responses.get(response.status, 'Unknown error'), url))
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
		log_info("File %s already exists, removing it for new download." % filename)
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
		_exit("An error occured while downloading image %s:\n%s\n\n... terminating" % (url, exc))

	# validate hash
	if hash_value:
		def _progress(current_size, file_size):
			progress(0.2 * current_size + 0.8 * file_size, file_size)

		log_info('Validating hash value of file %s' % filename)
		digest = _sha256(outfile, _progress)
		if digest != hash_value:
			_exit("Invalid hash value for downloaded file %s! Quitting!\nHash expected: %s\nHash received: %s" % (filename, hash_value, digest))


def _get_file_sizes(spec):
	file_keys = ('img', 'initrd', 'md5', 'kernel', 'reg')
	sizes = {}
	for ikey in file_keys:
		file_key = 'file-%s' % ikey
		sizes[ikey] = _get_file_size(spec[file_key])
	return sizes


def _read_spec_file(spec_file):
	'''Download and read the content of the spec file from the URL specified by
	ucc/image/path. The correct content of the spec file is verified and free
	disk spaces is ensured, as well.'''

	_get_file_size(spec_file)  # raises an error if file does not exist
	url = '%s/%s' % (UCC_BASE_URL, spec_file)
	stream = urllib.urlopen(url, proxies=_get_proxies())
	spec = yaml.load(stream)
	stream.close()

	for i in ['title', 'version', 'hash-img', 'hash-kernel', 'hash-initrd', 'hash-md5', 'hash-reg', 'file-img', 'file-initrd', 'file-kernel', 'file-md5', 'file-reg']:
		if not spec.get(i):
			raise ValueError('Malformed spec file, missing entry "%s"' % i)

	total_download_size = sum(_get_file_sizes(spec).values())
	free_diskspace = _free_disk_space(UCC_IMAGE_DIRECTORY)
	if (free_diskspace <= 1.1 * total_download_size):  # take 110% more of needed space into account as little buffer
		raise ValueError("Not enough free diskspace to download the image!\nNeeded: %s\nAvailable: %s" % (spec['total-size'], free_diskspace))

	# download spec file to hard disk
	_download_file(spec_file)
	return spec


def _set_rootpw(imgname, interactive_rootpw=False):
	'''Calls ucc-image-root-password for the image'''
	cmd = ["/usr/sbin/ucc-image-root-password", "-i", imgname]
	if interactive_rootpw:
		print "Setting root password in the downloaded image. Please enter the password:"
		cmd += ["-p"]
	else:
		log_process("Setting root password in the image to the root password of the current system")

	ret = subprocess.call(cmd)
	if ret != 0:
		log_warn("Root password could not be set!")


def _run_join_script(join_script):
	'''Calls the specified join script on a DC master.'''

	# make sure that the join script is executable
	join_script_path = os.path.join('/usr/lib/univention-install/', join_script)
	subprocess.call(["/bin/chmod", "a+x", join_script_path])

	# only run join script directly on master
	systemrole = configRegistry['server/role']
	if systemrole == "domaincontroller_master" or systemrole == "domaincontroller_backup":
		try:
			log_process('Run join script %s' % join_script)
			subprocess.call([join_script_path])
		except OSError as exc:
			log_error('Could not run join script %s: %s' % (join_script_path, exc))
			log_error('... ignoring')


def download_ucc_image(spec_file, validate_hash=True, interactive_rootpw=False, progress=Progress()):
	'''Convenience function, given a spec file, downloads all associated files and unpacks the image.'''

	try:
		# some basic system checks
		if not configRegistry['ucc/image/path']:
			_exit("The UCR variable ucc/image/path must be set!", True)

		if not os.path.exists(UCC_IMAGE_DIRECTORY):
			_exit("UCC image path %s does not exists!" % UCC_IMAGE_DIRECTORY, True)

		# download spec file
		progress.component_handler(_('Downloading and reading spec file %s') % spec_file)
		spec = _read_spec_file(spec_file)

		# compute file size
		sizes = _get_file_sizes(spec)
		total_download_size = sum(sizes.values())
		total_progress = 0
		log_info('Need to download in total %d files and %.1f MB of data.' % (len(sizes), total_download_size / 1000**2))

		# helper function for wrapping the step_handler method of the Progress object
		def _step_handler(percent_fraction):
			def _inner_function(current_size, file_size):
				fraction_component = float(current_size) / file_size
				percent_component = 100.0 * fraction_component
				percent_total = total_progress + fraction_component * percent_fraction
				progress.step_handler(percent_total, percent_component)

			return _inner_function

		# download all files -> 76%
		for ikey, isize in sizes.iteritems():
			file_key = 'file-%s' % ikey
			hash_value = None
			if validate_hash:
				progress.component_handler(_('Downloading and validating image file %s [%.1f MB]') % (spec['file-img'], sizes[ikey] / 1000**2))
				hash_key = 'hash-%s' % ikey
				hash_value = spec[hash_key]
			else:
				progress.component_handler(_('Downloading image file %s [%.1f MB]') % (spec['file-img'], isize / 1000**2))

			file_percent = (75.0 * isize) / total_download_size
			_download_file(spec[file_key], hash_value, _step_handler(file_percent))
			total_progress += file_percent

		# place join script into correct directory
		join_script_src_path = os.path.join(UCC_IMAGE_DIRECTORY, spec['file-reg'])
		join_script_dest_path = os.path.join('/usr/lib/univention-install/', spec['file-reg'])
		log_info('Copy join script to %s' % join_script_dest_path)
		shutil.copy(join_script_src_path, join_script_dest_path)

		# unpack UCC image -> 20%
		progress.component_handler(_('Unpacking image file %s') % spec['file-img'])
		imgname = os.path.join(UCC_IMAGE_DIRECTORY, spec['file-img'])
		if imgname.endswith('.xz'):
			imgname = _unxz(imgname, False, _step_handler(20.0))
		progress.step_handler(96.0)

		# set root password -> 2%
		progress.component_handler(_('Setting root password for image %s') % spec['file-img'])
		_set_rootpw(imgname, interactive_rootpw)
		progress.step_handler(98.0)

		# run join script -> 2%
		progress.component_handler(_('Running join script %s') % spec['file-reg'])
		_run_join_script(spec['file-reg'])
		progress.step_handler(100.0)
		log_process('Done')
	except (IOError, ValueError, OSError, RuntimeError, httplib.HTTPException) as exc:
		progress.error_handler(_("An error occured while downloading the image data (%s):\n%s\n\n... terminating") % (spec_file, exc))
		progress.critical_handler(True)


def get_installed_ucc_images():
	'''Get a list of all locally installed UCC images represented by a dict with the spec-file content.'''
	def _read(spec_file):
		file_path = os.path.join(UCC_IMAGE_DIRECTORY, spec_file)
		with open(file_path, 'r') as infile:
			spec = yaml.load(infile)
		spec['id'] = spec_file
		return spec

	all_files = os.listdir(UCC_IMAGE_DIRECTORY)
	specs = [_read(i) for i in all_files if i.endswith('.spec')]
	return specs


_regWhiteSpace = re.compile(r'\s+')
def get_available_ucc_images():
	'''Get a list of all images that are available online.'''
	stream = urllib.urlopen(UCC_IMAGE_INDEX_URL, proxies=_get_proxies())
	index = []
	try:
		for line in stream:
			line = line.strip()
			parts = _regWhiteSpace.split(line, 1)  #TODO: should be 4 later
			if len(parts) != 2:
				continue
			index.append({
				'id': parts[0],
				'title': parts[1],
			})
	finally:
		stream.close()
	return index
