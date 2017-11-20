# -*- coding: utf-8 -*-
#
# Univention Corporate Client
#  UDM policy for thin client session
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

from univention.admin.layout import Tab, Group
import univention.admin.filter
import univention.admin.handlers
import univention.admin.syntax
import univention.admin.localization
import univention.admin.uexceptions

translation = univention.admin.localization.translation('univention.admin.handlers.ucc-policies')
_ = translation.translate

module = 'settings/ucc_session'

childs = 0
short_description = _('UCC session script')
long_description = ''
operations = ['search', 'edit', 'add', 'remove']
superordinate = 'settings/cn'

property_descriptions = {
	'name': univention.admin.property(
			short_description=_('Name'),
			long_description=_('Name'),
			syntax=univention.admin.syntax.string,
			multivalue=False,
			options=[],
			required=True,
			may_change=True,
			identifies=True
	),
	'description': univention.admin.property(
			short_description=_('Description'),
			long_description=_('Description of session'),
			syntax=univention.admin.syntax.string,
			multivalue=False,
			options=[],
			required=False,
			may_change=True,
			identifies=False
	),
	'session': univention.admin.property(
			short_description=_('Session to start'),
			long_description=_('Session to start by display manager'),
			syntax=univention.admin.syntax.string,
			multivalue=False,
			options=[],
			required=False,
			may_change=True,
			identifies=False
	),
}


layout = [
	Tab(_('General'), _('UCC session script'), layout=[
		Group(_('General'), layout=[
			'name',
			'description',
			'session'
		]),
	])
]


mapping = univention.admin.mapping.mapping()
mapping.register('name', 'univentionCorporateClientSessionName', None, univention.admin.mapping.ListToString)
mapping.register('description', 'description', None, univention.admin.mapping.ListToString)
mapping.register('session', 'univentionCorporateClientSessionScript', None, univention.admin.mapping.ListToString)


class object(univention.admin.handlers.simpleLdap):
	module = module

	def _ldap_pre_create(self):
		self.dn = '%s=%s,%s' % (mapping.mapName('name'), mapping.mapValue('name', self.info['name']), self.position.getDn())

	def _ldap_addlist(self):
		return [('objectClass', ['univentionCorporateClientSession'])]


def lookup(co, lo, filter_s, base='', superordinate=None, scope='sub', unique=False, required=False, timeout=-1, sizelimit=0):
	filter = univention.admin.filter.conjunction('&', [
		univention.admin.filter.expression('objectClass', 'univentionCorporateClientSession'),
	])

	if filter_s:
		filter_p = univention.admin.filter.parse(filter_s)
		univention.admin.filter.walk(filter_p, univention.admin.mapping.mapRewrite, arg=mapping)
		filter.expressions.append(filter_p)

	res = []
	for dn in lo.searchDn(unicode(filter), base, scope, unique, required, timeout, sizelimit):
		res.append(object(co, lo, None, dn))
	return res


def identify(dn, attr, canonical=0):
	return 'univentionCorporateClientSession' in attr.get('objectClass', [])
