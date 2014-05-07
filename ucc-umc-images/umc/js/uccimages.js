/*
 * Copyright 2014 Univention GmbH
 *
 * http://www.univention.de/
 *
 * All rights reserved.
 *
 * The source code of this program is made available
 * under the terms of the GNU Affero General Public License version 3
 * (GNU AGPL V3) as published by the Free Software Foundation.
 *
 * Binary versions of this program provided by Univention to you as
 * well as other copyrighted, protected or trademarked materials like
 * Logos, graphics, fonts, specific documentations and configurations,
 * cryptographic keys etc. are subject to a license agreement between
 * you and Univention and not subject to the GNU AGPL V3.
 *
 * In the case you use this program under the terms of the GNU AGPL V3,
 * the program is provided in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License with the Debian GNU/Linux or Univention distribution in file
 * /usr/share/common-licenses/AGPL-3; if not, see
 * <http://www.gnu.org/licenses/>.
 */
/*global define*/

define([
	"dojo/_base/declare",
	"dojo/_base/lang",
	"dojo/on",
	"umc/dialog",
	"umc/widgets/Grid",
	"umc/widgets/Page",
	"umc/widgets/ExpandingTitlePane",
	"umc/widgets/Module",
	"umc/widgets/TextBox",
	"umc/widgets/ComboBox",
	"umc/i18n!umc/modules/uccimages"
], function(declare, lang, on, dialog, Grid, Page, ExpandingTitlePane, Module, TextBox, ComboBox, _) {
	return declare("umc.modules.uccimages", [ Module ], {
		idProperty: 'id',
		_grid: null,
		_searchPage: null,

		buildRendering: function() {
			this.inherited(arguments);
			this.renderSearchPage();
		},

		renderSearchPage: function(containers, superordinates) {
			this._searchPage = new Page({
				headerText: this.description,
				helpText: ''
			});

			// umc.widgets.Module is also a StackContainer instance that can hold
			// different pages (see also umc.widgets.TabbedModule)
			this.addChild(this._searchPage);

			// umc.widgets.ExpandingTitlePane is an extension of dijit.layout.BorderContainer
			var titlePane = new ExpandingTitlePane({
				title: _('Search results')
			});
			this._searchPage.addChild(titlePane);


			//
			// data grid
			//

			// define grid actions
			var actions = [{
				name: 'add',
				label: _('Add object'),
				description: _('Create a new object'),
				iconClass: 'umcIconAdd',
				isContextAction: false,
				isStandardAction: true,
				callback: lang.hitch(this, '_addObject')
			}, {
				name: 'edit',
				label: _('Edit'),
				description: _('Edit the selected object'),
				iconClass: 'umcIconEdit',
				isStandardAction: true,
				isMultiAction: false,
				callback: lang.hitch(this, '_editObject')
			}, {
				name: 'delete',
				label: _('Delete'),
				description: _('Deleting the selected objects.'),
				isStandardAction: true,
				isMultiAction: true,
				iconClass: 'umcIconDelete',
				callback: lang.hitch(this, '_deleteObjects')
			}];

			// define the grid columns
			var columns = [{
				name: 'title',
				label: _('Image name'),
				width: '55%'
			}, {
				name: 'version',
				label: _('Version'),
				width: '30%'
			}, {
				name: 'status',
				label: _('Status'),
				width: '15%'
			}];

			// generate the data grid
			this._grid = new Grid({
				actions: actions,
				columns: columns,
				moduleStore: this.moduleStore,
				query: { pattern: '' }
			});

			// add the grid to the title pane
			titlePane.addChild(this._grid);


			//
			// conclusion
			//

			// we need to call page's startup method manually as all widgets have
			// been added to the page container object
			this._searchPage.startup();

		},

		_addObject: function() {
			dialog.alert(_('Feature not yet implemented'));
		},

		_editObject: function(ids, items) {
			if (ids.length != 1) {
				// should not happen
				return;
			}
		},

		_deleteObjects: function(ids, items) {
			dialog.alert(_('Feature not yet implemented'));
		}
	});
});
