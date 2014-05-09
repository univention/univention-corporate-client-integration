#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Download and management of UCC client images
#
# Copyright 2014 Univention GmbH
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

from threading import Thread
import time
import traceback
import sys

from univention.lib.i18n import Translation
from univention.management.console.modules import UMC_OptionTypeError, Base
from univention.management.console.log import MODULE
from univention.management.console.modules.decorators import simple_response

import ucc.images as ucc_images

_ = Translation('ucc-umc-images').translate

class Progress(ucc_images.Progress):
	pass

class Instance(Base):
	def init(self):
		self.progress_state = Progress()

	@simple_response
	def progress(self):
		time.sleep(1)
		return self.progress_state.poll()

	@simple_response
	def query(self):
		images = ucc_images.get_local_ucc_images()
		images += ucc_images.get_online_ucc_images()
		MODULE.info('Images: %s' % images)

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
			idict = i.to_dict()

			# set status
			is_deprecated = images_grouped_by_id[i.id][0] != i
			if is_deprecated:
				idict['status'] = 'deprecated'
			elif i.location == 'local':
				idict['status'] = 'installed'
			else:
				idict['status'] = 'available'

			result.append(idict)

		return result

	@simple_response
	def download(self, image=''):
		# start download process in a thread
		def _run():
			try:
				ucc_images.download_ucc_image(image, username=self._username, password=self._password, progress=self.progress_state)
			except Exception as exc:
				# be sure to log any error that might occur (albeit it should not)
				# ... otherwise the Thread will let disappear any exception
				self.progress_state.error_handler(_('Unexpected error: %s') % exc)
				self.progress_state.critical_handler(True)
				MODULE.error('Unexpected error:\n%s' % ''.join(traceback.format_tb(sys.exc_info()[2])))

		thread = Thread(target=_run)
		thread.start()
		return True

