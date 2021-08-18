cd $WORKSPACE/engineers_cool

python3 tools/gen_sidebar.py
cat _sidebar.gen.md
#mv _sidebar.md _sidebar.md.old
#mv _sidebar.gen.md _sidebar.md

#sudo rm -rf /var/www/engineers_cool
#sudo cp -rf ~/work/engineers_cool /var/www/
