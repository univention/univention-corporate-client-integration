#!/usr/bin/python2.6
#
# Copyright 2012-2014 Univention GmbH
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

import os.path
import shutil
import tempfile
import subprocess

from univention.management.console.modules import Base
from univention.management.console.modules import UMC_CommandError
from univention.management.console.log import MODULE
from univention.management.console.config import ucr
from univention.management.console.modules.decorators import simple_response, sanitize, file_upload
from univention.management.console.modules.mixins import ProgressMixin
from univention.management.console.modules.sanitizers import DictSanitizer, StringSanitizer, BooleanSanitizer
from univention.management.console.protocol.session import TEMPUPLOADDIR

import univention.admin.modules as udm_modules
import univention.admin.objects as udm_objects
import ucc.images as ucc_images

from univention.lib.i18n import Translation

import util

_ = Translation( 'ucc-umc-setup' ).translate


class Instance(Base, ProgressMixin):
	def init(self):
		util.set_credentials(self._user_dn, self._password)
		self._citrix_receiver_path = None

	def destroy(self):
		if self._citrix_receiver_path and os.path.exists(self._citrix_receiver_path):
			MODULE.info('Remove uploaded citrix receiver debian package: %s' % self._citrix_receiver_path)
			shutil.rmtree(self._citrix_receiver_path, ignore_errors=True)
			self._citrix_receiver_path = None

	@simple_response
	def info_networks(self):
		ldap_connection = util.get_ldap_connection()
		networks = udm_modules.lookup('networks/network', None, ldap_connection, base=ucr['ldap/base'], scope='sub')
		result = []
		for inet in networks:
			ilabel = '{name} ({network})'.format(**inet.info)
			result.append({
				'id': inet.dn,
				'label': ilabel
			})
		return result

	@simple_response
	def info_ucc_images(self):
		images = ucc_images.get_local_ucc_images()
		result = []
		for iimg in images:
			result.append({
				'id': iimg.file,
				'label': iimg.description,
			})
		return result

	@simple_response
	def info(self):
		ldap_connection = util.get_ldap_connection()
		dhcp_routing_obj = util.get_dhcp_routing_policy(ldap_connection)
		ucr_policy_obj = udm_objects.get(udm_modules.get('policies/registry'), None, ldap_connection, None, util.UCR_VARIABLE_POLICY_DN)
		return {
			'gateway': ucr.get('gateway'),
			'dhcp_routing_policy': dhcp_routing_obj and dhcp_routing_obj.dn,
			'ucr_policy_exists': ucr_policy_obj.exists(),
		}

	@file_upload
	def upload_deb(self, request):
		# make sure that we got a list
		if not isinstance(request.options, (tuple, list)):
			raise UMC_CommandError(_('Expected list of dicts, but got: %s') % str(request.options) )
		file_info = request.options[0]
		if not ('tmpfile' in file_info and 'filename' in file_info):
			raise UMC_CommandError(_('Invalid upload data, got: %s') % str(file_info) )

		# check for fake uploads
		tmpfile = file_info['tmpfile']
		if not os.path.realpath(tmpfile).startswith(TEMPUPLOADDIR):
			raise UMC_CommandError(_('Invalid upload file path'))

		# check for correct file type
		filename = file_info['filename']
		if not filename.endswith('_i386.deb'):
			raise UMC_CommandError(_('Invalid file type! File needs to be a Debian archive (.deb) for 32 bit architecture.'))

		# we got an uploaded file with the following properties:
		#   name, filename, tmpfile
		dest_path = tempfile.mktemp(suffix='_i386.deb')
		MODULE.info('Received file "%s", saving it to "%s"' % (tmpfile, dest_path))
		shutil.move(tmpfile, dest_path)
		self._citrix_receiver_path = dest_path

		# done
		self.finished( request.id, None )

	@sanitize(
		thinclient=BooleanSanitizer(),
		fatclient=BooleanSanitizer(),
		downloadThinClientImage=BooleanSanitizer(),
		downloadFatClientImage=BooleanSanitizer(),
		network=DictSanitizer({
			'address': StringSanitizer(),
			'mask': StringSanitizer(),
			'firstIP': StringSanitizer(),
			'lastIP': StringSanitizer(),
			'existingDN': StringSanitizer(),
		}, allow_other_keys=False),
		gateway=StringSanitizer(),
		rdp=DictSanitizer({
			'host': StringSanitizer(),
			'domain': StringSanitizer(),
			'sound': BooleanSanitizer(),
			'usb': BooleanSanitizer(),
		}, allow_other_keys=False),
		citrix=DictSanitizer({
			'image': StringSanitizer(),
			'url': StringSanitizer(regexp_pattern='^https?://'),
			'autoLogin': BooleanSanitizer(),
		}, allow_other_keys=False),
		browser=DictSanitizer({
			'url': StringSanitizer(regexp_pattern='^https?://'),
		}, allow_other_keys=False),
	)
	@simple_response(with_progress=True)
	def apply(self, gateway=None, rdp=None, citrix=None, thinclient=False, fatclient=False, downloadThinClientImage=False, downloadFatClientImage=False, network=None, browser=None, defaultSession=None, progress=None):
		ldap_connection = util.get_ldap_connection()
		progress.title =_('Applying UCC configuration settings')
		progress.total = 100

		# make sure the citrix receiver debian package has been uploaded
		if citrix and not self._citrix_receiver_path:
			raise UMC_CommandError(_('The Debian package of the Citrix Receiver could not be found. Please make sure that the file has been uploaded.'))

		def _progress(steps, msg):
			progress.current = steps
			progress.message = msg

		# create network obj and make sure that the network obj is linked to the DHCP service
		_progress(0, _('Network settings...'))
		if network:
			if network.get('existingDN'):
				util.set_dhcp_service_for_network(network.get('existingDN'), ldap_connection)
			else:
				#TODO: error handling
				util.set_network(network.get('address'), network.get('mask'), network.get('firstIP'), network.get('lastIP'), ldap_connection)

		# DHCP routing policy for gateway
		dhcp_routing_obj = util.get_dhcp_routing_policy(ldap_connection)
		if not dhcp_routing_obj and gateway:
			util.set_dhcp_routing(gateway, ldap_connection)

		ucr_variables = {}
		thinclient_ucr_variables = {}
		fatclient_ucr_variables = {}
		if browser:
			_progress(2, _('Browser settings'))
			# web browser access
			ucr_variables['firefox/startsite'] = browser.get('url', '')
			# default session (might be overwritten by RDP or Citrix)
			thinclient_ucr_variables['lightdm/sessiondefault'] = 'firefox'

		if rdp:
			_progress(4, _('RDP terminal server settings'))
			# RDP terminal server + domain name
			util.set_rdp_values(rdp.get('domain', ''), rdp.get('host', ''), ldap_connection)
			# RDP configuration -> usb and sound
			ucr_variables['rdp/redirectdisk'] = util.bool2str(rdp.get('usb'))
			ucr_variables['rdp/disable-sound'] = util.bool2str(not rdp.get('sound'))
			# default session (might be overwritten by Citrix)
			thinclient_ucr_variables['lightdm/sessiondefault'] = 'RDP'

		if citrix:
			_progress(6, _('Citrix XenApp settings'))

			# Citrix configuration
			ucr_variables['citrix/webinterface'] = citrix.get('url', '')
			ucr_variables['citrix/accepteula'] = 'true'
			thinclient_ucr_variables['lightdm/sessiondefault'] = 'XenApp'
			if citrix.get('autoLogin'):
				thinclient_ucr_variables['lightdm/autologin/session'] = 'XenApp'
				thinclient_ucr_variables['lightdm/autologin'] = 'true'

		# save UCR variables as policy
		_progress(8, _('Setting UCR variables'))
		util.set_ucr_policy_variables(ucr_variables, thinclient_ucr_variables, fatclient_ucr_variables, ldap_connection)

		# query the latest ucc image file
		online_images = ucc_images.get_latest_online_ucc_image()
		thinclient_image = [i for i in online_images if i.id == 'ucc20thin']
		desktop_image = [i for i in online_images if i.id == 'ucc20desktop']
		if not thinclient_image or not desktop_image:
			return { 'success': False, 'error': _('UCC images cannot be downloaded! Please check your internet connection.') }
		thinclient_image = thinclient_image[0]
		desktop_image = desktop_image[0]

		# download image(s)
		download_percentage = 60 if citrix else 90
		download_percentage_third = download_percentage / 3
		if downloadThinClientImage and downloadFatClientImage:
			progress_wrapper = util.ProgressWrapper(progress, download_percentage_third, 10)
			ucc_images.download_ucc_image(thinclient_image.spec_file, username=self._username, password=self._password, progress=progress_wrapper)
			progress_wrapper = util.ProgressWrapper(progress, download_percentage_third * 2, 10 + download_percentage_third)
			ucc_images.download_ucc_image(desktop_image.spec_file, username=self._username, password=self._password, progress=progress_wrapper)
		elif downloadThinClientImage:
			progress_wrapper = util.ProgressWrapper(progress, download_percentage, 10)
			ucc_images.download_ucc_image(thinclient_image.spec_file, username=self._username, password=self._password, progress=progress_wrapper)
		elif downloadFatClientImage:
			progress_wrapper = util.ProgressWrapper(progress, download_percentage, 10)
			ucc_images.download_ucc_image(desktop_image.spec_file, username=self._username, password=self._password, progress=progress_wrapper)

		# install citrix receiver in UCC image
		if citrix:
			_progress(70, _('Installing Citrix Receiver application in image file. This might take a few minutes to complete.'))
			ucc_image_choice = citrix.get('image', '_DEFAULT_')
			if ucc_image_choice == '_DEFAULT_':
				ucc_image_choice = thinclient_image.file
			ucc_image = [i for i in ucc_images.get_local_ucc_images() if i.file == ucc_image_choice]
			ucc_image = ucc_image[0] if ucc_image else None
			ucc_image_path = os.path.join(ucc_images.UCC_IMAGE_DIRECTORY, ucc_image.file) if ucc_image else None
			if not ucc_image or not os.path.exists(ucc_image_path):
				MODULE.warn('Chosen UCC image %s for Citrix Receiver installation could not be found' % ucc_image_choice)
				raise UMC_CommandError(_('The chosen UCC image file %s could not be found on the local system!' % ucc_image_choice))

			subprocess.call(['/usr/sbin/ucc-image-add-citrix-receiver', '--uccimage', ucc_image_path, '--debpackage', self._citrix_receiver_path])

		return { 'success': True }

