# -*- coding: utf-8 -*-
#
# Univention Corporate Client
#  Syntax extensions
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

import univention.admin.localization
import univention.admin.syntax

translation = univention.admin.localization.translation('univention.admin.handlers.ucc-policies')
_ = translation.translate


class uccBoot(univention.admin.syntax.select):
	choices = [
	    ('overlayfs', _('Live system')),
	    ('localboot', _('Local boot')),
	    ('none', _('Image boot without update check')),
	    ('rollout', _('Image boot with update check')),
	    ('repartition', _('Installation with repartitioning and image rollout')),
	]


class uccImage(univention.admin.syntax.UDM_Objects):
	udm_modules = ('settings/ucc_image', )
	regex = None
	key = '%(name)s'
	label = '%(name)s'
	simple = True
	empty_value = False


class uccSessions(univention.admin.syntax.UDM_Objects):
	udm_modules = ('settings/ucc_session',)
	empty_value = True


class uccUserFixedAttributes(univention.admin.syntax.select):
	name = 'slavePackagesFixedAttributes'
	choices = [
		('univentionCorporateClientUserSession', _('Force this session for user logins')),
		('univentionCorporateClientUserWindowsDomain', _('Windows domain')),
		('univentionCorporateClientUserWindowsTerminalserver', _('Windows terminal server')),
	]


class uccDesktopFixedAttributes(univention.admin.syntax.select):
	name = 'uccDesktopFixedAttributes'
	choices = [
		('environmentVars', _('UCC desktop environment variables'))
	]


class uccDesktopEnvVar(complex):
	subsyntaxes = ((_('Variable'), string), (_('Value'), string))


class uccImageServer(UDM_Attribute):
	udm_module = 'computers/computer'
	udm_filter = '(&(objectClass=univentionHost)(service=UCC))'
	empty_value = True
	attribute = 'ip'
	label_format = '%(name)s: %($attribute$)s'
