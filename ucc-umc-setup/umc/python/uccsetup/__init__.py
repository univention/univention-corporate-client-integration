#!/usr/bin/python2.7
#
# Copyright 2012-2016 Univention GmbH
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

from univention.management.console.log import MODULE
from univention.management.console.config import ucr
from univention.management.console.modules import Base, UMC_Error
from univention.management.console.modules.decorators import simple_response, sanitize, file_upload, require_password
from univention.management.console.modules.mixins import ProgressMixin
from univention.management.console.modules.sanitizers import DictSanitizer, StringSanitizer, BooleanSanitizer
from univention.management.console.protocol.session import TEMPUPLOADDIR

import univention.admin.modules as udm_modules
import ucc.images as ucc_images
from univention.config_registry import ConfigRegistry

from univention.lib.i18n import Translation
_ = Translation('ucc-umc-setup').translate

import util


class Instance(Base, ProgressMixin):
	def init(self):
		util.set_bind_function(self.bind_user_connection)

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
		rdp_host, rdp_domain = util.get_rdp_values(ldap_connection)
		ucr_policy = ConfigRegistry()
		ucr_policy.update(util.get_ucr_policy_variables(ldap_connection))  # hack to access the method is_true()
		thinclient_image, desktop_image = util.get_latest_ucc_images()
		return {
			'gateway': ucr.get('gateway', ''),
			'dhcp_routing_policy': dhcp_routing_obj and dhcp_routing_obj.dn,
			'has_installed_ucc_desktop': util.has_installed_ucc_desktop(),
			'has_installed_ucc_thinclient': util.has_installed_ucc_thinclient(),
			'rdp_usb': ucr_policy.is_true('rdp/redirectdisk'),
			'rdp_sound': ucr_policy.is_false('rdp/disable-sound'),
			'rdp_host': rdp_host,
			'rdp_domain': rdp_domain,
			'citrix_accepteula': ucr_policy.is_true('citrix/accepteula'),
			'citrix_receiver_deb_package': os.path.basename(util.get_citrix_receiver_package_path()),
			'citrix_url': ucr_policy.get('citrix/webinterface', ''),
			'citrix_autologin': ucr_policy.get('lightdm/autologin/session') == 'XenApp' and ucr_policy.is_true('lightdm/autologin'),
			'browser_url': ucr_policy.get('firefox/startsite', ''),
			'download_size_thinclient': thinclient_image.total_download_size,
			'download_size_desktop': desktop_image.total_download_size,
		}

	@file_upload
	def upload_deb(self, request):
		# make sure that we got a list
		if not isinstance(request.options, (tuple, list)):
			raise UMC_Error(_('Expected list of dicts, but got: %s') % str(request.options))
		file_info = request.options[0]
		if not ('tmpfile' in file_info and 'filename' in file_info):
			raise UMC_Error(_('Invalid upload data, got: %s') % str(file_info))

		# check for fake uploads
		tmpfile = file_info['tmpfile']
		if not os.path.realpath(tmpfile).startswith(TEMPUPLOADDIR):
			raise UMC_Error(_('Invalid upload file path'))

		# check for correct file type
		filename = file_info['filename']
		if not filename.endswith('_i386.deb'):
			raise UMC_Error(_('Invalid file type! File needs to be a Debian archive (.deb) for 32 bit architecture.'))

		# we got an uploaded file with the following properties:
		#   name, filename, tmpfile
		util.remove_citrix_receiver_package()
		dest_file = os.path.join(ucc_images.UCC_IMAGE_DIRECTORY, filename)
		MODULE.info('Received file "%s", saving it to "%s"' % (tmpfile, dest_file))
		shutil.move(tmpfile, dest_file)
		os.chmod(dest_file, 0644)

		# done
		self.finished(request.id, None)

	@require_password
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
			'customReceiver': BooleanSanitizer(),
		}, allow_other_keys=False),
		browser=DictSanitizer({
			'url': StringSanitizer(regexp_pattern='^https?://'),
		}, allow_other_keys=False),
	)
	@simple_response(with_progress=True)
	def apply(self, gateway=None, rdp=None, citrix=None, thinclient=False, fatclient=False, downloadThinClientImage=False, downloadFatClientImage=False, network=None, browser=None, defaultSession=None, progress=None):
		ldap_connection = util.get_ldap_connection()
		progress.title = _('Applying UCC configuration settings')
		progress.total = 100

		# make sure the citrix receiver debian package has been uploaded
		if citrix and citrix.get('customReceiver') and not util.get_citrix_receiver_package_path():
			return {'success': False, 'error': _('The Debian package of the Citrix Receiver could not be found. Please make sure that the file has been uploaded.')}

		def _progress(steps, msg):
			progress.current = steps
			progress.message = msg

		# create network obj and make sure that the network obj is linked to the DHCP service
		_progress(0, _('Network settings...'))
		if network:
			if network.get('existingDN'):
				util.set_dhcp_service_for_network(network.get('existingDN'), ldap_connection)
			else:
				try:
					util.set_network(network.get('address'), network.get('mask'), network.get('firstIP'), network.get('lastIP'), ldap_connection)
				except ValueError as exc:
					return {'success': False, 'error': str(exc)}

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
			_progress(3, _('RDP terminal server settings'))
			# RDP terminal server + domain name
			util.set_rdp_values(rdp.get('domain', ''), rdp.get('host', ''), ldap_connection)
			# RDP configuration -> usb and sound
			ucr_variables['rdp/redirectdisk'] = util.bool2str(rdp.get('usb'))
			ucr_variables['rdp/disable-sound'] = util.bool2str(not rdp.get('sound'))
			# default session (might be overwritten by Citrix)
			thinclient_ucr_variables['lightdm/sessiondefault'] = 'RDP'

		if citrix:
			_progress(4, _('Citrix XenApp settings'))

			# Citrix configuration
			ucr_variables['citrix/webinterface'] = citrix.get('url', '')
			ucr_variables['citrix/accepteula'] = 'true'
			thinclient_ucr_variables['lightdm/sessiondefault'] = 'XenApp'
			if citrix.get('autoLogin'):
				thinclient_ucr_variables['lightdm/autologin/session'] = 'XenApp'
				thinclient_ucr_variables['lightdm/autologin'] = 'true'
			else:
				thinclient_ucr_variables['lightdm/autologin/session'] = ''
				thinclient_ucr_variables['lightdm/autologin'] = 'false'

		# save UCR variables as policy
		_progress(5, _('Setting UCR variables'))
		util.set_ucr_policy_variables(ucr_variables, thinclient_ucr_variables, fatclient_ucr_variables, ldap_connection)

		# query the latest ucc image file
		thinclient_image, desktop_image = util.get_latest_ucc_images()
		if not thinclient_image or not desktop_image:
			return {'success': False, 'error': _('UCC images cannot be downloaded! Please check your internet connection.')}

		# download image(s)
		download_percentage = 60 if citrix else 90
		download_percentage_third = download_percentage / 3
		if downloadThinClientImage and downloadFatClientImage:
			progress_wrapper = util.ProgressWrapper(progress, download_percentage_third, 10)
			ucc_images.download_ucc_image(thinclient_image.spec_file, username=self.username, password=self.password, progress=progress_wrapper)
			progress_wrapper = util.ProgressWrapper(progress, download_percentage_third * 2, 10 + download_percentage_third)
			ucc_images.download_ucc_image(desktop_image.spec_file, username=self.username, password=self.password, progress=progress_wrapper)
		elif downloadThinClientImage:
			progress_wrapper = util.ProgressWrapper(progress, download_percentage, 10)
			ucc_images.download_ucc_image(thinclient_image.spec_file, username=self.username, password=self.password, progress=progress_wrapper)
		elif downloadFatClientImage:
			progress_wrapper = util.ProgressWrapper(progress, download_percentage, 10)
			ucc_images.download_ucc_image(desktop_image.spec_file, username=self.username, password=self.password, progress=progress_wrapper)

		# install citrix receiver in UCC image
		if citrix and citrix.get('customReceiver') and not progress.finished:
			_progress(70, _('Installing Citrix Receiver application in image file. This might take a few minutes to complete.'))
			ucc_image_choice = citrix.get('image', '_DEFAULT_')
			if ucc_image_choice == '_DEFAULT_':
				ucc_image_choice = thinclient_image.file
			ucc_image = [i for i in ucc_images.get_local_ucc_images() if i.file == ucc_image_choice]
			ucc_image = ucc_image[0] if ucc_image else None
			ucc_image_path = os.path.join(ucc_images.UCC_IMAGE_DIRECTORY, ucc_image.file) if ucc_image else None
			if not ucc_image or not os.path.exists(ucc_image_path):
				MODULE.warn('Chosen UCC image %s for Citrix Receiver installation could not be found' % ucc_image_choice)
				raise UMC_Error(_('The chosen UCC image file %s could not be found on the local system!') % ucc_image_choice)

			progress_wrapper = util.ProgressWrapper(progress, 30, 70)
			util.add_citrix_receiver_to_ucc_image(ucc_image_path, util.get_citrix_receiver_package_path(), progress_wrapper)


		if hasattr(progress, 'result'):
			# some error probably occurred -> return the result in the progress
			return progress.result

		return {'success': True}

