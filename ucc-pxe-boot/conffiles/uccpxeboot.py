# -*- coding: utf-8 -*-
#
# Univention Client Boot PXE
#  baseconfig/listener module: update config for PXE clients
#
# Copyright (C) 2004-2011 Univention GmbH
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

def update_loglevel (line, changes):
	if type(changes.get('ucc/pxe/loglevel')) == type(()):
		old, new = changes.get('ucc/pxe/loglevel', (False, False))
		if not old == new:
			line = re.sub("(^| )loglevel=[^ ]+($| )", " ", line)
			if new:
				line = line.rstrip()
				line = line + " loglevel=%s" % new
	return line

def update_quiet (line, changes):
	if type(changes.get('ucc/pxe/quit')) == type(()):
		old, new = changes.get('ucc/pxe/quiet', (False, False))
		if not old == new:
			line = re.sub("(^| )quiet($| )", " ", line)
			if new and new.lower() in ['yes', 'true', '1']:
				line = line.rstrip()
				line = line + " quiet"
	return line

def update_vga (line, changes):
	if type(changes.get('ucc/pxe/vga')) == type(()):
		old, new = changes.get('ucc/pxe/vga', (False, False))
		if not old == new:
			line = re.sub("(^| )vga=[^ ]+($| )", " ", line)
			if new:
				line = line.rstrip()
				line = line + " vga=%s" % new
	return line

def update_nfs_root (line, changes):
	if type(changes.get('ucc/pxe/nfsroot')) == type(()):
		old, new = changes.get('ucc/pxe/nfsroot', (False, False))
		if not old == new:
			line = re.sub("(^| )nfsroot=[^:]+:/var/lib/univention-client-root($| )", " ", line)
			if new:
				line = line.rstrip()
				line = line + " nfsroot=%s:/var/lib/univention-client-root" % new
	return line

def update_append(line, changes):
	if type(changes.get('pxe/append')) == type(()):
		old, new = changes.get('pxe/append', ("", ""))
		if not old == new:
			line = re.sub('(^| )%s($| )' % old, " ", line)
			if new:
				line = line.rstrip()
				line = line + ' %s' % new
	return line

def handler(baseConfig, changes):

	for line in input(glob(pattern), inplace = True):
		line = line.strip('\n')
		if 'APPEND root=' in line:
			line = update_loglevel(line, changes)
			line = update_quiet(line, changes)
			line = update_vga(line, changes)
			line = update_nfs_root(line, changes)
			line = update_append(line, changes)
			# xorg/keyboard/options/XkbLayout
			# locale/default
			# ucc/pxe/timezone
			# ucc/pxe/append
			# ucc/pxe/bootsplash
		print line
