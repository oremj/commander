from commander.commands import local, remote


ADMIN = ["mradm02"]
PREVIEW = ["pm-app-amo24", "pm-app-amodev01"]


remote(ADMIN, """
    cd /data/amo_python
    /usr/bin/rsync -aq --exclude '.git*' --delete src/preview/ www/preview/
    /usr/bin/rsync -aq --exclude '.git*' --delete src/next/ www/next/
    pushd www
    git add .
    git commit -q -a -m "Push AMO preview"
    popd
""")

remote(PREVIEW, "/data/bin/libget/get-php5-www-git.sh; apachectl graceful")
