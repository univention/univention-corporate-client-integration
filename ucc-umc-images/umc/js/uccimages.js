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
	"dojo/_base/array",
	"dojo/on",
	"dojo/Deferred",
	"umc/tools",
	"umc/dialog",
	"umc/widgets/Grid",
	"umc/widgets/Page",
	"umc/widgets/ExpandingTitlePane",
	"umc/widgets/Module",
	"umc/widgets/ProgressBar",
	"umc/i18n!umc/modules/uccimages"
], function(declare, lang, array, on, Deferred, tools, dialog, Grid, Page, ExpandingTitlePane, Module, ProgressBar, _) {
	return declare("umc.modules.uccimages", [ Module ], {
		idProperty: 'file',
		_grid: null,
		_searchPage: null,
		_progressBar: null,

		buildRendering: function() {
			this.inherited(arguments);
			this.renderSearchPage();
		},

		renderSearchPage: function(containers, superordinates) {
			this._progressBar = new ProgressBar();
			this.own(this._progressBar);

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
				name: 'reload',
				label: _('Refresh'),
				description: _('Refresh the list view'),
				isContextAction: false,
				iconClass: 'umcIconRefresh',
				callback: lang.hitch(this, function() {
					this._grid.filter(this._grid.query);
				})
			}, {
				name: 'download',
				label: _('Download'),
				description: _('Download a UCC image'),
				iconClass: 'umcIconAdd',
				isStandardAction: true,
				callback: lang.hitch(this, '_download'),
				canExecute: function(item) {
					return item.status == 'available' || item.status == 'incomplete';
				}
			}, {
				name: 'remove',
				label: _('Remove'),
				description: _('Remove a UCC image'),
				isStandardAction: true,
				isMultiAction: true,
				iconClass: 'umcIconDelete',
				callback: lang.hitch(this, '_remove'),
				canExecute: function(item) {
					return item.status == 'installed' || item.status == 'incomplete' || item.status == 'deprecated';
				}
			}];

			// define the grid columns
			var statusMap = {
				installed: _('Installed'),
				downloading: _('Downloading'),
				available: _('Available'),
				incomplete: _('Incomplete'),
				deprecated: _('Deprecated')
			};

			var columns = [{
				name: 'description',
				label: _('Image name'),
				width: '55%'
			}, {
				name: 'version',
				label: _('Version'),
				width: '30%'
			}, {
				name: 'status',
				label: _('Status'),
				width: '15%',
				formatter: function(value) {
					return statusMap[value];
				}
			}];

			// generate the data grid
			this._grid = new Grid({
				actions: actions,
				columns: columns,
				moduleStore: this.moduleStore,
				query: { pattern: '' },
				sortIndex: null
			});

			// set sorting options
			this._grid._grid.set('sortFields', [{
				attribute: 'id',
				descending: false
			}, {
				attribute: 'version',
				descending: true
			}]);

			// add the grid to the title pane
			titlePane.addChild(this._grid);


			//
			// conclusion
			//

			// we need to call page's startup method manually as all widgets have
			// been added to the page container object
			this._searchPage.startup();

		},

		_download: function(spec_files, items) {
			if (items.length != 1) {
				// should not happen
				return;
			}
			var item = items[0];
			var gb = item.size / Math.pow(10, 9);
			dialog.confirm(_('Please confirm the download of the UCC image %s [%.1f GB].', item.description, gb), [{
				label: _('Cancel'),
				name: 'cancel'
			}, {
				label: _('Download'),
				'default': true,
				name: 'download'
			}]).then(lang.hitch(this, function(response) {
				if (response != 'download') {
					return;
				}

				this.standby(false);
				this._progressBar.reset(_('Downloading and registering UCC image'));
				var downloadCmd = this.umcpProgressCommand(this._progressBar, 'uccimages/download', {
					image: items[0].spec_file
				}).then(lang.hitch(this, function(result) {
					this.standby(false);
					this._grid.filter(this._grid.query);
					if (result.error) {
						var err = result.error;
						err = err.replace(/\n/g, '<br>');
						dialog.alert(err, _('Download error'));
					}
				}), lang.hitch(this, function(err) {
					this.standby(false);
				}));
				this.standbyDuring(downloadCmd, this._progressBar);
			}));
		},

		_remove: function(ids, items) {
			var deferred_progress = new Deferred();
			var deferred_chain = new Deferred();
			deferred_chain.resolve();

			this.standby(false);
			this._progressBar.feedFromDeferred(deferred_progress, _('Removing images...'));
			this.standby(true, this._progressBar);

			var remove = function(spec_file) {
				return tools.umcpCommand('uccimages/remove', {
					image: spec_file
				});
			};

			array.forEach(items, function(item, idx) {
				deferred_chain = deferred_chain.then(lang.hitch(this, function() {
					deferred_progress.progress({
						component: _('Removing image %s of %s', idx + 1, items.length),
						percentage: 100.0 * idx / items.length
					});
					return remove(item.spec_file);
				}));
			}, this);

			deferred_chain.then(lang.hitch(this, function() {
				this.standby(false);
				this._grid.filter(this._grid.query);
			}), lang.hitch(this, function() {
				this.standby(false)
				this._grid.filter(this._grid.query);
			}));
		}
	});
});
