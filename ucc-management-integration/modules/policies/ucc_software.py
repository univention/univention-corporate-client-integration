# -*- coding: utf-8 -*-
#
# Univention Corporate Client
#  UDM policy for software updates
#
# Copyright (C) 2013-2016 Univention GmbH
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

from univention.admin.layout import Tab, Group
import univention.admin.syntax
import univention.admin.filter
import univention.admin.handlers
import univention.admin.localization

import univention.debug

translation = univention.admin.localization.translation('univention.admin.handlers.ucc-policies')
_ = translation.translate

module = 'policies/ucc_software'
operations = ['add', 'edit', 'remove', 'search']

policy_oc = 'univentionPolicySoftwareupdates'
policy_apply_to = ["computers/ucc"]
policy_position_dn_prefix = "cn=ucc"

childs = 0
short_description = _('Policy: UCC software update settings')
policy_short_description = _('UCC software update settings')
long_description = ''
options = {
}
property_descriptions = {
	'name': univention.admin.property(
			short_description=_('Name'),
			long_description='',
			syntax=univention.admin.syntax.string,
			multivalue=False,
			options=[],
			required=True,
			may_change=False,
			identifies=True,
	),
	'uccupdate': univention.admin.property(
			short_description=_('Install available software updates'),
			long_description=_('If this option is set all available software updates for this UCC client are installed at the next system start'),
			syntax=univention.admin.syntax.boolean,
			multivalue=False,
			options=[],
			required=False,
			may_change=True,
			identifies=False
	),
	'pkgremove': univention.admin.property(
			short_description=_('Packages to be removed'),
			long_description=_('The packages configured in this policy will be removed on the next system start'),
			syntax=univention.admin.syntax.string,
			multivalue=True,
			options=[],
			required=False,
			may_change=True,
			identifies=False
	),
	'pkginstall': univention.admin.property(
			short_description=_('Packages to be installed'),
			long_description=_('The packages configured in this policy will be installed on the next system start'),
			syntax=univention.admin.syntax.string,
			multivalue=True,
			options=[],
			required=False,
			may_change=True,
			identifies=False
	),
	'requiredObjectClasses': univention.admin.property(
			short_description=_('Required object classes'),
			long_description='',
			syntax=univention.admin.syntax.string,
			multivalue=True,
			options=[],
			required=False,
			may_change=True,
			identifies=False
	),
	'prohibitedObjectClasses': univention.admin.property(
			short_description=_('Excluded object classes'),
			long_description='',
			syntax=univention.admin.syntax.string,
			multivalue=True,
			options=[],
			required=False,
			may_change=True,
			identifies=False
	),
	'fixedAttributes': univention.admin.property(
			short_description=_('Fixed attributes'),
			long_description='',
			syntax=univention.admin.syntax.uccUserFixedAttributes,
			multivalue=True,
			options=[],
			required=False,
			may_change=True,
			identifies=False
	),
	'emptyAttributes': univention.admin.property(
			short_description=_('Empty attributes'),
			long_description='',
			syntax=univention.admin.syntax.uccUserFixedAttributes,
			multivalue=True,
			options=[],
			required=False,
			may_change=True,
			identifies=False
	),
	'filler': univention.admin.property(
			short_description='',
			long_description='',
			syntax=univention.admin.syntax.none,
			multivalue=False,
			required=False,
			may_change=True,
			identifies=False,
			dontsearch=True
	)
}
layout = [
	Tab(_('General'), _('UCC client configuration'), layout=[
		Group(_('General'), layout=[
			'name',
			'uccupdate',
			'pkginstall',
			'pkgremove',
		]),
	]),
	Tab(_('Object'), _('Object'), advanced=True, layout=[
		['requiredObjectClasses', 'prohibitedObjectClasses'],
		['fixedAttributes', 'emptyAttributes']
	]),
]

mapping = univention.admin.mapping.mapping()
mapping.register('name', 'cn', None, univention.admin.mapping.ListToString)
mapping.register('uccupdate', 'univentionCorporateClientSoftwareUpdateActivate', None, univention.admin.mapping.ListToString)
mapping.register('pkgremove', 'univentionCorporateClientSoftwareUpdateRemoveList')
mapping.register('pkginstall', 'univentionCorporateClientSoftwareUpdateInstallList')


class object(univention.admin.handlers.simplePolicy):
	module = module

	def _ldap_addlist(self):
		return [('objectClass', ['top', 'univentionPolicy', 'univentionPolicySoftwareupdates'])]


def lookup(co, lo, filter_s, base='', superordinate=None, scope='sub', unique=False, required=False, timeout=-1, sizelimit=0):

	filter = univention.admin.filter.conjunction('&', [
		univention.admin.filter.expression('objectClass', 'univentionPolicySoftwareupdates')
	])

	if filter_s:
		filter_p = univention.admin.filter.parse(filter_s)
		univention.admin.filter.walk(filter_p, univention.admin.mapping.mapRewrite, arg=mapping)
		filter.expressions.append(filter_p)

	res = []
	try:
		for dn in lo.searchDn(unicode(filter), base, scope, unique, required, timeout, sizelimit):
			res.append(object(co, lo, None, dn))
	except:
		pass
	return res


def identify(dn, attr, canonical=0):
	return 'univentionPolicySoftwareupdates' in attr.get('objectClass', [])
