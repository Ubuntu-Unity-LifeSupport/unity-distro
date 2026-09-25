#!/bin/sh
# Print every xorg-server upload to resolute (all pockets) newer than the one we
# are based on. Anything printed means: rebase our CVE patches onto it before it
# reaches -updates (proposed gives about a week).
BASE=${1:-2:21.1.22-1ubuntu1.3}
curl -s -m 60 'https://api.launchpad.net/devel/ubuntu/+archive/primary?ws.op=getPublishedSources&source_name=xorg-server&exact_match=true&distro_series=https://api.launchpad.net/devel/ubuntu/resolute&order_by_date=true' |
python3 -c "
import json,sys,subprocess
base=sys.argv[1]
for e in json.load(sys.stdin)['entries']:
    v=e['source_package_version']
    if subprocess.run(['dpkg','--compare-versions',v,'gt',base]).returncode==0:
        print(v, e['pocket'], e['status'], e['date_published'] or e['date_created'])
" "$BASE"
