#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Download and management of UCC client images
#
# Copyright 2014-2016 Univention GmbH
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

import traceback
import sys
import httplib

from univention.lib.i18n import Translation
from univention.management.console.modules import Base, UMC_CommandError
from univention.management.console.log import MODULE
from univention.management.console.modules.decorators import simple_response, require_password
from univention.management.console.modules.mixins import ProgressMixin

import ucc.images as ucc_images

_ = Translation('ucc-umc-images').translate

UCCProgress = ucc_images.Progress


class ProgressWrapper(ucc_images.Progress):

	def __init__(self, umc_progress):
		UCCProgress.__init__(self)
		self.umc_progress = umc_progress
		self.umc_progress.title = _('Downloading and registering UCC image')
		self.umc_progress.total = self.max_steps

	def finish(self):
		if not self.umc_progress.finished:
			self.umc_progress.finish_with_result({
				'success': True,
			})
		UCCProgress.finish(self)

	def error(self, err, finish=True):
		if finish:
			self.umc_progress.finish_with_result({
				'success': False,
				'error': err,
			})
		else:
			self.umc_progress.intermediate.append(err)
		UCCProgress.error(self, err, finish)

	def info(self, message):
		self.umc_progress.message = message
		UCCProgress.info(self, message)

	def advance(self, steps, substeps=-1):
		self.umc_progress.current = steps
		UCCProgress.advance(self, steps, substeps)


class Instance(Base, ProgressMixin):

	@simple_response
	def query(self):
		try:
			_images = ucc_images.get_local_ucc_images()
			_images += ucc_images.get_online_ucc_images()

			# make sure the spec files meet the strict validation
			images = []
			for i in _images:
				try:
					i.validate(True)
					images.append(i)
				except ValueError as exc:
					MODULE.warn('Ignoring image %s: %s' % (i.file, exc))
			MODULE.info('Images: %s' % images)
		except ValueError as exc:
			raise UMC_CommandError(str(exc))

		# if an image is installed, remove its online equivalent
		image_files_local = set([i.file for i in images if i.location == 'local'])
		images = [i for i in images if i.location == 'local' or i.file not in image_files_local]

		# group images by id and sort by their version
		images_grouped_by_id = {}
		for i in images:
			images_grouped_by_id.setdefault(i.id, []).append(i)
		for iimages in images_grouped_by_id.itervalues():
			iimages.sort(cmp=lambda x, y: -cmp(x.version, y.version))

		result = []
		for i in images:
			try:
				idict = i.to_dict()

				# set status
				is_deprecated = images_grouped_by_id[i.id][0] != i
				status = i.status
				if is_deprecated and status == 'installed' and i.id:
					idict['status'] = 'deprecated'
				else:
					idict['status'] = status

				# get the download size for files that can be downloaded
				if status in ('available', 'incomplete'):
					idict['size'] = i.total_download_size
				else:
					idict['size'] = 0
				result.append(idict)
			except httplib.HTTPException as exc:
				MODULE.warn('Image data for spec file %s could not be downloaded ... ignoring: %s' % (i.spec_file, exc))

		return result

	@require_password
	@simple_response(with_progress=True)
	def download(self, image='', progress=None):
		# start download process in a thread
		progress_wrapper = ProgressWrapper(progress)
		ucc_images.download_ucc_image(image, username=self.username, password=self.password, progress=progress_wrapper)
		if hasattr(progress, 'result'):
			return progress.result
		return {'success': True}

	@simple_response
	def remove(self, image=''):
		try:
			ucc_images.remove_ucc_image(image)
		except Exception as exc:
			MODULE.error('Unexpected error:\n%s' % ''.join(traceback.format_tb(sys.exc_info()[2])))
			raise UMC_CommandError(_('Unexpected error: %s') % exc)

		return True

