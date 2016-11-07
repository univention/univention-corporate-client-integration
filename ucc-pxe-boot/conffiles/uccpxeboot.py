# -*- coding: utf-8 -*-
#
# Univention Client Boot PXE
#  baseconfig/listener module: update config for PXE clients
#
# Copyright (C) 2004-2016 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# Binary versions of this file provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
import re
from fileinput import *
from glob import glob

pattern = '/var/lib/univention-client-boot/pxelinux.cfg/*'


def update_nfs_root(line, changes):
	if isinstance(changes.get('ucc/pxe/nfsroot'), type(())):
		old, new = changes.get('ucc/pxe/nfsroot', (False, False))
		if not old == new:
			line = re.sub("(^| )nfsroot=[^:]+:/var/lib/univention-client-boot($| )", " ", line)
			if new:
				line = line.rstrip()
				line = line + " nfsroot=%s:/var/lib/univention-client-boot" % new
	return line


def update_append(line, changes):
	if isinstance(changes.get('ucc/pxe/append'), type(())):
		old, new = changes.get('ucc/pxe/append', ("", ""))
		if not old == new:
			line = re.sub('(^| )%s($| )' % old, " ", line)
			if new:
				line = re.sub('(^| )%s($| )' % new, " ", line)
				line = line.rstrip()
				line = line + ' %s' % new
	return line


def update_flag(line, changes, baseConfig, var, flag):
	if isinstance(changes.get(var), type(())):
		old, new = changes.get(var, ('', ''))
		if not old == new:
			line = re.sub("(^| )%s($| )" % flag, " ", line)
			if baseConfig.is_true(var, False):
				line = line.rstrip()
				line = line + " %s" % flag
	return line


def update_parameter(line, changes, var, parameter):
	if isinstance(changes.get(var), type(())):
		old, new = changes.get(var, ('', ''))
		if not old == new:
			line = re.sub("(^| )%s=[^ ]+($| )" % parameter, " ", line)
			if new:
				line = line.rstrip()
				line = line + ' %s=%s' % (parameter, new)
	return line


def handler(baseConfig, changes):
	for line in input(glob(pattern), inplace=True):
		line = line.strip('\n')
		if 'APPEND root=' in line:
			line = update_flag(line, changes, baseConfig, "ucc/pxe/bootsplash", "splash")
			line = update_flag(line, changes, baseConfig, "ucc/pxe/quiet", "quiet")
			line = update_flag(line, changes, baseConfig, "ucc/pxe/traditionalinterfacenames", "net.ifnames=0 biosdevname=0")
			line = update_parameter(line, changes, "ucc/pxe/timezone", "timezone")
			line = update_parameter(line, changes, "ucc/pxe/loglevel", "loglevel")
			line = update_parameter(line, changes, "ucc/pxe/vga", "vga")
			line = update_parameter(line, changes, "xorg/keyboard/options/XkbLayout", "keyboard")
			line = update_parameter(line, changes, "locale/default", "locale")
			line = update_append(line, changes)
			line = update_nfs_root(line, changes)
		print line
