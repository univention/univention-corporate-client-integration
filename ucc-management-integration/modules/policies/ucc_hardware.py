# -*- coding: utf-8 -*-
#
# Univention Corporate Client
#  UDM policy for user session configuration
#
# Copyright (C) 2010-2016 Univention GmbH
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

import sys, string
sys.path = ['.'] + sys.path

from univention.admin.layout import Tab, Group
import univention.admin.syntax
import univention.admin.filter
import univention.admin.handlers
import univention.admin.localization

import univention.debug

translation = univention.admin.localization.translation('univention.admin.handlers.ucc-policies')
_ = translation.translate

class uccClientFixedAttributes(univention.admin.syntax.select):
	name = 'uccClientFixedAttributes'
	choices = [
		('univentionCorporateClientComputerLocalStorage', _('Allow access to local mass storage')),
		]

module = 'policies/ucc_computer'
operations = ['add', 'edit', 'remove', 'search']

policy_oc = 'univentionPolicyCorporateClientComputer'
policy_apply_to = ["computers/ucc"]
policy_position_dn_prefix = "cn=ucc"

childs = 0
short_description = _('Policy: UCC hardware settings')
policy_short_description = _('UCC hardware settings')
long_description = ''
options = {
}
property_descriptions = {
	'name': univention.admin.property(
			short_description=_('Name'),
			long_description='',
			syntax=univention.admin.syntax.string,
			multivalue=0,
			options=[],
			required=1,
			may_change=0,
			identifies=1,
		),
	'massstorage': univention.admin.property(
			short_description=_('Allow access to local mass storage'),
			long_description=_('This settings configures, whether access to local mass storage is enabled if a UCC system is used as a thin client'),
			syntax=univention.admin.syntax.boolean,
			multivalue=0,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
	'prim_res': univention.admin.property(
			short_description=_('Resolution of primary display'),
			long_description=_('The resolution in pixels (XxY) of the primary display, if left blank the detection is done automatically'),
			syntax=univention.admin.syntax.XResolution,
			multivalue=0,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
	'sec_res': univention.admin.property(
			short_description=_('Resolution of secondary display'),
			long_description=_('The resolution in pixels (XxY) of the secondary display, if left blank the detection is done automatically'),
			syntax=univention.admin.syntax.XResolution,
			multivalue=0,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
	'prim_name': univention.admin.property(
			short_description=_('Name of primary display'),
			long_description=_('The X name of the primary display device (can be queried with xrandr -q)'),
			syntax=univention.admin.syntax.string,
			multivalue=0,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
	'sec_name': univention.admin.property(
			short_description=_('Name of secondary display'),
			long_description=_('The X name of the secondary display device (can be queried with xrandr -q)'),
			syntax=univention.admin.syntax.string,
			multivalue=0,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
	'display-position': univention.admin.property(
			short_description=_('Position of secondary display relative to the primary'),
			long_description='',
			syntax=univention.admin.syntax.XDisplayPosition,
			multivalue=0,
			options=[],
			required=0,
			may_change=1,
			identifies=0,
			default=('', [])
		),
	'requiredObjectClasses': univention.admin.property(
			short_description=_('Required object classes'),
			long_description='',
			syntax=univention.admin.syntax.string,
			multivalue=1,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
	'prohibitedObjectClasses': univention.admin.property(
			short_description=_('Excluded object classes'),
			long_description='',
			syntax=univention.admin.syntax.string,
			multivalue=1,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
	'fixedAttributes': univention.admin.property(
			short_description=_('Fixed attributes'),
			long_description='',
			syntax=uccClientFixedAttributes,
			multivalue=1,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
	'emptyAttributes': univention.admin.property(
			short_description=_('Empty attributes'),
			long_description='',
			syntax=uccClientFixedAttributes,
			multivalue=1,
			options=[],
			required=0,
			may_change=1,
			identifies=0
		),
	'filler': univention.admin.property(
			short_description='',
			long_description='',
			syntax=univention.admin.syntax.none,
			multivalue=0,
			required=0,
			may_change=1,
			identifies=0,
			dontsearch=1
		)
}
layout = [
	Tab(_('General'), _('UCC client configuration'), layout=[
		Group(_('General'), layout=[
			'name',
			'massstorage',
		]),
		Group(_('Multi monitor configuration'), layout=[
			['prim_res', 'sec_res'],
			['prim_name', 'sec_name'],
			'display-position',
		]),
	]),
	Tab(_('Object'), _('Object'), advanced=True, layout=[
		['requiredObjectClasses', 'prohibitedObjectClasses'],
		['fixedAttributes', 'emptyAttributes']
	]),
]

mapping = univention.admin.mapping.mapping()
mapping.register('name', 'cn', None, univention.admin.mapping.ListToString)
mapping.register('massstorage', 'univentionCorporateClientComputerLocalStorage', None, univention.admin.mapping.ListToString)
mapping.register('prim_res', 'univentionCorporateClientPrimaryDisplayResolution', None, univention.admin.mapping.ListToString)
mapping.register('sec_res', 'univentionCorporateClientSecondaryDisplayResolution', None, univention.admin.mapping.ListToString)
mapping.register('prim_name', 'univentionCorporateClientPrimaryDisplayName', None, univention.admin.mapping.ListToString)
mapping.register('sec_name', 'univentionCorporateClientSecondaryDisplayName', None, univention.admin.mapping.ListToString)
mapping.register('display-position', 'univentionCorporateClientDisplayPosition', None, univention.admin.mapping.ListToString)



class object(univention.admin.handlers.simplePolicy):
	module = module

	def __init__(self, co, lo, position, dn='', superordinate=None, attributes=[]):
		global mapping
		global property_descriptions

		self.mapping = mapping
		self.descriptions = property_descriptions

		univention.admin.handlers.simplePolicy.__init__(self, co, lo, position, dn, superordinate)

	def exists(self):
		return self._exists

	def _ldap_pre_create(self):
		self.dn = '%s=%s,%s' % (mapping.mapName('name'), mapping.mapValue('name', self.info['name']), self.position.getDn())

	def _ldap_addlist(self):
		return [('objectClass', ['top', 'univentionPolicy', 'univentionPolicyCorporateClientComputer'])]

def lookup(co, lo, filter_s, base='', superordinate=None, scope='sub', unique=0, required=0, timeout=-1, sizelimit=0):

	filter = univention.admin.filter.conjunction('&', [
		univention.admin.filter.expression('objectClass', 'univentionPolicyCorporateClientComputer')
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
	return 'univentionPolicyCorporateClientComputer' in attr.get('objectClass', [])
