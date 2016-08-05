#!/bin/bash

outdir="app_center_upload_dir"
package_source="omar:/var/univention/buildsystem2/apt/"
base_version="ucs_4.1-0"
ucc_scope="-ucc-3.0-integration"

[ -e ${outdir} ] && rm -r ${outdir}
mkdir -p ${outdir}/packages/{all,i386,amd64,source}

# copy local files
cp *ini *svg *png README* ${outdir}

# copy files from integration scope
scp ${package_source}${base_version}${ucc_scope}/all/*deb ${outdir}/packages/all
scp ${package_source}${base_version}${ucc_scope}/i386/*deb ${outdir}/packages/i386
scp ${package_source}${base_version}${ucc_scope}/amd64/*deb ${outdir}/packages/amd64
scp ${package_source}${base_version}${ucc_scope}/source/{*dsc,*tar.gz,*changes} ${outdir}/packages/source

# build tar.gz for appcenter selfservice
cd $outdir
tar czvf ../ucc-3.0.tar.gz *
cd ..

[ ! "${1}" == "--no-delete" ] && rm -r ${outdir}
