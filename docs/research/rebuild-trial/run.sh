#!/bin/bash
# trial sbuild in clean resolute of never-built section-B sources; one line per result
cd ~/work/b/rebuild
for d in libindicator libunity unity-lens-applications unity-lens-files unity-scope-home indicator-application indicator-appmenu indicator-notifications vala-panel; do
	dsc=$(ls ${d}_*.dsc | head -1)
	mkdir -p out-$d
	start=$(date +%s)
	( cd out-$d && sbuild -d resolute --no-run-lintian ../$dsc > sbuild.log 2>&1 )
	st=$(grep -h '^Status:' out-$d/*.build 2>/dev/null | tail -1 | awk '{print $2}')
	stage=$(grep -h '^Fail-Stage:' out-$d/*.build 2>/dev/null | tail -1 | awk '{print $2}')
	echo "$(date -u +%H:%MZ) $d ${st:-unknown} ${stage} $(( $(date +%s) - start ))s" >> results.txt
done
echo DONE >> results.txt
