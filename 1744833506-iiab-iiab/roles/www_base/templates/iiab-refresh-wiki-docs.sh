#!/bin/bash -x

# This /opt/iiab/iiab/roles/httpd/templates/refresh-wiki-docs.sh becomes
# /usr/bin/iiab-refresh-wiki-docs during IIAB's install.

# This pulls down iiab/iiab repo's entire Tech Docs Wiki (and scrapes/downloads
# other docs!) to create IIAB's offline docs collection: http://box/info

# TO DO: find more pages to download/scrape and offline links to fix,
# based on "fieldback" from truly remote implementer/operators.

set -e                           # Exit on error (avoids snowballing)
source {{ iiab_env_file }}       # /etc/iiab/iiab.env
INPUT=/tmp/iiab-wiki
OUTPUT=/tmp/iiab-wiki.out
DESTPATH={{ doc_root }}/info     # /library/www/html/info
DOCSPATH=$DESTPATH/docs          # /library/www/html/info/docs
ADMINDOCSPATH=$DESTPATH/admin-console    # /library/www/html/info/admin-console
# Note 1: sed (below) shortens URLs to 'admin-console'
# Note 2: Depends on "fancyindex on;" in roles/nginx/templates/iiab.conf.j2

rm -rf $INPUT
rm -rf $OUTPUT
mkdir -p $INPUT
mkdir -p $OUTPUT
mkdir -p $DOCSPATH
mkdir -p $ADMINDOCSPATH

git clone https://github.com/iiab/iiab.wiki.git $INPUT
for f in `ls $INPUT`; do    # Unlike further below, $f does NOT include path
    FTRIMMED=${f%.md}
    if [ $FTRIMMED = "Home" ]; then FTRIMMED=index; fi
    pandoc -s $INPUT/$f -o $OUTPUT/$FTRIMMED.html
done
rsync -av $OUTPUT/ $DESTPATH

if [ -d /opt/iiab/iiab-admin-console/docs ]; then
    cp /opt/iiab/iiab-admin-console/docs/*.md $ADMINDOCSPATH
    for f in $ADMINDOCSPATH/*.md; do    # Unlike above, $f INCLUDES path
	FTRIMMED=${f%.md}
	pandoc -s $f -o $FTRIMMED.html
	rm $f
    done
fi

# Download FAQ etc
lynx -reload -source https://wiki.iiab.io/go/FAQ > $DESTPATH/FAQ.html
lynx -reload -source https://wiki.iiab.io/go/Security > $DESTPATH/Security.html
#lynx -reload -source https://wiki.laptop.org/go/IIAB/local_vars.yml > $DESTPATH/local_vars.yml
#lynx -reload -source https://wiki.laptop.org/go/IIAB/local_vars_min.yml > $DESTPATH/local_vars_min.yml
#lynx -reload -source https://wiki.laptop.org/go/IIAB/local_vars_big.yml > $DESTPATH/local_vars_big.yml

# Download older release notes
lynx -reload -source https://github.com/XSCE/xsce/wiki/IIAB-6.2-Release-Notes > $DESTPATH/IIAB-6.2-Release-Notes.html
lynx -reload -source https://github.com/XSCE/xsce/blob/release-6.2/ReleaseNotes6.0.md > $DESTPATH/ReleaseNotes6.0.html
lynx -reload -source https://github.com/XSCE/xsce/blob/release-6.2/ReleaseNotes6.1.md > $DESTPATH/ReleaseNotes6.1.html

# Download Raspberry Pi guides
wget -nc https://magazines-attachments.raspberrypi.org/books/full_pdfs/000/000/038/original/BeginnersGuide-4thEd-Eng_v2.pdf -O $DOCSPATH/BeginnersGuide-4thEd-Eng_v2.pdf || true    # Overrides set -e
wget -nc https://archive.org/15/items/other_doc/other_doc.pdf -O $DOCSPATH/Raspberry_Pi_User_Guide_v4.pdf || true

# Copy PDF from Lokole playbook
cp -p "{{ iiab_dir }}/roles/lokole/Lokole-IIAB_Users_Manual.pdf" $DOCSPATH    # From /opt/iiab/iiab

# MAKE LINKS REFER TO LOCAL ITEMS...

# ...on main page (http://box/info)
sed -i "s|https://magazines-attachments.raspberrypi.org/books/full_pdfs/000/000/038/original/BeginnersGuide-4thEd-Eng_v2.pdf|docs/BeginnersGuide-4thEd-Eng_v2.pdf|g" $DESTPATH/index.html
sed -i "s|https://.*archive.org/15/items/other_doc/other_doc.pdf|docs/Raspberry_Pi_User_Guide_v4.pdf|g" $DESTPATH/index.html
sed -i "s|https://github.com/iiab/iiab/blob/master/roles/lokole/Lokole-IIAB_Users_Manual.pdf|docs/Lokole-IIAB_Users_Manual.pdf|g" $DESTPATH/index.html

# ...and within subpages
for f in $(find $DESTPATH -name "*.html"); do    # Recursive (even if not yet nec, as of 2023-01-11)
#for f in $DESTPATH/*.html; do                   # Non-recursive (omits subdirs)
    sed -i -r "s|https://github.com/iiab/iiab/wiki/([-.~A-Za-z0-9]*)|\1.html|g" $f

    sed -i "s|https://github.com/iiab/iiab-admin-console/tree/master/docs|admin-console|g" $f

    sed -i "s|https://github.com/xsce/xsce/blob/release-6.2/\(.*\)\.md\">|\1.html\">|g" $f
    sed -i "s|https://github.com/xsce/xsce/wiki/\(.*\)\">|\1.html\">|g" $f

    sed -i "s|https://wiki.iiab.io/go/FAQ|FAQ.html|g" $f
    #sed -i "s|http://wiki.laptop.org/go/IIAB/FAQ|FAQ.html|g" $f
    sed -i "s|/go/IIAB/FAQ|FAQ.html|g" $f
    sed -i "s|http://wiki.iiab.io/FAQ|FAQ.html|g" $f
    sed -i "s|http://FAQ.IIAB.IO|FAQ.html|g" $f
    sed -i "s|http://faq.iiab.io|FAQ.html|g" $f
    #sed -i "s|http://schoolserver.org/FAQ|FAQ.html|g" $f
    #sed -i "s|http://schoolserver.org/faq|FAQ.html|g" $f
    #sed -i "s|http://wiki.laptop.org/go/XS_Community_Edition/FAQ|FAQ.html|g" $f

    #sed -i "s|http://wiki.laptop.org/go/IIAB/Security|Security.html|g" $f
    sed -i "s|/go/IIAB/Security|Security.html|g" $f
    sed -i "s|http://wiki.iiab.io/Security|Security.html|g" $f

    #sed -i "s|http://wiki.laptop.org/go/IIAB/local_vars.yml|local_vars.yml|g" $f
    sed -i "s|/go/IIAB/local_vars.yml|local_vars.yml|g" $f
    sed -i "s|https://wiki.iiab.io/local_vars.yml|local_vars.yml|g" $f

    #sed -i "s|http://wiki.laptop.org/go/IIAB/local_vars_min.yml|local_vars_min.yml|g" $f
    #sed -i "s|/go/IIAB/local_vars_min.yml|local_vars_min.yml|g" $f
    #sed -i "s|http://wiki.iiab.io/local_vars_min.yml|local_vars_min.yml|g" $f

    #sed -i "s|http://wiki.laptop.org/go/IIAB/local_vars_big.yml|local_vars_big.yml|g" $f
    #sed -i "s|/go/IIAB/local_vars_big.yml|local_vars_big.yml|g" $f
    #sed -i "s|http://wiki.iiab.io/local_vars_big.yml|local_vars_big.yml|g" $f
done

exit 0
